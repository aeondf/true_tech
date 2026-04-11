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
    def __init__(self) -> None:
        self._search = WebSearchService()
        self._parser = WebParserService()

    async def run(
        self,
        request: ChatCompletionRequest,
        tools: list[str],
        query: str,
    ) -> ChatCompletionRequest:
        """
        Запускает нужные инструменты параллельно и добавляет результат в контекст.
        Если tools пустой или не содержит известных инструментов — возвращает запрос как есть.
        """
        tool_set = set(tools)

        # Нет инструментов — ничего не делаем
        if not tool_set & {"web_search", "web_parse"}:
            return request

        tasks: dict[str, asyncio.Task] = {}

        if "web_search" in tool_set:
            tasks["search"] = asyncio.create_task(
                self._search.search(query, max_results=5)
            )

        # Если есть web_parse — сначала ищем, потом парсим найденные URL
        # Но если web_search тоже есть — запускаем поиск параллельно
        # и парсим по результатам. Если только web_parse — ищем URL в тексте запроса.
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results = dict(zip(tasks.keys(), gathered))

        context_blocks: list[str] = []

        # Обрабатываем результаты поиска
        search_results: list[dict] = []
        if "search" in results and isinstance(results["search"], list):
            search_results = results["search"]
            if search_results:
                lines = "\n".join(
                    f"- [{r['title']}]({r['url']}): {r['snippet']}"
                    for r in search_results
                )
                context_blocks.append(f"[Результаты поиска]\n{lines}")

        # Если нужен web_parse — парсим топ-3 URL из поиска параллельно
        if "web_parse" in tool_set and search_results:
            urls = [r["url"] for r in search_results[:3] if r.get("url")]
            parse_tasks = [self._parser.parse(url) for url in urls]
            pages = await asyncio.gather(*parse_tasks, return_exceptions=True)

            parsed_blocks: list[str] = []
            for page in pages:
                if isinstance(page, dict) and page.get("text"):
                    parsed_blocks.append(
                        f"Источник: {page['url']}\n{page['text'][:1500]}"
                    )

            if parsed_blocks:
                context_blocks.append(
                    "[Содержимое страниц]\n\n" + "\n\n---\n\n".join(parsed_blocks)
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
