from __future__ import annotations

"""Deep Research pipeline with cancellable runs and disconnect-aware SSE."""

import asyncio
import contextlib
import json
import logging
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.mws_client import MWSClient, get_mws_client
from app.services.web_parser import WebParserService, build_web_parser_service
from app.services.web_search import WebSearchService, build_web_search_service

logger = logging.getLogger(__name__)

router = APIRouter()

ProgressEmitter = Callable[[str, dict], Awaitable[None]]
_RESEARCH_LIMITERS: dict[tuple[int, int], asyncio.Semaphore] = {}
_DISCONNECT_POLL_INTERVAL = 0.2


class ResearchRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


@dataclass(slots=True)
class ResearchSource:
    query: str
    query_order: int
    search_rank: int
    title: str
    url: str
    snippet: str
    text: str
    source_id: str = ""


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _trim(text: str | None, limit: int) -> str:
    return (text or "").strip()[:limit]


def _parse_json_array(raw: str) -> list[str]:
    if not raw:
        return []
    match = re.search(r"\[[\s\S]*\]", raw)
    candidate = match.group(0) if match else raw
    try:
        parsed = json.loads(candidate)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _normalize_sub_queries(raw_queries: list[str], query: str, limit: int) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for candidate in [*raw_queries, query]:
        clean = re.sub(r"\s+", " ", candidate or "").strip()
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(clean)
        if len(normalized) >= limit:
            break

    return normalized or [query]


def _source_excerpt(text: str, limit: int = 280) -> str:
    excerpt = re.sub(r"\s+", " ", (text or "").strip())
    return excerpt[:limit]


def _serialize_source(source: ResearchSource) -> dict:
    return {
        "source_id": source.source_id,
        "query": source.query,
        "title": source.title,
        "url": source.url,
        "snippet": source.snippet,
        "excerpt": _source_excerpt(source.text),
    }


def _build_error_result(
    query: str,
    message: str,
    *,
    error_code: str = "research_failed",
    sub_queries: list[str] | None = None,
    sources: list[ResearchSource] | None = None,
    stats: dict | None = None,
    model: str | None = None,
) -> dict:
    return {
        "status": "error",
        "query": query,
        "message": message,
        "error_code": error_code,
        "sub_queries": sub_queries or [],
        "sources": [_serialize_source(source) for source in (sources or [])],
        "stats": stats or {
            "queries_total": 0,
            "queries_completed": 0,
            "pages_fetched": 0,
            "sources_used": 0,
            "timed_out": False,
        },
        "model": model,
    }


def _build_done_result(
    query: str,
    answer: str,
    *,
    sub_queries: list[str],
    sources: list[ResearchSource],
    stats: dict,
    model: str,
) -> dict:
    return {
        "status": "ok",
        "query": query,
        "answer": answer,
        "sub_queries": sub_queries,
        "sources": [_serialize_source(source) for source in sources],
        "stats": stats,
        "model": model,
    }


