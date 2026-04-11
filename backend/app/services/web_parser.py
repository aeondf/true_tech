"""Fetch URL → clean text via requests + BeautifulSoup (run in thread pool)."""
import asyncio
from functools import partial

import httpx
from bs4 import BeautifulSoup


class WebParserService:
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; MireaBot/1.0)"
        )
    }

    async def parse(self, url: str, extract_links: bool = False) -> dict:
        try:
            async with httpx.AsyncClient(
                headers=self._HEADERS, timeout=15, follow_redirects=True, verify=False
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                html = r.text
        except Exception as e:
            return {"url": url, "error": str(e), "text": "", "links": []}

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, partial(self._parse_html, html, url, extract_links)
        )
        return result

    @staticmethod
    def _parse_html(html: str, url: str, extract_links: bool) -> dict:
        soup = BeautifulSoup(html, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse blank lines
        lines = [l for l in text.splitlines() if l.strip()]
        clean = "\n".join(lines)

        links = []
        if extract_links:
            links = [
                a["href"]
                for a in soup.find_all("a", href=True)
                if a["href"].startswith("http")
            ][:20]

        return {"url": url, "text": clean[:8000], "links": links}
