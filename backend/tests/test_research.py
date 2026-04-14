from __future__ import annotations

import asyncio
import json

import pytest

from app.api.v1 import research as research_module
from app.api.v1 import proxy as proxy_module
from app.api.v1.research import _run_pipeline, run_research
from app.config import Settings
from app.models.mws import ChatCompletionRequest, Message
from app.services.router_client import RouteResult
from app.services.web_parser import WebParserService


def make_settings(**overrides) -> Settings:
    base = {
        "MWS_API_KEY": "test-key",
        "MWS_BASE_URL": "https://example.test",
        "MODEL_RESEARCH_QUERY": "planner-model",
        "MODEL_RESEARCH_SYNTHESIS": "synthesis-model",
        "RESEARCH_SUBQUERY_COUNT": 3,
        "RESEARCH_SEARCH_RESULTS": 3,
        "RESEARCH_CONCURRENCY": 2,
        "RESEARCH_PARSE_TIMEOUT": 5,
        "RESEARCH_SEARCH_TIMEOUT": 5,
        "RESEARCH_FETCH_TOTAL_TIMEOUT": 5,
        "RESEARCH_SUBQUERY_TIMEOUT": 5,
        "RESEARCH_SYNTHESIS_TIMEOUT": 5,
        "RESEARCH_MAX_SOURCE_TEXT_CHARS": 400,
        "RESEARCH_MAX_SOURCES": 4,
        "RESEARCH_MAX_CONTEXT_CHARS": 3000,
        "RESEARCH_MAX_ACTIVE_RUNS": 2,
        "RESEARCH_SEARCH_THREADS": 2,
        "RESEARCH_MAX_PAGE_BYTES": 500_000,
    }
    base.update(overrides)
    return Settings(**base)


class FakeMWS:
    def __init__(
        self,
        *,
        sub_queries: list[str] | None = None,
        final_answer: str = "Structured answer with [S1].",
        synthesis_error: Exception | None = None,
        chat_response: dict | None = None,
    ) -> None:
        self.sub_queries = sub_queries or ["sub-query one", "sub-query two"]
        self.final_answer = final_answer
        self.synthesis_error = synthesis_error
        self.chat_response = chat_response or {
            "id": "chatcmpl-normal",
            "model": "plain-model",
            "choices": [{"message": {"content": "plain completion"}}],
        }
        self.calls: list[dict] = []
        self.chat_calls: list[ChatCompletionRequest] = []

    async def chat_simple(self, model: str, system: str, user: str) -> str:
        self.calls.append({"model": model, "system": system, "user": user})
        if "research planner" in system:
            return json.dumps(self.sub_queries, ensure_ascii=False)
        if self.synthesis_error:
            raise self.synthesis_error
        return self.final_answer

    async def chat(self, request: ChatCompletionRequest) -> dict:
        self.chat_calls.append(request)
        return self.chat_response


class FakeSearchService:
    def __init__(self, mapping: dict[str, list[dict]]) -> None:
        self.mapping = mapping
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        self.calls.append((query, max_results))
        return list(self.mapping.get(query, []))[:max_results]


class FakeParserService:
    def __init__(self, mapping: dict[str, dict]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    async def parse(self, url: str) -> dict:
        self.calls.append(url)
        return self.mapping[url]


class FakeRouterClient:
    def __init__(self, route: RouteResult) -> None:
        self.route_result = route
        self.calls: list[tuple[str, list[dict]]] = []

    async def route(self, message: str, attachments: list[dict]) -> RouteResult:
        self.calls.append((message, attachments))
        return self.route_result


class FakeStreamResponse:
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        body_chunks: list[bytes] | None = None,
        status_code: int = 200,
        encoding: str = "utf-8",
    ) -> None:
        self.headers = headers or {}
        self._body_chunks = body_chunks or []
        self.status_code = status_code
        self.encoding = encoding

    async def __aenter__(self) -> "FakeStreamResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    async def aiter_bytes(self):
        for chunk in self._body_chunks:
            yield chunk


