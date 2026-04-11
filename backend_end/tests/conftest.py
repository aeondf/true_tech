"""
Pytest configuration.
Sets required env vars BEFORE any app module is imported.
"""
import os

# ── Required env vars for tests (no real services needed) ────────
os.environ.setdefault("MWS_API_KEY", "test-key-000")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/mirea_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("ROUTER_URL", "http://localhost:11434")
os.environ.setdefault("ASR_URL", "http://localhost:8001")
os.environ.setdefault("IMAGE_GEN_URL", "http://localhost:8002")
os.environ.setdefault("VLM_URL", "http://localhost:8003")

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client — no real DB/network unless mocked."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
