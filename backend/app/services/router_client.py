from __future__ import annotations

"""
Task Router — deterministic rules first, LLM (qwen2.5:3b via Ollama) as fallback.

Route decision:
  Input:  { message: str, attachments: list[Attachment] }
  Output: { task_type: str, model_id: str, tools: list[str], confidence: float }
"""
import re
import json
from dataclasses import dataclass, field

import httpx
from fastapi import Depends

from app.config import Settings, get_settings

TASK_MODELS = {
    "text":           "mws-gpt-alpha",
    "code":           "kodify-2.0",
    "deep_research":  "cotype-preview-32k",
    "asr":            "faster-whisper",
    "vlm":            "llava",
    "image_gen":      "stable-diffusion",
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

# Audio/video MIME prefixes
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


@dataclass
class RouteResult:
    task_type: str
    model_id: str
    tools: list[str] = field(default_factory=list)
    confidence: float = 1.0


class RouterClient:
    def __init__(self, settings: Settings):
        self.ollama_url = settings.ROUTER_URL
        self.ollama_model = settings.ROUTER_MODEL
        self.fallback_model = settings.MODEL_TEXT

    def _deterministic(
        self, message: str, attachments: list[dict]
    ) -> RouteResult | None:
        """Fast O(1) rules — if matched, skip LLM entirely."""
        # Check attachments
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

        # Check message text
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

        return None  # needs LLM routing

    async def _llm_route(self, message: str) -> RouteResult:
        """Call qwen2.5:3b via Ollama for ambiguous cases."""
        system_prompt = (
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

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.ollama_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message},
                        ],
                        "stream": False,
                        "format": "json",
                    },
                )
                r.raise_for_status()
                data = r.json()
                parsed = json.loads(data["message"]["content"])
                task_type = parsed.get("task_type", "text")
                confidence = float(parsed.get("confidence", 0.5))
        except Exception:
            task_type, confidence = "text", 0.5

        # Low confidence → fallback to plain text
        if confidence < 0.7:
            task_type = "text"

        model_id = TASK_MODELS.get(task_type, self.fallback_model)
        tools = TASK_TOOLS.get(task_type, [])
        return RouteResult(task_type, model_id, tools, confidence)

    async def route(self, message: str, attachments: list[dict]) -> RouteResult:
        det = self._deterministic(message, attachments)
        if det is not None:
            return det
        return await self._llm_route(message)


def get_router_client(settings: Settings = Depends(get_settings)) -> RouterClient:
    return RouterClient(settings)
