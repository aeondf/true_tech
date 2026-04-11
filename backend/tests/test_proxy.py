"""Tests for the OpenAI-compatible proxy."""
import pytest


@pytest.mark.anyio
async def test_chat_completions_ok(client):
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
async def test_list_models(client):
    resp = await client.get("/v1/models")
    assert resp.status_code == 200
    assert "data" in resp.json()


@pytest.mark.anyio
async def test_embeddings(client):
    resp = await client.post(
        "/v1/embeddings",
        json={"model": "bge-m3", "input": "test text"},
    )
    assert resp.status_code == 200
    assert "data" in resp.json()
