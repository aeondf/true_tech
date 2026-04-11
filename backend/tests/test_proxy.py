"""Tests for the OpenAI-compatible proxy."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.router_client import RouteResult


@pytest.fixture
def mock_deps():
    """Mock all external dependencies of the proxy endpoint."""
    route = RouteResult(task_type="text", model_id="mws-gpt-alpha", tools=[], confidence=0.99)

    chat_resp = {
        "choices": [{"message": {"content": "Привет!"}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 12},
    }

    with (
        patch("app.api.v1.proxy.get_mws_client") as p_mws,
        patch("app.api.v1.proxy.get_router_client") as p_router,
        patch("app.api.v1.proxy.get_memory_retriever") as p_mem,
        patch("app.api.v1.proxy.get_chunk_store") as p_chunk,
        patch("app.api.v1.proxy.get_embedding_service") as p_embed,
        patch("app.api.v1.proxy.get_session") as p_session,
    ):
        mws = AsyncMock()
        mws.chat.return_value = chat_resp
        mws.list_models.return_value = {"data": [{"id": "mws-gpt-alpha"}]}
        p_mws.return_value = mws

        router_client = AsyncMock()
        router_client.route.return_value = route
        p_router.return_value = router_client

        retriever = AsyncMock()
        retriever.retrieve.return_value = []
        p_mem.return_value = retriever

        chunk_store = AsyncMock()
        chunk_store.search.return_value = []
        p_chunk.return_value = chunk_store

        embedder = AsyncMock()
        embedder.embed.return_value = [0.0] * 1024
        p_embed.return_value = embedder

        session = AsyncMock()
        p_session.return_value = session

        yield {"mws": mws, "router": router_client}


@pytest.mark.anyio
async def test_chat_completions_ok(client, mock_deps):
    resp = await client.post(
        "/v1/chat/completions",
        json={
            "model": "mws-gpt-alpha",
            "messages": [{"role": "user", "content": "Привет"}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Привет!"


@pytest.mark.anyio
async def test_list_models(client, mock_deps):
    resp = await client.get("/v1/models")
    assert resp.status_code == 200
    assert "data" in resp.json()


@pytest.mark.anyio
async def test_embeddings(client):
    with patch("app.api.v1.proxy.get_mws_client") as p:
        mws = AsyncMock()
        mws.embed.return_value = {"data": [{"embedding": [0.1] * 1024}]}
        p.return_value = mws

        resp = await client.post(
            "/v1/embeddings",
            json={"model": "bge-m3", "input": "test text"},
        )
    assert resp.status_code == 200
    assert "data" in resp.json()
