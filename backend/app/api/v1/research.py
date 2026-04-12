"""
Deep Research pipeline — full SSE streaming to client.

Steps:
  1. mws-gpt-alpha generates 5 sub-queries
  2. Parallel web-search + web-parse per sub-query (with semaphore)
  3. cotype-preview-32k synthesises final answer with citations
"""
import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.mws_client import MWSClient, get_mws_client
from app.services.web_search import WebSearchService
from app.services.web_parser import WebParserService

router = APIRouter()

# Limit concurrent external HTTP requests to avoid resource exhaustion
_http_sem = asyncio.Semaphore(4)


class ResearchRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _run_pipeline(query: str, mws: MWSClient, settings: Settings):
    search_svc = WebSearchService()
    parser_svc = WebParserService()

    try:
        # ── Step 1: generate sub-queries (timeout 30s) ──────────────
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
                timeout=30,
            )
        except asyncio.TimeoutError:
            yield _sse("error", {"message": "Таймаут генерации подзапросов"})
            return

        try:
            sub_queries: list[str] = json.loads(raw)[:5]
        except Exception:
            sub_queries = [query]

        yield _sse("progress", {"step": 2, "sub_queries": sub_queries})

        # ── Step 2: parallel search + parse (semaphore-limited) ─────
        yield _sse("progress", {"step": 3, "message": "Ищу и парсю страницы…"})

        async def parse_with_limit(url: str) -> dict:
            async with _http_sem:
                return await parser_svc.parse(url)

        async def fetch_one(q: str) -> list[str]:
            try:
                results = await asyncio.wait_for(
                    search_svc.search(q, max_results=3),
                    timeout=15,
                )
            except asyncio.TimeoutError:
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

        all_groups = await asyncio.wait_for(
            asyncio.gather(*[fetch_one(q) for q in sub_queries]),
            timeout=60,
        )
        all_texts = [t for group in all_groups for t in group]

        yield _sse("progress", {"step": 4, "pages_fetched": len(all_texts)})

        # ── Step 3: synthesise (timeout 60s) ─────────────────────────
        yield _sse("progress", {"step": 5, "message": "Синтезирую ответ…"})

        context = "\n\n---\n\n".join(all_texts[:10])
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
                timeout=60,
            )
        except asyncio.TimeoutError:
            yield _sse("error", {"message": "Таймаут синтеза ответа"})
            return

        yield _sse("done", {"answer": final})

    except asyncio.TimeoutError:
        yield _sse("error", {"message": "Общий таймаут исследования"})
    except Exception as e:
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
