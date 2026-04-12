from __future__ import annotations

"""
CascadeRouter — выполняет несколько инструментов параллельно за один запрос.

Когда роутер возвращает task_type с несколькими tools (например web_search + web_parse),
этот сервис запускает их одновременно и возвращает объединённый контекст.

Результат подкладывается в system-промпт перед отправкой в LLM.
"""

import asyncio
from fastapi import Depends

from app.models.mws import ChatCompletionRequest, Message
from app.services.web_search import WebSearchService
from app.services.web_parser import WebParserService


class CascadeRouter:
    async def run(
        self,
        request: ChatCompletionRequest,
        tools: list[str],
        query: str,
    ) -> ChatCompletionRequest:
        tool_set = set(tools)

        if not tool_set & {"web_search", "web_parse"}:
            return request

        search_svc = WebSearchService()
        parser_svc = WebParserService()

        context_blocks: list[str] = []
        search_results: list[dict] = []

        if "web_search" in tool_set:
            try:
                search_results = await asyncio.wait_for(
                    search_svc.search(query, max_results=5),
                    timeout=15,
                )
            except (asyncio.TimeoutError, Exception):
                search_results = []

            if search_results:
                lines = "\n".join(
                    f"- [{r['title']}]({r['url']}): {r['snippet']}"
                    for r in search_results
                )
                context_blocks.append(f"[Результаты поиска]\n{lines}")

        if "web_parse" in tool_set and search_results:
            urls = [r["url"] for r in search_results[:3] if r.get("url")]
            parse_tasks = [parser_svc.parse(url) for url in urls]
            try:
                pages = await asyncio.wait_for(
                    asyncio.gather(*parse_tasks, return_exceptions=True),
                    timeout=20,
                )
            except asyncio.TimeoutError:
                pages = []

            for page in pages:
                if isinstance(page, dict) and page.get("text"):
                    context_blocks.append(
                        f"Источник: {page['url']}\n{page['text'][:1500]}"
                    )

        if not context_blocks:
            return request

        addition = "\n\n".join(context_blocks)
        system_addition = f"\n\n[Контекст из интернета]\n{addition}"

        messages = list(request.messages)
        if messages and messages[0].role == "system":
            messages[0] = messages[0].model_copy(
                update={"content": messages[0].content + system_addition}
            )
        else:
            messages.insert(0, Message(role="system", content=system_addition.strip()))

        return request.model_copy(update={"messages": messages})


def get_cascade_router() -> CascadeRouter:
    return CascadeRouter()
