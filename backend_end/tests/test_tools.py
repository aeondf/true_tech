"""Tests for web search and web parse endpoints."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.anyio
async def test_web_search(client):
    mock_results = [
        {"title": "Python", "url": "https://python.org", "snippet": "Official site"},
    ]
    with patch(
        "app.api.v1.tools.WebSearchService.search",
        new_callable=AsyncMock,
        return_value=mock_results,
    ):
        resp = await client.post(
            "/v1/tools/web-search",
            json={"query": "Python programming", "max_results": 3},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["results"][0]["url"] == "https://python.org"


@pytest.mark.anyio
async def test_web_parse(client):
    mock_page = {"url": "https://example.com", "text": "Hello world", "links": []}
    with patch(
        "app.api.v1.tools.WebParserService.parse",
        new_callable=AsyncMock,
        return_value=mock_page,
    ):
        resp = await client.post(
            "/v1/tools/web-parse",
            json={"url": "https://example.com"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello world"


@pytest.mark.anyio
async def test_web_parse_invalid_url(client):
    resp = await client.post(
        "/v1/tools/web-parse",
        json={"url": "not-a-url"},
    )
    assert resp.status_code == 422
