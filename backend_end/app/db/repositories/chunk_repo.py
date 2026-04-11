from __future__ import annotations

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import FileChunk


class ChunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_files(self, user_id: str) -> list[dict]:
        """Return distinct files uploaded by user."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(
                FileChunk.file_id,
                FileChunk.filename,
                func.count(FileChunk.id).label("chunk_count"),
            )
            .where(FileChunk.user_id == user_id)
            .group_by(FileChunk.file_id, FileChunk.filename)
        )
        return [
            {"file_id": r.file_id, "filename": r.filename, "chunks": r.chunk_count}
            for r in result
        ]

    async def delete_file(self, user_id: str, file_id: str) -> int:
        result = await self.session.execute(
            delete(FileChunk).where(
                FileChunk.file_id == file_id,
                FileChunk.user_id == user_id,
            )
        )
        await self.session.commit()
        return result.rowcount

    async def get_chunks(self, file_id: str) -> list[dict]:
        result = await self.session.execute(
            select(FileChunk)
            .where(FileChunk.file_id == file_id)
            .order_by(FileChunk.chunk_index)
        )
        rows = result.scalars().all()
        return [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "text": c.text[:200] + "…" if len(c.text) > 200 else c.text,
            }
            for c in rows
        ]


async def get_chunk_repo(
    session: AsyncSession = Depends(get_session),
) -> ChunkRepository:
    return ChunkRepository(session)