class FakeParserHttpClient:
    def __init__(self, response: FakeStreamResponse) -> None:
        self._response = response
        self.is_closed = False

    def stream(self, method: str, url: str) -> FakeStreamResponse:
        return self._response


class FakeWebParserService(WebParserService):
    def __init__(self, response: FakeStreamResponse, *, max_body_bytes: int = 1_500_000) -> None:
        super().__init__(timeout=5, max_body_bytes=max_body_bytes)
        self._test_client = FakeParserHttpClient(response)

    def _http(self):
        return self._test_client


class FakeDisconnectRequest:
    def __init__(self) -> None:
        self.disconnected = False

    async def is_disconnected(self) -> bool:
        return self.disconnected


class DelayedSearchService(FakeSearchService):
    def __init__(self, mapping: dict[str, list[dict]], delays: dict[str, float]) -> None:
        super().__init__(mapping)
        self.delays = delays

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        delay = self.delays.get(query, 0.0)
        if delay:
            await asyncio.sleep(delay)
        return await super().search(query, max_results=max_results)


def parse_sse(raw_event: str) -> tuple[str, dict]:
    event_type = ""
    data: dict = {}
    for line in raw_event.strip().splitlines():
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = json.loads(line.split(":", 1)[1].strip())
    return event_type, data


def build_fake_services():
    search = FakeSearchService(
        {
            "sub-query one": [
                {
                    "title": "Alpha source",
                    "url": "https://example.test/a",
                    "snippet": "Alpha snippet",
                },
                {
                    "title": "Shared source",
                    "url": "https://example.test/shared",
                    "snippet": "Shared short snippet",
                },
            ],
            "sub-query two": [
                {
                    "title": "Beta source",
                    "url": "https://example.test/b",
                    "snippet": "Beta snippet",
                },
                {
                    "title": "Shared source newer",
                    "url": "https://example.test/shared",
                    "snippet": "Shared longer snippet",
                },
            ],
        }
    )
    parser = FakeParserService(
        {
            "https://example.test/a": {
                "url": "https://example.test/a",
                "title": "Alpha article",
                "text": "Alpha details " * 20,
                "links": [],
            },
            "https://example.test/b": {
                "url": "https://example.test/b",
                "title": "Beta article",
                "text": "Beta details " * 18,
                "links": [],
            },
            "https://example.test/shared": {
                "url": "https://example.test/shared",
                "title": "Shared article",
                "text": "Shared details that are intentionally longer than the first version. " * 10,
                "links": [],
            },
        }
    )
    return search, parser


@pytest.mark.asyncio
async def test_run_research_returns_structured_sources_and_progress() -> None:
    settings = make_settings()
    mws = FakeMWS(
        final_answer="Final answer with citations [S1] and [S2].",
    )
    search, parser = build_fake_services()
    progress_events: list[tuple[str, dict]] = []

    async def emit(event: str, data: dict) -> None:
        progress_events.append((event, data))

    result = await run_research(
        "Tell me about vector databases",
        mws,
        settings,
        search_svc=search,
        parser_svc=parser,
        emit=emit,
    )

    assert result["status"] == "ok"
    assert result["answer"] == "Final answer with citations [S1] and [S2]."
    assert result["model"] == settings.MODEL_RESEARCH_SYNTHESIS
    assert result["sub_queries"] == ["sub-query one", "sub-query two", "Tell me about vector databases"]
    assert result["stats"]["pages_fetched"] == 3
    assert result["stats"]["sources_used"] == 3
    assert {source["url"] for source in result["sources"]} == {
        "https://example.test/a",
        "https://example.test/b",
        "https://example.test/shared",
    }
    assert all(source["source_id"].startswith("S") for source in result["sources"])
    assert any("Shared details" in source["excerpt"] for source in result["sources"])
    assert [call["model"] for call in mws.calls] == [
        settings.MODEL_RESEARCH_QUERY,
        settings.MODEL_RESEARCH_SYNTHESIS,
    ]
    assert [event for event, _ in progress_events].count("progress") >= 5
    assert {data["step"] for event, data in progress_events if event == "progress" and "step" in data} >= {
        1,
        2,
        3,
        4,
        5,
    }


