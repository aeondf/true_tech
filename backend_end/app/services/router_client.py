from __future__ import annotations

"""
Task Router — deterministic rules first, local GGUF (qwen2.5-1.5b) as LLM fallback,
with Ollama as secondary fallback if GGUF is unavailable.

Route decision:
  Input:  { message: str, attachments: list[Attachment] }
  Output: { task_type: str, model_id: str, tools: list[str], confidence: float }
"""
import re
import json
import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

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


# ── Module-level GGUF singleton ───────────────────────────────────────────────

_gguf_llm = None
_gguf_load_lock: Optional[asyncio.Lock] = None
_gguf_load_attempted = False


def _load_gguf_sync(model_path: str):
    """Load GGUF model synchronously (runs in executor)."""
    from llama_cpp import Llama  # type: ignore
    logger.info("Loading local GGUF model from: %s", model_path)
    llm = Llama(
        model_path=model_path,
        n_ctx=512,
        n_gpu_layers=0,   # CPU inference; set to -1 to use GPU if available
        n_threads=4,
        verbose=False,
    )
    logger.info("Local GGUF model loaded successfully.")
    return llm


async def _get_gguf_llm(model_path: str):
    """Lazily load and return the GGUF Llama instance (thread-safe)."""
    global _gguf_llm, _gguf_load_lock, _gguf_load_attempted

    if _gguf_llm is not None:
        return _gguf_llm

    if _gguf_load_attempted:
        return None  # previous load failed — don't retry

    if _gguf_load_lock is None:
        _gguf_load_lock = asyncio.Lock()

    async with _gguf_load_lock:
        if _gguf_llm is not None:
            return _gguf_llm
        if _gguf_load_attempted:
            return None

        _gguf_load_attempted = True
        try:
            loop = asyncio.get_event_loop()
            _gguf_llm = await loop.run_in_executor(None, _load_gguf_sync, model_path)
        except Exception as exc:
            logger.warning("Failed to load local GGUF model: %s. Falling back to Ollama.", exc)
            _gguf_llm = None

    return _gguf_llm


# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class RouteResult:
    task_type: str
    model_id: str
    tools: list[str] = field(default_factory=list)
    confidence: float = 1.0


# ── Router ────────────────────────────────────────────────────────────────────

class RouterClient:
    def __init__(self, settings: Settings):
        self.ollama_url = settings.ROUTER_URL
        self.ollama_model = settings.ROUTER_MODEL
        self.fallback_model = settings.MODEL_TEXT
        self.gguf_path: str = settings.ROUTER_GGUF_PATH

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

        return None  # needs LLM routing

    async def _llm_route_local(self, message: str) -> RouteResult | None:
        """Use local GGUF model (qwen2.5-1.5b-instruct-fp16.gguf) for routing."""
        if not self.gguf_path or not os.path.isfile(self.gguf_path):
            return None

        llm = await _get_gguf_llm(self.gguf_path)
        if llm is None:
            return None

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                        {"role": "user", "content": message},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=64,
                    temperature=0.0,
                ),
            )
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            task_type = parsed.get("task_type", "text")
            confidence = float(parsed.get("confidence", 0.5))
        except Exception as exc:
            logger.warning("Local GGUF routing error: %s", exc)
            return None

        if confidence < 0.7:
            task_type = "text"

        model_id = TASK_MODELS.get(task_type, self.fallback_model)
        tools = TASK_TOOLS.get(task_type, [])
        return RouteResult(task_type, model_id, tools, confidence)

    async def _llm_route_ollama(self, message: str) -> RouteResult:
        """Call qwen2.5:3b via Ollama for ambiguous cases (secondary fallback)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.ollama_model,
                        "messages": [
                            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
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
        except Exception as exc:
            logger.warning("Ollama routing error: %s", exc)
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

        # 2. Local GGUF model (preferred LLM router)
        local_result = await self._llm_route_local(message)
        if local_result is not None:
            return local_result

        # 3. Ollama fallback
        return await self._llm_route_ollama(message)


def get_router_client(settings: Settings = Depends(get_settings)) -> RouterClient:
    return RouterClient(settings)
