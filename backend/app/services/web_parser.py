"""Fetch a URL and extract structured text content."""

from __future__ import annotations

import asyncio
from functools import lru_cache, partial

import httpx
from bs4 import BeautifulSoup
from fastapi import Depends

from app.config import Settings, get_settings

_TEXTUAL_CONTENT_TYPES = {
    "application/json",
    "application/ld+json",
    "application/xhtml+xml",
    "application/xml",
    "text/html",
    "text/plain",
    "text/xml",
}


class WebParserService:
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def __init__(self, *, timeout: int = 15, max_body_bytes: int = 1_500_000) -> None:
        self._timeout = timeout
        self._max_body_bytes = max_body_bytes
        self._limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        self._clients: dict[int, httpx.AsyncClient] = {}

    def _http(self) -> httpx.AsyncClient:
        loop_id = id(asyncio.get_running_loop())
        client = self._clients.get(loop_id)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(
                headers=self._HEADERS,
                timeout=httpx.Timeout(self._timeout, connect=min(self._timeout, 10)),
                follow_redirects=True,
                limits=self._limits,
            )
            self._clients[loop_id] = client
        return client

    def _is_supported_content_type(self, content_type: str) -> bool:
        if not content_type:
            return True
        if content_type.startswith("text/"):
            return True
        return content_type in _TEXTUAL_CONTENT_TYPES

    async def parse(self, url: str, extract_links: bool = False) -> dict:
        try:
            client = self._http()
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                content_type = content_type.split(";", 1)[0].strip().lower()
                if not self._is_supported_content_type(content_type):
                    return {
                        "url": url,
                        "error": f"unsupported content type: {content_type or 'unknown'}",
                        "title": "",
                        "text": "",
                        "links": [],
                    }

                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > self._max_body_bytes:
                            return {
                                "url": url,
                                "error": "response too large",
                                "title": "",
                                "text": "",
                                "links": [],
                            }
                    except ValueError:
                        pass

                body: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > self._max_body_bytes:
                        return {
                            "url": url,
                            "error": "response too large",
                            "title": "",
                            "text": "",
                            "links": [],
                        }
                    body.append(chunk)

                encoding = response.encoding or "utf-8"
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return {"url": url, "error": str(e), "title": "", "text": "", "links": []}

        html = b"".join(body).decode(encoding, errors="replace")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(self._parse_html, html, url, extract_links),
        )

    @staticmethod
    def _parse_html(html: str, url: str, extract_links: bool) -> dict:
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line for line in text.splitlines() if line.strip()]
        clean = "\n".join(lines)

        links = []
        if extract_links:
            links = [
                anchor["href"]
                for anchor in soup.find_all("a", href=True)
                if anchor["href"].startswith("http")
            ][:20]

        return {"url": url, "title": title, "text": clean[:8000], "links": links}


@lru_cache(maxsize=4)
def _get_cached_web_parser_service(
    timeout: int,
    max_body_bytes: int,
) -> WebParserService:
    return WebParserService(timeout=timeout, max_body_bytes=max_body_bytes)


def build_web_parser_service(settings: Settings) -> WebParserService:
    return _get_cached_web_parser_service(
        settings.RESEARCH_PARSE_TIMEOUT,
        settings.RESEARCH_MAX_PAGE_BYTES,
    )


def get_web_parser_service(
    settings: Settings = Depends(get_settings),
) -> WebParserService:
    return build_web_parser_service(settings)