@pytest.mark.asyncio
async def test_run_research_falls_back_to_original_query_on_planner_error() -> None:
    settings = make_settings(RESEARCH_SUBQUERY_COUNT=2)
    search = FakeSearchService(
        {
            "fallback query": [
                {
                    "title": "Only source",
                    "url": "https://example.test/fallback",
                    "snippet": "Fallback snippet",
                }
            ]
        }
    )
    parser = FakeParserService(
        {
            "https://example.test/fallback": {
                "url": "https://example.test/fallback",
                "title": "Fallback title",
                "text": "Fallback content " * 12,
                "links": [],
            }
        }
    )

    class PlannerFailureMWS(FakeMWS):
        async def chat_simple(self, model: str, system: str, user: str) -> str:
            self.calls.append({"model": model, "system": system, "user": user})
            if "research planner" in system:
                raise RuntimeError("planner unavailable")
            return self.final_answer

    mws = PlannerFailureMWS(final_answer="Recovered answer with [S1].")
    result = await run_research(
        "fallback query",
        mws,
        settings,
        search_svc=search,
        parser_svc=parser,
    )

    assert result["status"] == "ok"
    assert result["sub_queries"] == ["fallback query"]
    assert result["stats"]["pages_fetched"] == 1
    assert result["sources"][0]["url"] == "https://example.test/fallback"


@pytest.mark.asyncio
async def test_run_research_returns_error_for_empty_query() -> None:
    result = await run_research("", FakeMWS(), make_settings())

    assert result["status"] == "error"
    assert result["error_code"] == "empty_query"
    assert result["sources"] == []
    assert result["stats"]["pages_fetched"] == 0
    assert result["message"]


@pytest.mark.asyncio
async def test_run_research_surfaces_synthesis_timeout_with_partial_sources() -> None:
    settings = make_settings()
    search, parser = build_fake_services()
    mws = FakeMWS(synthesis_error=asyncio.TimeoutError())

    result = await run_research(
        "timeout query",
        mws,
        settings,
        search_svc=search,
        parser_svc=parser,
    )

    assert result["status"] == "error"
    assert result["error_code"] == "synthesis_timeout"
    assert result["model"] == settings.MODEL_RESEARCH_SYNTHESIS
    assert result["sources"]
    assert result["stats"]["pages_fetched"] == 3
    assert result["stats"]["sources_used"] == 3


@pytest.mark.asyncio
async def test_run_research_returns_planner_timeout_error() -> None:
    settings = make_settings(RESEARCH_SUBQUERY_TIMEOUT=1)

    class SlowPlannerMWS(FakeMWS):
        async def chat_simple(self, model: str, system: str, user: str) -> str:
            self.calls.append({"model": model, "system": system, "user": user})
            if "research planner" in system:
                await asyncio.sleep(2)
                return json.dumps(["slow-sub-query"])
            return self.final_answer

    result = await run_research(
        "planner timeout",
        SlowPlannerMWS(),
        settings,
        search_svc=FakeSearchService({}),
        parser_svc=FakeParserService({}),
    )

    assert result["status"] == "error"
    assert result["error_code"] == "planner_timeout"
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_run_research_returns_partial_sources_when_fetch_deadline_hits() -> None:
    settings = make_settings(
        RESEARCH_SUBQUERY_COUNT=2,
        RESEARCH_FETCH_TOTAL_TIMEOUT=1,
        RESEARCH_SEARCH_TIMEOUT=1,
    )
    search = DelayedSearchService(
        {
            "fast-search": [
                {
                    "title": "Fast source",
                    "url": "https://example.test/fast",
                    "snippet": "Fast snippet",
                }
            ],
            "slow-search": [
                {
                    "title": "Slow source",
                    "url": "https://example.test/slow",
                    "snippet": "Slow snippet",
                }
            ],
        },
        delays={"slow-search": 2},
    )
    parser = FakeParserService(
        {
            "https://example.test/fast": {
                "url": "https://example.test/fast",
                "title": "Fast title",
                "text": "Fast content " * 10,
                "links": [],
            },
            "https://example.test/slow": {
                "url": "https://example.test/slow",
                "title": "Slow title",
                "text": "Slow content " * 10,
                "links": [],
            },
        }
    )
    mws = FakeMWS(sub_queries=["fast-search", "slow-search"], final_answer="Partial answer with [S1].")

    result = await run_research(
        "fetch timeout query",
        mws,
        settings,
        search_svc=search,
        parser_svc=parser,
    )

    assert result["status"] == "ok"
    assert result["stats"]["timed_out"] is True
    assert result["stats"]["queries_completed"] == 1
    assert result["stats"]["pages_fetched"] == 1
    assert result["stats"]["sources_used"] == 1
    assert result["sources"][0]["url"] == "https://example.test/fast"


