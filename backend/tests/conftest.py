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
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_session
from app.services.mws_client import get_mws_client
from app.services.router_client import get_router_client, RouteResult
from app.services.memory_retriever import get_memory_retriever
from app.services.chunk_store import get_chunk_store
from app.services.embedding_service import get_embedding_service
from app.services.context_compressor import get_context_compressor
from app.services.cascade_router import get_cascade_router


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── Default mock implementations ─────────────────────────────────

def _make_mws_mock():
    mws = AsyncMock()
    mws.chat.return_value = {
        "choices": [{"message": {"content": "Привет!"}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 12},
    }
    mws.embed.return_value = {"data": [{"embedding": [0.0] * 1024}]}
    mws.list_models.return_value = {"data": [{"id": "mws-gpt-alpha"}]}
    return mws


def _make_router_mock():
    router = AsyncMock()
    router.route.return_value = RouteResult(
        task_type="text", model_id="mws-gpt-alpha", tools=[], confidence=0.99
    )
    return router


async def _mock_session():
    yield AsyncMock(spec=AsyncSession)


@pytest.fixture
async def client():
    """
    Async test client.
    All external dependencies (DB, MWS, router, memory, RAG) are mocked via
    dependency_overrides so no real network/DB calls are made.
    """
    mws = _make_mws_mock()
    router_mock = _make_router_mock()
    retriever = AsyncMock(); retriever.retrieve.return_value = []
    chunk_store = AsyncMock(); chunk_store.store.return_value = "file-uuid-123"; chunk_store.search.return_value = []
    embedder = AsyncMock(); embedder.embed.return_value = [0.0] * 1024; embedder.embed_batch.return_value = [[0.0] * 1024]
    compressor = AsyncMock(); compressor.compress_if_needed.side_effect = lambda msgs: msgs
    cascade = AsyncMock(); cascade.run.side_effect = lambda req, *a, **kw: req

    app.dependency_overrides.update({
        get_session:           _mock_session,
        get_mws_client:        lambda: mws,
        get_router_client:     lambda: router_mock,
        get_memory_retriever:  lambda: retriever,
        get_chunk_store:       lambda: chunk_store,
        get_embedding_service: lambda: embedder,
        get_context_compressor: lambda: compressor,
        get_cascade_router:    lambda: cascade,
    })

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
