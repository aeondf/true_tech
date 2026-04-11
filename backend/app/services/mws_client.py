from __future__ import annotations

"""
Async client for MWS GPT API.
  - chat / completion / embeddings (regular + streaming)
  - stream_tokens(): parses SSE → yields plain text tokens (for WebSocket)
  - Exponential backoff on 429 / 503
"""
import json
import logging
from typing import AsyncIterator

import httpx
from fastapi import Depends

from app.config import Settings, get_settings
from app.models.mws import ChatCompletionRequest, CompletionRequest, EmbeddingRequest
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class MWSClient:
    def __init__(self, settings: Settings):
        self._base_url = settings.MWS_BASE_URL
        self._headers = {
            "Authorization": f"Bearer {settings.MWS_API_KEY}",
            "Content-Type": "application/json",
        }

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=120,
        )

    # ── Regular (non-streaming) ───────────────────────────────────

    @with_retry(retries=3, retry_on={429, 503})
    async def chat(self, request: ChatCompletionRequest) -> dict:
        async with self._http() as c:
            r = await c.post(
                "/v1/chat/completions",
                json=request.model_dump(exclude_none=True),
            )
            r.raise_for_status()
            if not r.content:
                logger.error(
                    "MWS returned empty body for model=%s status=%s",
                    request.model, r.status_code,
                )
                raise ValueError(
                    f"MWS returned empty response body (status={r.status_code}, model={request.model})"
                )
            try:
                return r.json()
            except Exception as exc:
                logger.error(
                    "MWS JSON parse error for model=%s status=%s body=%r",
                    request.model, r.status_code, r.text[:500],
                )
                raise ValueError(
                    f"MWS returned non-JSON body (status={r.status_code}, model={request.model}): {r.text[:200]}"
                ) from exc

    @with_retry(retries=3, retry_on={429, 503})
    async def completion(self, request: CompletionRequest) -> dict:
        async with self._http() as c:
            r = await c.post(
                "/v1/completions",
                json=request.model_dump(exclude_none=True),
            )
            r.raise_for_status()
            return r.json()

    @with_retry(retries=3, retry_on={429, 503})
    async def embed(self, request: EmbeddingRequest) -> dict:
        async with self._http() as c:
            r = await c.post(
                "/v1/embeddings",
                json=request.model_dump(exclude_none=True),
            )
            r.raise_for_status()
            return r.json()

    async def list_models(self) -> dict:
        async with self._http() as c:
            r = await c.get("/v1/models")
            r.raise_for_status()
            return r.json()

    # ── Streaming: raw SSE lines (for HTTP proxy) ─────────────────

    async def stream_chat(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[bytes]:
        """
        Yields raw SSE bytes forwarded directly to the HTTP client.
        If streaming fails (e.g. model doesn't support SSE), falls back to
        non-streaming and emits a single synthetic SSE chunk so the client
        always gets a response.
        """
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        stream_failed = False
        try:
            async with self._http() as c:
                async with c.stream("POST", "/v1/chat/completions", json=payload) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        if chunk:
                            yield chunk
            return  # normal exit
        except Exception as e:
            logger.warning(
                "stream_chat failed for model=%s (%s). Falling back to non-streaming.",
                request.model, e,
            )
            stream_failed = True

        if stream_failed:
            # Non-streaming fallback — same request without stream flag
            try:
                result = await self.chat(request)
                content = result["choices"][0]["message"]["content"]
                token_event = json.dumps({
                    "choices": [{"delta": {"content": content}, "finish_reason": "stop", "index": 0}]
                })
                yield f"data: {token_event}\n\n".encode()
                yield b"data: [DONE]\n\n"
            except Exception as fallback_exc:
                logger.error("Non-streaming fallback also failed for model=%s: %s", request.model, fallback_exc)
                error_event = json.dumps({
                    "error": {"code": 502, "message": str(fallback_exc)}
                })
                yield f"data: {error_event}\n\n".encode()

    async def stream_completion(
        self, request: CompletionRequest
    ) -> AsyncIterator[bytes]:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        async with self._http() as c:
            async with c.stream("POST", "/v1/completions", json=payload) as r:
                r.raise_for_status()
                async for chunk in r.aiter_bytes():
                    if chunk:
                        yield chunk

    # ── Streaming: parsed tokens (for WebSocket / internal use) ───

    async def stream_tokens(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        """
        Parses the SSE stream and yields plain text content tokens.
        Skips [DONE] and empty deltas.
        """
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        async with self._http() as c:
            async with c.stream("POST", "/v1/chat/completions", json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                        token = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if token:
                            yield token
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    # ── Convenience ───────────────────────────────────────────────

    async def chat_simple(self, model: str, system: str, user: str) -> str:
        """Single-turn chat — returns assistant text."""
        from app.models.mws import Message

        req = ChatCompletionRequest(
            model=model,
            messages=[
                Message(role="system", content=system),
                Message(role="user", content=user),
            ],
        )
        resp = await self.chat(req)
        return resp["choices"][0]["message"]["content"]


def get_mws_client(settings: Settings = Depends(get_settings)) -> MWSClient:
    return MWSClient(settings)