@pytest.mark.asyncio
async def test_web_parser_extracts_text_from_html() -> None:
    response = FakeStreamResponse(
        headers={"content-type": "text/html; charset=utf-8"},
        body_chunks=[
            (
                b"<html><head><title>Alpha</title><script>ignored()</script></head>"
                b"<body><h1>Hello</h1><p>World</p></body></html>"
            )
        ],
    )
    parser = FakeWebParserService(response)

    parsed = await parser.parse("https://example.test/article")

    assert parsed["title"] == "Alpha"
    assert "Hello" in parsed["text"]
    assert "World" in parsed["text"]
    assert "ignored" not in parsed["text"]


@pytest.mark.asyncio
async def test_web_parser_rejects_unsupported_content_type() -> None:
    parser = FakeWebParserService(
        FakeStreamResponse(
            headers={"content-type": "application/pdf"},
            body_chunks=[b"%PDF-1.7"],
        )
    )

    parsed = await parser.parse("https://example.test/file.pdf")

    assert parsed["error"] == "unsupported content type: application/pdf"
    assert parsed["text"] == ""


@pytest.mark.asyncio
async def test_web_parser_rejects_large_content_length() -> None:
    parser = FakeWebParserService(
        FakeStreamResponse(
            headers={
                "content-type": "text/html",
                "content-length": "2048",
            },
            body_chunks=[b"<html><body>too large</body></html>"],
        ),
        max_body_bytes=1024,
    )

    parsed = await parser.parse("https://example.test/oversized")

    assert parsed["error"] == "response too large"
    assert parsed["text"] == ""


@pytest.mark.asyncio
async def test_web_parser_rejects_stream_body_over_limit() -> None:
    parser = FakeWebParserService(
        FakeStreamResponse(
            headers={"content-type": "text/html"},
            body_chunks=[b"a" * 700, b"b" * 700],
        ),
        max_body_bytes=1000,
    )

    parsed = await parser.parse("https://example.test/stream-too-large")

    assert parsed["error"] == "response too large"
    assert parsed["text"] == ""


@pytest.mark.asyncio
async def test_run_pipeline_emits_progress_then_done_payload() -> None:
    settings = make_settings()
    mws = FakeMWS(final_answer="Pipeline answer with [S1].")
    search, parser = build_fake_services()

    events: list[tuple[str, dict]] = []
    async for raw in _run_pipeline(
        "pipeline query",
        mws,
        settings,
        search_svc=search,
        parser_svc=parser,
    ):
        events.append(parse_sse(raw))

    assert events
    assert events[-1][0] == "done"
    assert events[-1][1]["answer"] == "Pipeline answer with [S1]."
    assert events[-1][1]["sources"]
    assert any(event == "progress" and data.get("step") == 2 for event, data in events)
    assert any(event == "progress" and data.get("step") == 4 for event, data in events)


