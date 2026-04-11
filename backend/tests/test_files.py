"""Tests for file upload endpoint and FileProcessor."""
import io
import pytest
from unittest.mock import AsyncMock, patch

from app.services.file_processor import FileProcessor


# ── FileProcessor unit tests ─────────────────────────────────────

def test_split_plain_text():
    processor = FileProcessor()
    long_text = "слово " * 1000  # ~6000 chars → multiple chunks
    chunks = processor._split(long_text)
    assert len(chunks) > 1
    # Each chunk should be at most CHUNK_CHARS chars
    from app.services.file_processor import CHUNK_CHARS
    for chunk in chunks:
        assert len(chunk) <= CHUNK_CHARS


def test_no_empty_chunks():
    processor = FileProcessor()
    chunks = processor._split("   \n  \n   ")
    assert chunks == []


def test_extract_txt():
    processor = FileProcessor()
    content = "Hello world".encode("utf-8")
    chunks = processor.extract_chunks(content, "file.txt", "text/plain")
    assert len(chunks) == 1
    assert chunks[0] == "Hello world"


# ── Upload endpoint tests ────────────────────────────────────────

@pytest.mark.anyio
async def test_upload_txt(client):
    with (
        patch("app.api.v1.files.get_chunk_store") as p_store,
    ):
        store = AsyncMock()
        store.store.return_value = "file-uuid-123"
        p_store.return_value = store

        resp = await client.post(
            "/v1/files/upload",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
            params={"user_id": "user1"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_id"] == "file-uuid-123"
    assert data["chunks"] >= 1


@pytest.mark.anyio
async def test_upload_unsupported_type(client):
    resp = await client.post(
        "/v1/files/upload",
        files={"file": ("photo.jpg", b"fake-image", "image/jpeg")},
    )
    assert resp.status_code == 415


@pytest.mark.anyio
async def test_upload_too_large(client):
    big = b"x" * (51 * 1024 * 1024)  # 51 MB
    resp = await client.post(
        "/v1/files/upload",
        files={"file": ("big.txt", big, "text/plain")},
    )
    assert resp.status_code == 413