async def _raise_if_cancelled(cancel_event: asyncio.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise asyncio.CancelledError()


async def _maybe_emit(
    emit: ProgressEmitter | None,
    event: str,
    data: dict,
    *,
    cancel_event: asyncio.Event | None = None,
) -> None:
    await _raise_if_cancelled(cancel_event)
    if emit:
        await emit(event, data)


def _get_research_limiter(limit: int) -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    normalized_limit = max(1, limit)
    key = (id(loop), normalized_limit)
    limiter = _RESEARCH_LIMITERS.get(key)
    if limiter is None:
        limiter = asyncio.Semaphore(normalized_limit)
        _RESEARCH_LIMITERS[key] = limiter
    return limiter


@asynccontextmanager
async def _research_slot(settings: Settings):
    limiter = _get_research_limiter(settings.RESEARCH_MAX_ACTIVE_RUNS)
    await limiter.acquire()
    try:
        yield
    finally:
        limiter.release()


async def _generate_sub_queries(
    query: str,
    mws: MWSClient,
    settings: Settings,
    *,
    cancel_event: asyncio.Event | None = None,
) -> list[str]:
    await _raise_if_cancelled(cancel_event)
    raw = await asyncio.wait_for(
        mws.chat_simple(
            model=settings.MODEL_RESEARCH_QUERY,
            system=(
                "You are a research planner. Generate concise search-engine sub-queries "
                "that help investigate the user's topic from different angles. "
                "Return ONLY a JSON array of strings."
            ),
            user=query,
        ),
        timeout=settings.RESEARCH_SUBQUERY_TIMEOUT,
    )
    await _raise_if_cancelled(cancel_event)
    parsed = _parse_json_array(raw)
    return _normalize_sub_queries(parsed, query, settings.RESEARCH_SUBQUERY_COUNT)


async def _parse_search_result(
    result: dict,
    *,
    query: str,
    query_order: int,
    search_rank: int,
    parser_svc: WebParserService,
    parse_timeout: int,
    max_chars: int,
    http_sem: asyncio.Semaphore,
    cancel_event: asyncio.Event | None = None,
) -> ResearchSource | None:
    url = _trim(result.get("url"), 1000)
    if not url:
        return None

    await _raise_if_cancelled(cancel_event)
    async with http_sem:
        await _raise_if_cancelled(cancel_event)
        try:
            parsed = await asyncio.wait_for(
                parser_svc.parse(url),
                timeout=parse_timeout,
            )
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            logger.debug("Parse timeout for url=%s", url)
            parsed = {"url": url, "title": "", "text": "", "links": []}
        except Exception as exc:
            logger.debug("Parse error for url=%s: %s", url, exc)
            parsed = {"url": url, "title": "", "text": "", "links": []}

    await _raise_if_cancelled(cancel_event)
    title = _trim(parsed.get("title") or result.get("title") or url, 300)
    snippet = _trim(result.get("snippet"), 500)
    text = _trim(parsed.get("text") or snippet, max_chars)
    if not text:
        return None

    return ResearchSource(
        query=query,
        query_order=query_order,
        search_rank=search_rank,
        title=title,
        url=url,
        snippet=snippet,
        text=text,
    )


async def _fetch_sources_for_query(
    query: str,
    *,
    query_order: int,
    search_svc: WebSearchService,
    parser_svc: WebParserService,
    settings: Settings,
    http_sem: asyncio.Semaphore,
    cancel_event: asyncio.Event | None = None,
) -> list[ResearchSource]:
    await _raise_if_cancelled(cancel_event)
    try:
        results = await asyncio.wait_for(
            search_svc.search(query, max_results=settings.RESEARCH_SEARCH_RESULTS),
            timeout=settings.RESEARCH_SEARCH_TIMEOUT,
        )
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        logger.debug("Search timeout for query=%r", query)
        return []
    except Exception as exc:
        logger.debug("Search error for query=%r: %s", query, exc)
        return []

    await _raise_if_cancelled(cancel_event)
    tasks = [
        _parse_search_result(
            result,
            query=query,
            query_order=query_order,
            search_rank=index,
            parser_svc=parser_svc,
            parse_timeout=settings.RESEARCH_PARSE_TIMEOUT,
            max_chars=settings.RESEARCH_MAX_SOURCE_TEXT_CHARS,
            http_sem=http_sem,
            cancel_event=cancel_event,
        )
        for index, result in enumerate(results)
        if result.get("url")
    ]

    if not tasks:
        return []

    pages = await asyncio.gather(*tasks, return_exceptions=True)
    await _raise_if_cancelled(cancel_event)
    sources: list[ResearchSource] = []
    for page in pages:
        if isinstance(page, ResearchSource):
            sources.append(page)
    return sources


async def _collect_sources(
    sub_queries: list[str],
    *,
    search_svc: WebSearchService,
    parser_svc: WebParserService,
    settings: Settings,
    emit: ProgressEmitter | None = None,
    cancel_event: asyncio.Event | None = None,
) -> tuple[list[ResearchSource], dict]:
    http_sem = asyncio.Semaphore(settings.RESEARCH_CONCURRENCY)

    async def fetch_bundle(query: str, index: int) -> tuple[str, list[ResearchSource]]:
        return query, await _fetch_sources_for_query(
            query,
            query_order=index,
            search_svc=search_svc,
            parser_svc=parser_svc,
            settings=settings,
            http_sem=http_sem,
            cancel_event=cancel_event,
        )

    tasks = [
        asyncio.create_task(fetch_bundle(query, index), name=f"research-fetch-{index}")
        for index, query in enumerate(sub_queries)
    ]

    sources_by_url: dict[str, ResearchSource] = {}
    completed = 0
    timed_out = False
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.RESEARCH_FETCH_TOTAL_TIMEOUT
    pending = set(tasks)

    try:
        while pending:
            await _raise_if_cancelled(cancel_event)
            remaining = deadline - loop.time()
            if remaining <= 0:
                timed_out = True
                logger.warning("Research fetch timeout hit for sub_queries=%r", sub_queries)
                break

            done, pending = await asyncio.wait(
                pending,
                timeout=remaining,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                timed_out = True
                logger.warning("Research fetch timeout hit for sub_queries=%r", sub_queries)
                break

            for task in done:
                try:
                    query, query_sources = task.result()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.debug("Research bundle failed: %s", exc)
                    continue

                completed += 1

                for source in query_sources:
                    previous = sources_by_url.get(source.url)
                    if previous is None or len(source.text) > len(previous.text):
                        sources_by_url[source.url] = source

                await _maybe_emit(
                    emit,
                    "progress",
                    {
                        "step": 3,
                        "query": query,
                        "queries_completed": completed,
                        "queries_total": len(sub_queries),
                        "sources_total": len(sources_by_url),
                        "sources_found": len(query_sources),
                    },
                    cancel_event=cancel_event,
                )
    finally:
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    ordered_sources = sorted(
        sources_by_url.values(),
        key=lambda source: (source.query_order, source.search_rank, -len(source.text)),
    )

    stats = {
        "queries_total": len(sub_queries),
        "queries_completed": completed,
        "pages_fetched": len(ordered_sources),
        "sources_used": 0,
        "timed_out": timed_out,
    }
    return ordered_sources, stats


def _build_synthesis_context(
    sources: list[ResearchSource],
    settings: Settings,
) -> tuple[list[ResearchSource], str]:
    selected = sources[:settings.RESEARCH_MAX_SOURCES]
    total_chars = 0
    context_parts: list[str] = []
    used_sources: list[ResearchSource] = []

    for index, source in enumerate(selected, start=1):
        source.source_id = f"S{index}"
        block = "\n".join([
            f"[{source.source_id}]",
            f"Title: {source.title}",
            f"URL: {source.url}",
            f"Search query: {source.query}",
            f"Snippet: {source.snippet or '-'}",
            f"Content:\n{source.text}",
        ])
        if total_chars + len(block) > settings.RESEARCH_MAX_CONTEXT_CHARS and used_sources:
            break
        context_parts.append(block)
        used_sources.append(source)
        total_chars += len(block)

    if not used_sources:
        return [], "No reliable web sources were collected."
    return used_sources, "\n\n---\n\n".join(context_parts)


async def _synthesize_answer(
    query: str,
    context: str,
    *,
    mws: MWSClient,
    settings: Settings,
    cancel_event: asyncio.Event | None = None,
) -> str:
    await _raise_if_cancelled(cancel_event)
    answer = await asyncio.wait_for(
        mws.chat_simple(
            model=settings.MODEL_RESEARCH_SYNTHESIS,
            system=(
                "You are a research analyst. Write a structured answer in the language of the user. "
                "Use only the provided sources. Cite claims inline using source ids like [S1]. "
                "If the sources are insufficient, say so explicitly instead of inventing facts."
            ),
            user=f"Question: {query}\n\nSources:\n{context}",
        ),
        timeout=settings.RESEARCH_SYNTHESIS_TIMEOUT,
    )
    await _raise_if_cancelled(cancel_event)
    return answer


async def run_research(
    query: str,
    mws: MWSClient,
    settings: Settings,
    *,
    search_svc: WebSearchService | None = None,
    parser_svc: WebParserService | None = None,
    emit: ProgressEmitter | None = None,
    cancel_event: asyncio.Event | None = None,
) -> dict:
    query = (query or "").strip()
    if not query:
        return _build_error_result(
            query,
            "Empty research query.",
            error_code="empty_query",
        )

    search_svc = search_svc or build_web_search_service(settings)
    parser_svc = parser_svc or build_web_parser_service(settings)
    sources: list[ResearchSource] = []
    sub_queries = [query]
    stats = {
        "queries_total": 0,
        "queries_completed": 0,
        "pages_fetched": 0,
        "sources_used": 0,
        "timed_out": False,
    }

    try:
        async with _research_slot(settings):
            await _raise_if_cancelled(cancel_event)
            await _maybe_emit(
                emit,
                "progress",
                {"step": 1, "message": "Generating sub-queries..."},
                cancel_event=cancel_event,
            )
            try:
                sub_queries = await _generate_sub_queries(
                    query,
                    mws,
                    settings,
                    cancel_event=cancel_event,
                )
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                return _build_error_result(
                    query,
                    "Timed out while generating research sub-queries.",
                    error_code="planner_timeout",
                )
            except Exception as exc:
                logger.warning("Failed to generate sub-queries, falling back to original query: %s", exc)
                sub_queries = [query]

            await _maybe_emit(
                emit,
                "progress",
                {"step": 2, "sub_queries": sub_queries},
                cancel_event=cancel_event,
            )
            await _maybe_emit(
                emit,
                "progress",
                {"step": 3, "message": "Searching and parsing sources..."},
                cancel_event=cancel_event,
            )

            sources, stats = await _collect_sources(
                sub_queries,
                search_svc=search_svc,
                parser_svc=parser_svc,
                settings=settings,
                emit=emit,
                cancel_event=cancel_event,
            )

            await _maybe_emit(
                emit,
                "progress",
                {
                    "step": 4,
                    "pages_fetched": stats["pages_fetched"],
                    "timed_out": stats["timed_out"],
                },
                cancel_event=cancel_event,
            )

            await _maybe_emit(
                emit,
                "progress",
                {"step": 5, "message": "Synthesizing final answer..."},
                cancel_event=cancel_event,
            )
            used_sources, context = _build_synthesis_context(sources, settings)
            stats["sources_used"] = len(used_sources)

            try:
                answer = await _synthesize_answer(
                    query,
                    context,
                    mws=mws,
                    settings=settings,
                    cancel_event=cancel_event,
                )
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError:
                return _build_error_result(
                    query,
                    "Timed out while synthesizing the final answer.",
                    error_code="synthesis_timeout",
                    sub_queries=sub_queries,
                    sources=used_sources,
                    stats=stats,
                    model=settings.MODEL_RESEARCH_SYNTHESIS,
                )

            return _build_done_result(
                query,
                answer,
                sub_queries=sub_queries,
                sources=used_sources,
                stats=stats,
                model=settings.MODEL_RESEARCH_SYNTHESIS,
            )
    except asyncio.CancelledError:
        logger.info("Research pipeline cancelled for query=%r", query)
        raise
    except Exception as exc:
        logger.exception("Unexpected error in research pipeline for query=%r", query)
        return _build_error_result(
            query,
            f"Research failed: {exc}",
            error_code="unexpected_error",
            sub_queries=sub_queries,
            sources=sources,
            stats=stats,
            model=settings.MODEL_RESEARCH_SYNTHESIS,
        )


class ResearchStreamRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, ResearchStreamRun] = {}

    def create_run(
        self,
        *,
        query: str,
        mws: MWSClient,
        settings: Settings,
        search_svc: WebSearchService | None = None,
        parser_svc: WebParserService | None = None,
    ) -> "ResearchStreamRun":
        run = ResearchStreamRun(
            registry=self,
            query=query,
            mws=mws,
            settings=settings,
            search_svc=search_svc,
            parser_svc=parser_svc,
        )
        self._runs[run.run_id] = run
        return run

    def cancel(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run is None:
            return False
        run.cancel("api_cancel")
        return True

    def discard(self, run_id: str) -> None:
        self._runs.pop(run_id, None)


class ResearchStreamRun:
    def __init__(
        self,
        *,
        registry: ResearchStreamRegistry,
        query: str,
        mws: MWSClient,
        settings: Settings,
        search_svc: WebSearchService | None = None,
        parser_svc: WebParserService | None = None,
    ) -> None:
        self.registry = registry
        self.run_id = uuid.uuid4().hex
        self.query = query
        self.mws = mws
        self.settings = settings
        self.search_svc = search_svc
        self.parser_svc = parser_svc
        self.cancel_event = asyncio.Event()
        self._queue: asyncio.Queue[str | object] = asyncio.Queue()
        self._sentinel = object()
        self._runner_task: asyncio.Task | None = None
        self._disconnect_task: asyncio.Task | None = None

    def cancel(self, reason: str = "cancelled") -> None:
        if self.cancel_event.is_set():
            return
        logger.info("Cancelling research run_id=%s reason=%s", self.run_id, reason)
        self.cancel_event.set()
        if self._runner_task and not self._runner_task.done():
            self._runner_task.cancel()
        if self._disconnect_task and not self._disconnect_task.done():
            self._disconnect_task.cancel()

    async def _emit(self, event: str, data: dict) -> None:
        payload = dict(data)
        payload.setdefault("run_id", self.run_id)
        await self._queue.put(_sse(event, payload))

    async def _watch_disconnect(self, request: Request) -> None:
        try:
            while not self.cancel_event.is_set():
                if await request.is_disconnected():
                    self.cancel("client_disconnect")
                    return
                await asyncio.sleep(_DISCONNECT_POLL_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("Disconnect watcher failed for run_id=%s: %s", self.run_id, exc)

    async def _runner(self) -> None:
        try:
            result = await run_research(
                self.query,
                self.mws,
                self.settings,
                search_svc=self.search_svc,
                parser_svc=self.parser_svc,
                emit=self._emit,
                cancel_event=self.cancel_event,
            )
            if self.cancel_event.is_set():
                return
            result["run_id"] = self.run_id
            if result["status"] == "ok":
                await self._emit("done", result)
            else:
                await self._emit("error", result)
        except asyncio.CancelledError:
            logger.info("Research stream runner cancelled for run_id=%s", self.run_id)
            raise
        except Exception as exc:
            logger.exception("Unhandled research runner failure for run_id=%s", self.run_id)
            if not self.cancel_event.is_set():
                await self._emit(
                    "error",
                    _build_error_result(
                        self.query,
                        f"Research failed: {exc}",
                        error_code="unexpected_error",
                        model=self.settings.MODEL_RESEARCH_SYNTHESIS,
                    ),
                )
        finally:
            await self._queue.put(self._sentinel)

    async def stream(self, request: Request | None = None):
        await self._emit(
            "progress",
            {
                "step": 0,
                "message": "Research run started.",
                "query": self.query,
            },
        )
        self._runner_task = asyncio.create_task(self._runner(), name=f"research-run-{self.run_id}")
        if request is not None:
            self._disconnect_task = asyncio.create_task(
                self._watch_disconnect(request),
                name=f"research-disconnect-{self.run_id}",
            )

        try:
            while True:
                item = await self._queue.get()
                if item is self._sentinel:
                    break
                yield item
        finally:
            self.cancel("stream_closed")
            tasks = [task for task in (self._runner_task, self._disconnect_task) if task is not None]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self.registry.discard(self.run_id)


@lru_cache(maxsize=1)
def get_research_registry() -> ResearchStreamRegistry:
    return ResearchStreamRegistry()


async def _run_pipeline(
    query: str,
    mws: MWSClient,
    settings: Settings,
    *,
    request: Request | None = None,
    search_svc: WebSearchService | None = None,
    parser_svc: WebParserService | None = None,
    registry: ResearchStreamRegistry | None = None,
):
    run_registry = registry or get_research_registry()
    run = run_registry.create_run(
        query=query,
        mws=mws,
        settings=settings,
        search_svc=search_svc,
        parser_svc=parser_svc,
    )
    async for item in run.stream(request=request):
        yield item


@router.post("/research")
async def deep_research(
    req: ResearchRequest,
    request: Request,
    mws: MWSClient = Depends(get_mws_client),
    settings: Settings = Depends(get_settings),
):
    return StreamingResponse(
        _run_pipeline(req.query, mws, settings, request=request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/research/{run_id}/cancel")
async def cancel_research(
    run_id: str,
    registry: ResearchStreamRegistry = Depends(get_research_registry),
):
    cancelled = registry.cancel(run_id)
    return {"status": "ok", "run_id": run_id, "cancelled": cancelled}