@pytest.mark.asyncio
async def test_run_pipeline_emits_run_id_in_initial_progress_event() -> None:
    settings = make_settings()
    planner_started = asyncio.Event()
    planner_cancelled = asyncio.Event()

    class SlowPlannerMWS(FakeMWS):
        async def chat_simple(self, model: str, system: str, user: str) -> str:
            self.calls.append({"model": model, "system": system, "user": user})
            if "research planner" in system:
                planner_started.set()
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    planner_cancelled.set()
                    raise
            return self.final_answer

    mws = SlowPlannerMWS()
    generator = _run_pipeline(
        "run id query",
        mws,
        settings,
        search_svc=FakeSearchService({}),
        parser_svc=FakeParserService({}),
        registry=research_module.ResearchStreamRegistry(),
    )

    first_event = parse_sse(await anext(generator))
    await asyncio.wait_for(planner_started.wait(), timeout=1)
    await generator.aclose()
    await asyncio.wait_for(planner_cancelled.wait(), timeout=1)

    assert first_event[0] == "progress"
    assert first_event[1]["step"] == 0
    assert first_event[1]["run_id"]


@pytest.mark.asyncio
async def test_run_pipeline_cancels_background_runner_when_client_closes() -> None:
    settings = make_settings(RESEARCH_SUBQUERY_TIMEOUT=30)
    planner_cancelled = asyncio.Event()

    class SlowPlannerMWS(FakeMWS):
        async def chat_simple(self, model: str, system: str, user: str) -> str:
            self.calls.append({"model": model, "system": system, "user": user})
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                planner_cancelled.set()
                raise
            if "research planner" in system:
                return json.dumps(["slow-sub-query"])
            return self.final_answer

    generator = _run_pipeline(
        "cancel this research",
        SlowPlannerMWS(),
        settings,
        search_svc=FakeSearchService({}),
        parser_svc=FakeParserService({}),
    )

    first_event = await anext(generator)
    assert parse_sse(first_event)[0] == "progress"

    loop = asyncio.get_running_loop()
    started = loop.time()
    await generator.aclose()
    elapsed = loop.time() - started

    assert elapsed < 0.5
    await asyncio.wait_for(planner_cancelled.wait(), timeout=1)


@pytest.mark.asyncio
async def test_run_pipeline_cancels_runner_when_request_disconnects() -> None:
    settings = make_settings(RESEARCH_SUBQUERY_TIMEOUT=30)
    planner_started = asyncio.Event()
    planner_cancelled = asyncio.Event()
    request = FakeDisconnectRequest()
    registry = research_module.ResearchStreamRegistry()

    class SlowPlannerMWS(FakeMWS):
        async def chat_simple(self, model: str, system: str, user: str) -> str:
            self.calls.append({"model": model, "system": system, "user": user})
            try:
                planner_started.set()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                planner_cancelled.set()
                raise

    generator = _run_pipeline(
        "disconnect this research",
        SlowPlannerMWS(),
        settings,
        request=request,
        search_svc=FakeSearchService({}),
        parser_svc=FakeParserService({}),
        registry=registry,
    )

    first_event = await anext(generator)
    assert parse_sse(first_event)[0] == "progress"

    await asyncio.wait_for(planner_started.wait(), timeout=1)
    request.disconnected = True
    await asyncio.wait_for(planner_cancelled.wait(), timeout=1)
    await generator.aclose()


@pytest.mark.asyncio
async def test_cancel_research_endpoint_stops_active_run() -> None:
    settings = make_settings(RESEARCH_SUBQUERY_TIMEOUT=30)
    planner_started = asyncio.Event()
    planner_cancelled = asyncio.Event()
    registry = research_module.ResearchStreamRegistry()

    class SlowPlannerMWS(FakeMWS):
        async def chat_simple(self, model: str, system: str, user: str) -> str:
            self.calls.append({"model": model, "system": system, "user": user})
            try:
                planner_started.set()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                planner_cancelled.set()
                raise

    generator = _run_pipeline(
        "cancel endpoint research",
        SlowPlannerMWS(),
        settings,
        search_svc=FakeSearchService({}),
        parser_svc=FakeParserService({}),
        registry=registry,
    )

    first_event = parse_sse(await anext(generator))
    run_id = first_event[1]["run_id"]
    await asyncio.wait_for(planner_started.wait(), timeout=1)
    payload = await research_module.cancel_research(run_id, registry=registry)

    assert payload["status"] == "ok"
    assert payload["run_id"] == run_id
    await asyncio.wait_for(planner_cancelled.wait(), timeout=1)
    await generator.aclose()


