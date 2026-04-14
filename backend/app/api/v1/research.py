from __future__ import annotations

"""
Deep Research pipeline with structured sources and SSE progress.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.mws_client import MWSClient, get_mws_client
from app.services.web_parser import WebParserService
from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)

router = APIRouter()

ProgressEmitter = Callable[[str, dict], Awaitable[None]]


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
    sub_queries: list[str] | None = None,
    sources: list[ResearchSource] | None = None,
    stats: dict | None = None,
    model: str | None = None,
) -> dict:
    return {
        "status": "error",
        "query": query,
        "message": message,
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


async def _maybe_emit(emit: ProgressEmitter | None, event: str, data: dict) -> None:
    if emit:
        await emit(event, data)


async def _generate_sub_queries(query: str, mws: MWSClient, settings: Settings) -> list[str]:
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
) -> ResearchSource | None:
    url = _trim(result.get("url"), 1000)
    if not url:
        return None

    async with http_sem:
        try:
            parsed = await asyncio.wait_for(
                parser_svc.parse(url),
                timeout=parse_timeout,
            )
        except asyncio.TimeoutError:
            logger.debug("Parse timeout for url=%s", url)
            parsed = {"url": url, "title": "", "text": "", "links": []}
        except Exception as exc:
            logger.debug("Parse error for url=%s: %s", url, exc)
            parsed = {"url": url, "title": "", "text": "", "links": []}

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
) -> list[ResearchSource]:
    try:
        results = await asyncio.wait_for(
            search_svc.search(query, max_results=settings.RESEARCH_SEARCH_RESULTS),
            timeout=settings.RESEARCH_SEARCH_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.debug("Search timeout for query=%r", query)
        return []
    except Exception as exc:
        logger.debug("Search error for query=%r: %s", query, exc)
        return []

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
        )
        for index, result in enumerate(results)
        if result.get("url")
    ]

    if not tasks:
        return []

    pages = await asyncio.gather(*tasks, return_exceptions=True)
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
        )

    tasks = [
        asyncio.create_task(fetch_bundle(query, index))
        for index, query in enumerate(sub_queries)
    ]

    sources_by_url: dict[str, ResearchSource] = {}
    completed = 0
    timed_out = False

    async def collect_completed_tasks() -> None:
        nonlocal completed
        for task in asyncio.as_completed(tasks):
            query, query_sources = await task
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
            )

    try:
        await asyncio.wait_for(
            collect_completed_tasks(),
            timeout=settings.RESEARCH_FETCH_TOTAL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        timed_out = True
        logger.warning("Research fetch timeout hit for sub_queries=%r", sub_queries)
    finally:
        for pending in tasks:
            if not pending.done():
                pending.cancel()
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
            f"Snippet: {source.snippet or '—'}",
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
) -> str:
    return await asyncio.wait_for(
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


async def run_research(
    query: str,
    mws: MWSClient,
    settings: Settings,
    *,
    search_svc: WebSearchService | None = None,
    parser_svc: WebParserService | None = None,
    emit: ProgressEmitter | None = None,
) -> dict:
    query = (query or "").strip()
    if not query:
        return _build_error_result(query, "Пустой запрос для исследования.")

    search_svc = search_svc or WebSearchService()
    parser_svc = parser_svc or WebParserService()
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
        await _maybe_emit(emit, "progress", {"step": 1, "message": "Генерирую подзапросы..."})
        try:
            sub_queries = await _generate_sub_queries(query, mws, settings)
        except asyncio.TimeoutError:
            return _build_error_result(query, "Таймаут генерации подзапросов.")
        except Exception as exc:
            logger.warning("Failed to generate sub-queries, falling back to original query: %s", exc)
            sub_queries = [query]

        await _maybe_emit(emit, "progress", {"step": 2, "sub_queries": sub_queries})
        await _maybe_emit(emit, "progress", {"step": 3, "message": "Ищу и парсю источники..."})

        sources, stats = await _collect_sources(
            sub_queries,
            search_svc=search_svc,
            parser_svc=parser_svc,
            settings=settings,
            emit=emit,
        )

        await _maybe_emit(
            emit,
            "progress",
            {
                "step": 4,
                "pages_fetched": stats["pages_fetched"],
                "timed_out": stats["timed_out"],
            },
        )

        await _maybe_emit(emit, "progress", {"step": 5, "message": "Синтезирую финальный ответ..."})
        used_sources, context = _build_synthesis_context(sources, settings)
        stats["sources_used"] = len(used_sources)

        try:
            answer = await _synthesize_answer(query, context, mws=mws, settings=settings)
        except asyncio.TimeoutError:
            return _build_error_result(
                query,
                "Таймаут синтеза финального ответа.",
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
    except Exception as exc:
        logger.exception("Unexpected error in research pipeline for query=%r", query)
        return _build_error_result(
            query,
            f"Ошибка исследования: {exc}",
            sub_queries=sub_queries,
            sources=sources,
            stats=stats,
            model=settings.MODEL_RESEARCH_SYNTHESIS,
        )


async def _run_pipeline(
    query: str,
    mws: MWSClient,
    settings: Settings,
    *,
    search_svc: WebSearchService | None = None,
    parser_svc: WebParserService | None = None,
):
    queue: asyncio.Queue[str | object] = asyncio.Queue()
    sentinel = object()

    async def emit(event: str, data: dict) -> None:
        await queue.put(_sse(event, data))

    async def runner() -> None:
        try:
            result = await run_research(
                query,
                mws,
                settings,
                search_svc=search_svc,
                parser_svc=parser_svc,
                emit=emit,
            )
            if result["status"] == "ok":
                await emit("done", result)
            else:
                await emit("error", result)
        finally:
            await queue.put(sentinel)

    task = asyncio.create_task(runner())
    try:
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            yield item
    finally:
        await task


@router.post("/research")
async def deep_research(
    req: ResearchRequest,
    mws: MWSClient = Depends(get_mws_client),
    settings: Settings = Depends(get_settings),
):
    return StreamingResponse(
        _run_pipeline(req.query, mws, settings),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
