from __future__ import annotations

"""
ChunkStore — text chunks → embed → store in pgvector → cosine search.
"""
import uuid

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import FileChunk
from app.services.embedding_service import EmbeddingService, get_embedding_service


def _vec_literal(vector: list[float]) -> str:
    """Convert Python list to pgvector literal: '[0.1,0.2,...]'"""
    return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"


class ChunkStore:
    def __init__(self, session: AsyncSession, embedder: EmbeddingService):
        self.session = session
        self.embedder = embedder

    async def store(
        self, user_id: str, filename: str, chunks: list[str]
    ) -> str:
        """Embed and persist all chunks. Returns file_id."""
        file_id = str(uuid.uuid4())
        vectors = await self.embedder.embed_batch(chunks)

        for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            self.session.add(
                FileChunk(
                    id=str(uuid.uuid4()),
                    file_id=file_id,
                    user_id=user_id,
                    filename=filename,
                    chunk_index=i,
                    text=chunk_text,
                    embedding=vector,
                )
            )
        await self.session.commit()
        return file_id

    async def search(
        self, user_id: str, query_vector: list[float], top_k: int = 5
    ) -> list[dict]:
        """Cosine similarity search using pgvector <=> operator."""
        vec_str = _vec_literal(query_vector)
        result = await self.session.execute(
            text(
                """
                SELECT id, file_id, filename, chunk_index, text,
                       1 - (embedding <=> CAST(:vec AS vector(1024))) AS score
                FROM file_chunks
                WHERE user_id = :uid
                ORDER BY embedding <=> CAST(:vec AS vector(1024))
                LIMIT :k
                """
            ),
            {"vec": vec_str, "uid": user_id, "k": top_k},
        )
        return [dict(row._mapping) for row in result]


def get_chunk_store(
    session: AsyncSession = Depends(get_session),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> ChunkStore:
    return ChunkStore(session, embedder)
