from __future__ import annotations

"""
Async client for MWS GPT API.
  - chat / completion / embeddings (regular + streaming)
  - stream_tokens(): parses SSE and yields plain text tokens
  - Exponential backoff on 429 / 503
"""

import asyncio
import json
import logging
from functools import lru_cache
from typing import AsyncIterator

import httpx

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
        self._timeout = httpx.Timeout(300, connect=10, write=30, pool=15)
        self._limits = httpx.Limits(max_connections=40, max_keepalive_connections=20)
        self._clients: dict[int, httpx.AsyncClient] = {}

    def _http(self) -> httpx.AsyncClient:
        loop_id = id(asyncio.get_running_loop())
        client = self._clients.get(loop_id)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=self._timeout,
                limits=self._limits,
            )
            self._clients[loop_id] = client
        return client

    @with_retry(retries=3, retry_on={429, 503})
    async def chat(self, request: ChatCompletionRequest) -> dict:
        c = self._http()
        r = await c.post(
            "/v1/chat/completions",
            json=request.model_dump(exclude_none=True),
        )
        r.raise_for_status()
        if not r.content:
            logger.error(
                "MWS returned empty body for model=%s status=%s",
                request.model,
                r.status_code,
            )
            raise ValueError(
                f"MWS returned empty response body (status={r.status_code}, model={request.model})"
            )
        try:
            return r.json()
        except Exception as exc:
            logger.error(
                "MWS JSON parse error for model=%s status=%s body=%r",
                request.model,
                r.status_code,
                r.text[:500],
            )
            raise ValueError(
                f"MWS returned non-JSON body (status={r.status_code}, model={request.model}): {r.text[:200]}"
            ) from exc

    @with_retry(retries=3, retry_on={429, 503})
    async def completion(self, request: CompletionRequest) -> dict:
        c = self._http()
        r = await c.post(
            "/v1/completions",
            json=request.model_dump(exclude_none=True),
        )
        r.raise_for_status()
        return r.json()

    @with_retry(retries=3, retry_on={429, 503})
    async def embed(self, request: EmbeddingRequest) -> dict:
        c = self._http()
        r = await c.post(
            "/v1/embeddings",
            json=request.model_dump(exclude_none=True),
        )
        r.raise_for_status()
        return r.json()

    async def list_models(self) -> dict:
        c = self._http()
        r = await c.get("/v1/models")
        r.raise_for_status()
        return r.json()

    async def stream_chat(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[bytes]:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        c = self._http()
        async with c.stream("POST", "/v1/chat/completions", json=payload) as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes():
                if chunk:
                    yield chunk

    async def stream_completion(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[bytes]:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        c = self._http()
        async with c.stream("POST", "/v1/completions", json=payload) as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes():
                if chunk:
                    yield chunk

    async def stream_tokens(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[str]:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        c = self._http()
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

    async def chat_simple(self, model: str, system: str, user: str) -> str:
        """Single-turn chat that returns assistant text."""
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


@lru_cache(maxsize=1)
def get_mws_client() -> MWSClient:
    return MWSClient(get_settings())
