from __future__ import annotations

"""Three-pass request router used by the proxy layer."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

TASK_MODELS: dict[str, str] = {
    "text": "mws-gpt-alpha",
    "code": "qwen3-coder-480b-a35b",
    "asr": "whisper-turbo-local",
    "vlm": "cotype-pro-vl-32b",
    "image_gen": "qwen-image",
    "web_search": "qwen2.5-72b-instruct",
    "web_parse": "qwen2.5-72b-instruct",
    "deep_research": "qwen2.5-72b-instruct",
    "file_qa": "qwen2.5-72b-instruct",
}

AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
DOC_EXTS = {".pdf", ".docx", ".txt"}

RESEARCH_EXPLICIT_RE = re.compile(
    r"(\bdeep research\b|"
    r"(?:проведи|сделай|выполни)\s+(?:глубокое\s+|детальное\s+|подробное\s+)?исследовани"
    r"|исследуй\b|исследование\b|изучи тему\b|do research\b|run research\b)",
    re.IGNORECASE,
)

RESEARCH_ANALYSIS_RE = re.compile(
    r"((?:глубокий|подробный|детальный|комплексный|thorough|detailed|in-depth)\s+"
    r"(?:анализ|исследование|analysis|research))",
    re.IGNORECASE,
)

RESEARCH_EVIDENCE_RE = re.compile(
    r"(по источникам|со ссылками|с ссылками на источники|с цитатами|с фактами|"
    r"подкрепи источниками|cite sources|with sources|with citations)",
    re.IGNORECASE,
)

IMAGE_GEN_RE = re.compile(
    r"(нарисуй|сгенерируй (изображение|картинку|арт)|создай (изображение|картинку)|"
    r"draw |generate (image|picture|art)|imagine )",
    re.IGNORECASE,
)

CODE_RE = re.compile(
    r"(код\b|функци|class |def |реализу|напиши (функцию|скрипт|код|программу)|"
    r"алгоритм|скрипт\b|программ|SELECT |INSERT |CREATE TABLE)",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://\S+")

WEB_PARSE_RE = re.compile(
    r"(открой|прочитай|проанализируй|разбери|перейди по|summarize|parse|read) .{0,60}https?://",
    re.IGNORECASE,
)

WEB_SEARCH_RE = re.compile(
    r"(найди|поищи|search|look up|find)",
    re.IGNORECASE,
)

_LLM_SYSTEM = (
    "You are a request classifier. Given a user message, output ONLY valid JSON:\n"
    '{"task_type": "<type>", "confidence": <0.0-1.0>}\n\n'
    "Valid types: text, code, web_search, web_parse, deep_research, "
    "file_qa, asr, vlm, image_gen.\n"
    "Use deep_research only for explicit multi-source or source-backed research requests. "
    "Do not choose deep_research for ordinary explanations, simple 'tell me in detail' prompts, "
    "or coding requests.\n\n"
    "Examples:\n"
    '{"message":"Привет"} -> {"task_type":"text","confidence":0.99}\n'
    '{"message":"Напиши merge sort на Python"} -> {"task_type":"code","confidence":0.97}\n'
    '{"message":"Найди последние новости о GPT-5"} -> {"task_type":"web_search","confidence":0.92}\n'
    '{"message":"Нарисуй закат над морем"} -> {"task_type":"image_gen","confidence":0.95}\n'
    '{"message":"Расскажи подробно про фотосинтез"} -> {"task_type":"text","confidence":0.90}\n'
    '{"message":"Сделай глубокое исследование рынка LLM со ссылками"} -> {"task_type":"deep_research","confidence":0.93}\n'
)

LLM_ROUTER_MODEL = "llama-3.1-8b-instruct"
LLM_ROUTER_TIMEOUT = 60.0


@dataclass
class RouteResult:
    task_type: str
    model_id: str
    confidence: float
    which_pass: int


def _normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", message or "").strip()


def _should_route_to_deep_research(message: str) -> bool:
    normalized = _normalize_message(message)
    if not normalized:
        return False

    explicit = RESEARCH_EXPLICIT_RE.search(normalized) is not None
    structured_analysis = RESEARCH_ANALYSIS_RE.search(normalized) is not None
    source_backed = RESEARCH_EVIDENCE_RE.search(normalized) is not None
    code_like = CODE_RE.search(normalized) is not None

    if code_like and not source_backed:
        return False

    if explicit:
        return True
    if structured_analysis:
        return True
    if source_backed and len(normalized.split()) >= 4:
        return True
    return False


class RouterClient:
    def __init__(self, settings: Settings):
        self._base_url = settings.MWS_BASE_URL
        self._api_key = settings.MWS_API_KEY
        self._timeout = httpx.Timeout(LLM_ROUTER_TIMEOUT, connect=10, write=15, pool=10)
        self._limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        self._clients: dict[int, httpx.AsyncClient] = {}

    def _http(self) -> httpx.AsyncClient:
        loop_id = id(asyncio.get_running_loop())
        client = self._clients.get(loop_id)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=self._limits,
            )
            self._clients[loop_id] = client
        return client

    def _pass1(self, attachments: list[dict]) -> RouteResult | None:
        for att in attachments:
            name: str = att.get("name", "").lower()
            mime: str = att.get("mime", "").lower()
            ext = ("." + name.rsplit(".", 1)[-1]) if "." in name else ""

            if ext in AUDIO_EXTS or mime.startswith("audio/"):
                return RouteResult("asr", TASK_MODELS["asr"], 1.0, 1)

            if ext in IMAGE_EXTS or mime.startswith("image/"):
                return RouteResult("vlm", TASK_MODELS["vlm"], 1.0, 1)

            if ext in DOC_EXTS:
                return RouteResult("file_qa", TASK_MODELS["file_qa"], 1.0, 1)

        return None

    def _pass2(self, message: str) -> RouteResult | None:
        normalized = _normalize_message(message)

        if URL_RE.search(normalized):
            if WEB_PARSE_RE.search(normalized):
                return RouteResult("web_parse", TASK_MODELS["web_parse"], 0.9, 2)
            if WEB_SEARCH_RE.search(normalized):
                return RouteResult("web_search", TASK_MODELS["web_search"], 0.9, 2)

        if IMAGE_GEN_RE.search(normalized):
            return RouteResult("image_gen", TASK_MODELS["image_gen"], 0.9, 2)

        if _should_route_to_deep_research(normalized):
            return RouteResult("deep_research", TASK_MODELS["deep_research"], 0.9, 2)

        if CODE_RE.search(normalized):
            return RouteResult("code", TASK_MODELS["code"], 0.9, 2)

        return None

    async def _pass3(self, message: str) -> RouteResult:
        try:
            client = self._http()
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_ROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": _LLM_SYSTEM},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": 64,
                    "temperature": 0.0,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*?\}", content, re.DOTALL)
            parsed = json.loads(match.group() if match else content)
            task_type = parsed.get("task_type", "text")
            confidence = float(parsed.get("confidence", 0.5))
        except Exception as exc:
            logger.warning("LLM router error (pass 3): %s", exc)
            return RouteResult("text", TASK_MODELS["text"], 0.5, 3)

        if confidence < 0.7:
            task_type = "text"

        model_id = TASK_MODELS.get(task_type, TASK_MODELS["text"])
        return RouteResult(task_type, model_id, confidence, 3)

    async def route(self, message: str, attachments: list[dict]) -> RouteResult:
        result = self._pass1(attachments)
        if result:
            return result

        result = self._pass2(message)
        if result:
            return result

        return await self._pass3(message)


@lru_cache(maxsize=1)
def get_router_client() -> RouterClient:
    return RouterClient(get_settings())
