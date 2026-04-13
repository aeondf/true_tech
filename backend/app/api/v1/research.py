"""
Deep Research pipeline — full SSE streaming to client.

Steps:
  1. mws-gpt-alpha generates 5 sub-queries
  2. Parallel web-search + web-parse per sub-query (with semaphore)
  3. cotype-preview-32k synthesises final answer with citations
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.mws_client import MWSClient, get_mws_client
from app.services.web_search import WebSearchService
from app.services.web_parser import WebParserService

logger = logging.getLogger(__name__)

router = APIRouter()

# Limit concurrent external HTTP requests to avoid resource exhaustion
# NOTE: semaphore is created per-request to avoid cross-request deadlocks
_SEM_LIMIT = 4
_PARSE_TIMEOUT = 12   # per-page parse timeout (web_parser has its own 15s httpx timeout)
_SEARCH_TIMEOUT = 15  # per sub-query search timeout
_FETCH_TOTAL_TIMEOUT = 90  # total timeout for all parallel fetches
_SUBQUERY_TIMEOUT = 30     # sub-query generation timeout
_SYNTHESIS_TIMEOUT = 120   # synthesis timeout (increased: MODEL_LONG can be slow)


class ResearchRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _run_pipeline(query: str, mws: MWSClient, settings: Settings):
    search_svc = WebSearchService()
    parser_svc = WebParserService()
    # Per-request semaphore — avoids cross-request deadlocks from global state
    http_sem = asyncio.Semaphore(_SEM_LIMIT)

    try:
        # ── Step 1: generate sub-queries ────────────────────────────
        yield _sse("progress", {"step": 1, "message": "Генерирую подзапросы…"})

        try:
            raw = await asyncio.wait_for(
                mws.chat_simple(
                    model=settings.MODEL_TEXT,
                    system=(
                        "Ты исследовательский ассистент. "
                        "Сгенерируй ровно 5 поисковых подзапросов для глубокого изучения темы. "
                        "Верни ТОЛЬКО JSON-массив строк без пояснений."
                    ),
                    user=query,
                ),
                timeout=_SUBQUERY_TIMEOUT,
            )
        except asyncio.TimeoutError:
            yield _sse("error", {"message": "Таймаут генерации подзапросов"})
            return

        try:
            sub_queries: list[str] = json.loads(raw)[:5]
            if not isinstance(sub_queries, list) or not sub_queries:
                raise ValueError("empty list")
        except Exception:
            logger.warning("Failed to parse sub-queries from LLM, falling back to original query. raw=%r", raw[:200])
            sub_queries = [query]

        yield _sse("progress", {"step": 2, "sub_queries": sub_queries})

        # ── Step 2: parallel search + parse (semaphore-limited) ─────
        yield _sse("progress", {"step": 3, "message": "Ищу и парсю страницы…"})

        async def parse_with_limit(url: str) -> dict:
            async with http_sem:
                try:
                    return await asyncio.wait_for(parser_svc.parse(url), timeout=_PARSE_TIMEOUT)
                except asyncio.TimeoutError:
                    logger.debug("Parse timeout for url=%s", url)
                    return {}
                except Exception as exc:
                    logger.debug("Parse error for url=%s: %s", url, exc)
                    return {}

        async def fetch_one(q: str) -> list[str]:
            try:
                results = await asyncio.wait_for(
                    search_svc.search(q, max_results=3),
                    timeout=_SEARCH_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.debug("Search timeout for query=%r", q)
                return []
            except Exception as exc:
                logger.debug("Search error for query=%r: %s", q, exc)
                return []
            tasks = [parse_with_limit(r["url"]) for r in results if r.get("url")]
            if not tasks:
                return []
            pages = await asyncio.gather(*tasks, return_exceptions=True)
            return [
                p["text"][:2000]
                for p in pages
                if isinstance(p, dict) and p.get("text")
            ]

        try:
            all_groups = await asyncio.wait_for(
                asyncio.gather(*[fetch_one(q) for q in sub_queries]),
                timeout=_FETCH_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Total fetch timeout hit for query=%r", query)
            all_groups = []

        all_texts = [t for group in all_groups for t in group]
        yield _sse("progress", {"step": 4, "pages_fetched": len(all_texts)})

        # ── Step 3: synthesise ────────────────────────────────────────
        yield _sse("progress", {"step": 5, "message": "Синтезирую ответ…"})

        context = "\n\n---\n\n".join(all_texts[:10]) if all_texts else "Источники не найдены."
        try:
            final = await asyncio.wait_for(
                mws.chat_simple(
                    model=settings.MODEL_LONG,
                    system=(
                        "Ты аналитик. На основе источников дай подробный структурированный ответ "
                        "с цитатами. Указывай из какого источника взята информация."
                    ),
                    user=f"Вопрос: {query}\n\nИсточники:\n{context}",
                ),
                timeout=_SYNTHESIS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            yield _sse("error", {"message": "Таймаут синтеза ответа"})
            return

        yield _sse("done", {"answer": final})

    except asyncio.TimeoutError:
        yield _sse("error", {"message": "Общий таймаут исследования"})
    except Exception as e:
        logger.exception("Unexpected error in research pipeline for query=%r", query)
        yield _sse("error", {"message": f"Ошибка: {str(e)}"})


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
