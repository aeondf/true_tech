from __future__ import annotations

"""Async web search service built on DuckDuckGo HTML results."""

import asyncio
from functools import lru_cache
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import Depends

from app.config import Settings, get_settings


class WebSearchService:
    _SEARCH_URL = "https://html.duckduckgo.com/html/"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def __init__(self, *, timeout: int = 15) -> None:
        self._timeout = timeout
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

    @staticmethod
    def _unwrap_result_url(raw_url: str) -> str:
        candidate = (raw_url or "").strip()
        if not candidate:
            return ""
        if candidate.startswith("//"):
            candidate = f"https:{candidate}"

        parsed = urlparse(candidate)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                return unquote(target)
        return candidate

    @classmethod
    def _parse_results(cls, html: str, max_results: int) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results: list[dict] = []
        seen: set[str] = set()

        for node in soup.select(".results .result"):
            link = node.select_one(".result__a")
            if link is None:
                continue

            url = cls._unwrap_result_url(link.get("href", ""))
            title = link.get_text(" ", strip=True)
            snippet_el = node.select_one(".result__snippet")
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

            if not url or not title or url in seen:
                continue

            seen.add(url)
            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                }
            )
            if len(results) >= max(1, max_results):
                break

        return results

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        client = self._http()
        response = await client.post(self._SEARCH_URL, data={"q": query})
        response.raise_for_status()
        return self._parse_results(response.text, max_results=max_results)


@lru_cache(maxsize=4)
def _get_cached_web_search_service(timeout: int) -> WebSearchService:
    return WebSearchService(timeout=timeout)


def build_web_search_service(settings: Settings) -> WebSearchService:
    return _get_cached_web_search_service(settings.RESEARCH_SEARCH_TIMEOUT)


def get_web_search_service(
    settings: Settings = Depends(get_settings),
) -> WebSearchService:
    return build_web_search_service(settings)
