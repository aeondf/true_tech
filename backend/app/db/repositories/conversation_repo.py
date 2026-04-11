from __future__ import annotations

import uuid
from fastapi import Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, conversation_id: str, user_id: str) -> Conversation:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            conv = Conversation(id=conversation_id, user_id=user_id)
            self.session.add(conv)
            await self.session.commit()
        return conv

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[dict]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in rows
        ]

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self.session.add(msg)
        await self.session.commit()
        return msg

    async def get_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[dict]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "token_count": m.token_count,
                "created_at": m.created_at.isoformat(),
            }
            for m in rows
        ]

    async def total_tokens(self, conversation_id: str) -> int:
        """Sum of token_count for all messages in a conversation."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.sum(Message.token_count)).where(
                Message.conversation_id == conversation_id,
                Message.token_count.isnot(None),
            )
        )
        total = result.scalar()
        return total or 0

    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        await self.session.execute(
            delete(Message).where(Message.conversation_id == conversation_id)
        )
        result = await self.session.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        await self.session.commit()
        return result.rowcount > 0


async def get_conversation_repo(
    session: AsyncSession = Depends(get_session),
) -> ConversationRepository:
    return ConversationRepository(session)
