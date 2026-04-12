from __future__ import annotations

"""
Task Router — deterministic rules first, MWS API as LLM fallback.

Route decision:
  Input:  { message: str, attachments: list[Attachment] }
  Output: { task_type: str, model_id: str, tools: list[str], confidence: float }
"""
import re
import json
import logging
from dataclasses import dataclass, field

import httpx
from fastapi import Depends

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

TASK_MODELS = {
    "text":           "mws-gpt-alpha",
    "code":           "qwen3-coder-480b-a35b",
    "deep_research":  "qwen2.5-72b-instruct",
    "asr":            "whisper-turbo-local",
    "vlm":            "cotype-pro-vl-32b",
    "image_gen":      "qwen-image",
    "web_search":     "mws-gpt-alpha",
    "web_parse":      "mws-gpt-alpha",
    "file_qa":        "mws-gpt-alpha",
}

TASK_TOOLS = {
    "web_search":    ["web_search"],
    "web_parse":     ["web_parse"],
    "deep_research": ["web_search", "web_parse"],
    "file_qa":       ["rag"],
}

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

CODE_KEYWORDS = re.compile(
    r"(код\b|функци|class |def |реализу|напиши|алгоритм|скрипт|программ|написать)",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r"https?://\S+")
RESEARCH_KEYWORDS = re.compile(
    r"(исследу|глубокий анализ|подробно разбери|deep research|расскажи подробно"
    r"|подробный анализ|детальный анализ|разбери подробно|изучи|проанализируй)",
    re.IGNORECASE,
)

ROUTER_SYSTEM_PROMPT = (
    "You are a task router. Given a user message, output ONLY a JSON object:\n"
    '{"task_type": "<type>", "confidence": <0.0-1.0>}\n\n'
    "Valid task types: text, code, web_search, web_parse, deep_research, "
    "file_qa, asr, vlm, image_gen\n\n"
    "Examples:\n"
    '{"message":"Привет, как дела?"} → {"task_type":"text","confidence":0.99}\n'
    '{"message":"Найди информацию о квантовых компьютерах"} → {"task_type":"web_search","confidence":0.9}\n'
    '{"message":"Напиши функцию сортировки на Python"} → {"task_type":"code","confidence":0.95}\n'
    '{"message":"Нарисуй закат над морем"} → {"task_type":"image_gen","confidence":0.92}\n'
    '{"message":"Расскажи подробно про блокчейн"} → {"task_type":"deep_research","confidence":0.88}\n'
)


@dataclass
class RouteResult:
    task_type: str
    model_id: str
    tools: list[str] = field(default_factory=list)
    confidence: float = 1.0


class RouterClient:
    def __init__(self, settings: Settings):
        self.mws_base = settings.MWS_BASE_URL
        self.mws_key = settings.MWS_API_KEY
        self.router_model = settings.MODEL_TEXT  # mws-gpt-alpha для роутинга
        self.fallback_model = settings.MODEL_TEXT

    def _deterministic(
        self, message: str, attachments: list[dict]
    ) -> RouteResult | None:
        """Fast O(1) rules — if matched, skip LLM entirely."""
        for att in attachments:
            name: str = att.get("name", "").lower()
            mime: str = att.get("mime", "").lower()
            ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""

            if ext in AUDIO_EXTS or mime.startswith("audio/"):
                return RouteResult("asr", TASK_MODELS["asr"], [])

            if ext in IMAGE_EXTS or mime.startswith("image/"):
                return RouteResult("vlm", TASK_MODELS["vlm"], [])

            if ext in {".pdf", ".docx", ".txt"}:
                return RouteResult(
                    "file_qa", TASK_MODELS["file_qa"], TASK_TOOLS["file_qa"]
                )

        if RESEARCH_KEYWORDS.search(message):
            return RouteResult(
                "deep_research",
                TASK_MODELS["deep_research"],
                TASK_TOOLS["deep_research"],
            )

        if URL_PATTERN.search(message):
            return RouteResult(
                "web_parse", TASK_MODELS["web_parse"], TASK_TOOLS["web_parse"]
            )

        if CODE_KEYWORDS.search(message):
            return RouteResult("code", TASK_MODELS["code"], [])

        return None

    async def _llm_route_mws(self, message: str) -> RouteResult:
        """Call MWS API (mws-gpt-alpha) for ambiguous routing."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.mws_base}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.mws_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.router_model,
                        "messages": [
                            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                            {"role": "user", "content": message},
                        ],
                        "max_tokens": 64,
                        "temperature": 0.0,
                    },
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                # Парсим JSON из ответа
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                else:
                    parsed = json.loads(content)
                task_type = parsed.get("task_type", "text")
                confidence = float(parsed.get("confidence", 0.5))
        except Exception as exc:
            print(exc)
            logger.warning("MWS routing error: %s", exc)
            task_type, confidence = "text", 0.5

        if confidence < 0.7:
            task_type = "text"

        model_id = TASK_MODELS.get(task_type, self.fallback_model)
        tools = TASK_TOOLS.get(task_type, [])
        return RouteResult(task_type, model_id, tools, confidence)

    async def route(self, message: str, attachments: list[dict]) -> RouteResult:
        # 1. Deterministic rules (fastest)
        det = self._deterministic(message, attachments)
        if det is not None:
            return det

        # 2. MWS API
        return await self._llm_route_mws(message)


def get_router_client(settings: Settings = Depends(get_settings)) -> RouterClient:
    return RouterClient(settings)
