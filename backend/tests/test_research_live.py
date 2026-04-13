from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.v1.research import _run_pipeline
from app.config import Settings
from app.services.mws_client import MWSClient

pytestmark = [pytest.mark.live, pytest.mark.slow]


def get_settings() -> Settings:
    return Settings(
        _env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def collect_sse(query: str) -> list[dict]:
    settings = get_settings()
    mws = MWSClient(settings)
    events = []
    async for raw in _run_pipeline(query, mws, settings):
        lines = raw.strip().splitlines()
        event_type = None
        data = {}
        for line in lines:
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if event_type:
            events.append({"event": event_type, "data": data})
    return events


def test_research_live_emits_progress_and_terminal_event() -> None:
    events = run(collect_sse("what is retrieval augmented generation"))
    event_types = [event["event"] for event in events]

    assert "progress" in event_types
    assert "done" in event_types or "error" in event_types


def test_research_live_done_payload_contains_sources_when_available() -> None:
    events = run(collect_sse("FastAPI versus Django for new backends"))
    done = next((event for event in events if event["event"] == "done"), None)
    if done is None:
        error = next((event for event in events if event["event"] == "error"), None)
        pytest.skip(f"live pipeline returned error instead of done: {error}")

    assert done["data"]["answer"]
    assert "sources" in done["data"]
    assert "stats" in done["data"]
    assert isinstance(done["data"]["sources"], list)


def test_research_live_short_query_does_not_hang() -> None:
    events = run(collect_sse("Python"))
    event_types = [event["event"] for event in events]

    assert "done" in event_types or "error" in event_types