@pytest.mark.asyncio
async def test_proxy_auto_route_returns_research_completion_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    fake_router = FakeRouterClient(
        RouteResult("deep_research", settings.MODEL_RESEARCH_SYNTHESIS, 0.91, 2)
    )
    fake_mws = FakeMWS()

    async def fake_run_research(query: str, mws: FakeMWS, passed_settings: Settings) -> dict:
        assert query == "research this topic"
        assert mws is fake_mws
        assert passed_settings is settings
        return {
            "status": "ok",
            "query": query,
            "answer": "Research answer with [S1].",
            "sub_queries": ["q1", "q2"],
            "sources": [{"source_id": "S1", "title": "Title", "url": "https://example.test/1"}],
            "stats": {"pages_fetched": 1, "sources_used": 1},
            "model": settings.MODEL_RESEARCH_SYNTHESIS,
        }

    async def fake_log_route(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(proxy_module, "run_research", fake_run_research)
    monkeypatch.setattr(proxy_module, "_log_route", fake_log_route)

    request = ChatCompletionRequest(
        model="auto",
        messages=[Message(role="user", content="research this topic")],
        stream=False,
        use_memory=False,
        user="user-1",
    )

    response = await proxy_module.chat_completions(
        request,
        mws=fake_mws,
        router_client=fake_router,
        settings=settings,
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["choices"][0]["message"]["content"] == "Research answer with [S1]."
    assert payload["model"] == settings.MODEL_RESEARCH_SYNTHESIS
    assert payload["sources"][0]["source_id"] == "S1"
    assert payload["sub_queries"] == ["q1", "q2"]
    assert not fake_mws.chat_calls


@pytest.mark.asyncio
async def test_proxy_auto_route_streams_research_progress_for_stream_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = make_settings()
    fake_router = FakeRouterClient(
        RouteResult("deep_research", settings.MODEL_RESEARCH_SYNTHESIS, 0.93, 2)
    )
    fake_mws = FakeMWS()

    async def fake_log_route(*args, **kwargs) -> None:
        return None

    async def fake_pipeline(
        query: str,
        mws: FakeMWS,
        passed_settings: Settings,
        request=None,
    ):
        assert query == "research this topic"
        assert mws is fake_mws
        assert passed_settings is settings
        yield (
            'event: progress\n'
            'data: {"step": 0, "message": "Research run started.", "run_id": "run-123"}\n\n'
        )
        yield (
            'event: done\n'
            'data: {"answer": "Research answer with [S1].", '
            '"run_id": "run-123", '
            '"model": "synthesis-model", '
            '"sources": [{"source_id": "S1", "title": "Title", "url": "https://example.test/1"}], '
            '"sub_queries": ["q1"], '
            '"stats": {"pages_fetched": 1, "sources_used": 1}}\n\n'
        )

    monkeypatch.setattr(proxy_module, "_log_route", fake_log_route)
    monkeypatch.setattr(proxy_module, "_run_pipeline", fake_pipeline)

    request = ChatCompletionRequest(
        model="auto",
        messages=[Message(role="user", content="research this topic")],
        stream=True,
        use_memory=False,
        user="user-3",
    )

    response = await proxy_module.chat_completions(
        request,
        mws=fake_mws,
        router_client=fake_router,
        settings=settings,
    )

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))

    payload = "".join(chunks)
    assert response.media_type == "text/event-stream"
    assert '"research_event": "progress"' in payload
    assert '"research_event": "done"' in payload
    assert '"run_id": "run-123"' in payload
    assert 'Research answer with [S1].' in payload
    assert 'data: [DONE]' in payload


