from __future__ import annotations

"""
ContextCompressor — сжимает историю чата когда она превышает лимит токенов.

Алгоритм:
  1. Считаем токены всех сообщений (кроме system).
  2. Если сумма > threshold — берём старые сообщения (всё кроме tail_messages последних).
  3. Просим LLM сделать краткое изложение этих старых сообщений.
  4. Заменяем их одним system-сообщением с пометкой [Сжатая история].
  5. Возвращаем укороченный список сообщений.
"""

import re
from fastapi import Depends

from app.config import Settings, get_settings
from app.models.mws import Message
from app.services.mws_client import MWSClient, get_mws_client

# Сколько последних сообщений оставляем нетронутыми (свежий контекст)
TAIL_MESSAGES = 10

_SUMMARY_SYSTEM = (
    "Ты — ассистент для сжатия истории диалога. "
    "Сделай краткое изложение разговора ниже на русском языке. "
    "Сохрани важные факты: имена, задачи, решения, договорённости. "
    "Пиши сжато, без лишних слов. Максимум 300 слов."
)


def _count_tokens(text: str) -> int:
    """Быстрая оценка токенов: ~1 токен = 4 символа (для русского чуть меньше)."""
    return max(1, len(text) // 3)


def _messages_tokens(messages: list[Message]) -> int:
    return sum(_count_tokens(m.content) for m in messages if m.role != "system")


class ContextCompressor:
    def __init__(self, mws: MWSClient, settings: Settings):
        self._mws = mws
        self._threshold = settings.CONTEXT_MAX_TOKENS
        self._model = settings.MODEL_TEXT

    async def compress_if_needed(self, messages: list[Message]) -> list[Message]:
        """
        Принимает список сообщений, возвращает (возможно сжатый) список.
        Если токенов меньше порога — возвращает как есть.
        """
        if _messages_tokens(messages) <= self._threshold:
            return messages

        # Разделяем: system-сообщения отдельно, остальные отдельно
        system_msgs = [m for m in messages if m.role == "system"]
        chat_msgs = [m for m in messages if m.role != "system"]

        # Нечего сжимать — слишком мало сообщений
        if len(chat_msgs) <= TAIL_MESSAGES:
            return messages

        old_msgs = chat_msgs[:-TAIL_MESSAGES]
        tail_msgs = chat_msgs[-TAIL_MESSAGES:]

        summary = await self._summarize(old_msgs)
        summary_msg = Message(
            role="system",
            content=f"[Сжатая история диалога]\n{summary}",
        )

        return system_msgs + [summary_msg] + tail_msgs

    async def _summarize(self, messages: list[Message]) -> str:
        """Просим LLM сжать старые сообщения в краткое изложение."""
        dialogue = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in messages
        )
        try:
            return await self._mws.chat_simple(
                model=self._model,
                system=_SUMMARY_SYSTEM,
                user=dialogue,
            )
        except Exception:
            # Если LLM недоступен — делаем простое обрезание текста
            return _fallback_summary(messages)


def _fallback_summary(messages: list[Message]) -> str:
    """Запасной вариант без LLM: берём первые 150 слов каждого сообщения."""
    parts = []
    for m in messages:
        words = re.split(r"\s+", m.content.strip())
        snippet = " ".join(words[:30])
        if len(words) > 30:
            snippet += "..."
        parts.append(f"{m.role}: {snippet}")
    return "\n".join(parts)


def get_context_compressor(
    mws: MWSClient = Depends(get_mws_client),
    settings: Settings = Depends(get_settings),
) -> ContextCompressor:
    return ContextCompressor(mws=mws, settings=settings)
