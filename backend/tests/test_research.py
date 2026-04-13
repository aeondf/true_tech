from __future__ import annotations

import asyncio
import json

import pytest

from app.api.v1 import proxy as proxy_module
from app.api.v1.research import _run_pipeline, run_research
from app.config import Settings
from app.models.mws import ChatCompletionRequest, Message
from app.services.router_client import RouteResult


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
    assert result["model"] == settings.MODEL_RESEARCH_SYNTHESIS
    assert result["sources"]
    assert result["stats"]["pages_fetched"] == 3
    assert result["stats"]["sources_used"] == 3


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

    async def fake_pipeline(query: str, mws: FakeMWS, passed_settings: Settings):
        assert query == "research this topic"
        assert mws is fake_mws
        assert passed_settings is settings
        yield (
            'event: progress\n'
            'data: {"step": 1, "message": "Planning"}\n\n'
        )
        yield (
            'event: done\n'
            'data: {"answer": "Research answer with [S1].", '
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