@pytest.mark.asyncio
async def test_proxy_keeps_manual_model_on_normal_chat_path(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    fake_router = FakeRouterClient(
        RouteResult("deep_research", settings.MODEL_RESEARCH_SYNTHESIS, 0.88, 2)
    )
    fake_mws = FakeMWS(
        chat_response={
            "id": "chatcmpl-manual",
            "model": "manual-model",
            "choices": [{"message": {"content": "Manual model answer"}}],
        }
    )

    async def fake_log_route(*args, **kwargs) -> None:
        return None

    async def should_not_run(*args, **kwargs):
        raise AssertionError("run_research should not be used for explicit models")

    monkeypatch.setattr(proxy_module, "_log_route", fake_log_route)
    monkeypatch.setattr(proxy_module, "run_research", should_not_run)

    request = ChatCompletionRequest(
        model="manual-model",
        messages=[Message(role="user", content="research this topic")],
        stream=False,
        use_memory=False,
        user="user-2",
    )

    response = await proxy_module.chat_completions(
        request,
        mws=fake_mws,
        router_client=fake_router,
        settings=settings,
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert payload["choices"][0]["message"]["content"] == "Manual model answer"
    assert len(fake_mws.chat_calls) == 1
    assert fake_mws.chat_calls[0].model == "manual-model"


@pytest.mark.asyncio
async def test_proxy_maps_research_errors_to_specific_http_status(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    fake_router = FakeRouterClient(
        RouteResult("deep_research", settings.MODEL_RESEARCH_SYNTHESIS, 0.91, 2)
    )
    fake_mws = FakeMWS()

    async def fake_run_research(query: str, mws: FakeMWS, passed_settings: Settings) -> dict:
        assert query == "research this topic"
        assert mws is fake_mws
        assert passed_settings is settings
        return {
            "status": "error",
            "message": "Timed out while synthesizing the final answer.",
            "error_code": "synthesis_timeout",
            "sub_queries": ["q1"],
            "sources": [],
            "stats": {"pages_fetched": 0, "sources_used": 0},
            "model": settings.MODEL_RESEARCH_SYNTHESIS,
        }

    async def fake_log_route(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(proxy_module, "run_research", fake_run_research)
    monkeypatch.setattr(proxy_module, "_log_route", fake_log_route)

    request = ChatCompletionRequest(
        model="auto",
        messages=[Message(role="user", content="research this topic")],
        stream=False,
        use_memory=False,
        user="user-4",
    )

    response = await proxy_module.chat_completions(
        request,
        mws=fake_mws,
        router_client=fake_router,
        settings=settings,
    )
    payload = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 504
    assert payload["error"]["code"] == "synthesis_timeout"
    assert payload["error"]["message"] == "Timed out while synthesizing the final answer."


@pytest.mark.asyncio
async def test_proxy_streams_research_error_with_run_id_and_code(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = make_settings()
    fake_router = FakeRouterClient(
        RouteResult("deep_research", settings.MODEL_RESEARCH_SYNTHESIS, 0.93, 2)
    )
    fake_mws = FakeMWS()

    async def fake_log_route(*args, **kwargs) -> None:
        return None

    async def fake_pipeline(
        query: str,
        mws: FakeMWS,
        passed_settings: Settings,
        request=None,
    ):
        assert query == "research this topic"
        assert mws is fake_mws
        assert passed_settings is settings
        yield (
            'event: progress\n'
            'data: {"step": 0, "message": "Research run started.", "run_id": "run-error"}\n\n'
        )
        yield (
            'event: error\n'
            'data: {"message": "Timed out while generating research sub-queries.", '
            '"error_code": "planner_timeout", '
            '"run_id": "run-error", '
            '"sources": [], '
            '"sub_queries": [], '
            '"stats": {"pages_fetched": 0, "sources_used": 0}}\n\n'
        )

    monkeypatch.setattr(proxy_module, "_log_route", fake_log_route)
    monkeypatch.setattr(proxy_module, "_run_pipeline", fake_pipeline)

    request = ChatCompletionRequest(
        model="auto",
        messages=[Message(role="user", content="research this topic")],
        stream=True,
        use_memory=False,
        user="user-5",
    )

    response = await proxy_module.chat_completions(
        request,
        mws=fake_mws,
        router_client=fake_router,
        settings=settings,
    )

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))

    payload = "".join(chunks)
    assert '"research_event": "error"' in payload
    assert '"code": "planner_timeout"' in payload
    assert '"run_id": "run-error"' in payload
    assert 'data: [DONE]' in payload
