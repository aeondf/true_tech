from __future__ import annotations

from fastapi import Depends
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Memory


def _vec_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        id: str,
        user_id: str,
        conversation_id: str | None,
        text: str,
        embedding: list[float],
    ) -> Memory:
        m = Memory(
            id=id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=text,
            embedding=embedding,
        )
        self.session.add(m)
        await self.session.commit()
        return m

    async def get_all(self, user_id: str, limit: int = 50) -> list[dict]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": m.id,
                "text": m.text,
                "conversation_id": m.conversation_id,
                "created_at": m.created_at.isoformat(),
            }
            for m in rows
        ]

    async def search(
        self,
        user_id: str,
        query_vector: list[float],
        top_k: int = 10,
    ) -> list[dict]:
        vec_str = _vec_literal(query_vector)
        result = await self.session.execute(
            text(
                """
                SELECT id, text,
                       1 - (embedding <=> CAST(:vec AS vector(1024))) AS score
                FROM memories
                WHERE user_id = :uid
                ORDER BY embedding <=> CAST(:vec AS vector(1024))
                LIMIT :k
                """
            ),
            {"vec": vec_str, "uid": user_id, "k": top_k},
        )
        return [dict(row._mapping) for row in result]

    async def delete(self, user_id: str, memory_id: str) -> bool:
        result = await self.session.execute(
            delete(Memory).where(
                Memory.id == memory_id, Memory.user_id == user_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    async def delete_all(self, user_id: str) -> int:
        result = await self.session.execute(
            delete(Memory).where(Memory.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount


async def get_memory_repo(
    session: AsyncSession = Depends(get_session),
) -> MemoryRepository:
    return MemoryRepository(session)
