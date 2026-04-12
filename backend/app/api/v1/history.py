"""
Chat history API.

GET  /v1/history/{user_id}                       — list conversations
GET  /v1/history/{user_id}/{conversation_id}      — get messages
DELETE /v1/history/{user_id}/{conversation_id}    — delete conversation
PATCH  /v1/history/{user_id}/{conversation_id}    — rename conversation
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Conversation, Message
from app.db.repositories.conversation_repo import ConversationRepository, get_conversation_repo

router = APIRouter()


class RenameRequest(BaseModel):
    title: str


@router.get("/{user_id}")
async def list_conversations(
    user_id: str,
    limit: int = 50,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    """List all conversations for a user, newest first."""
    return {"conversations": await repo.list_for_user(user_id, limit=limit)}


@router.get("/{user_id}/{conversation_id}")
async def get_messages(
    user_id: str,
    conversation_id: str,
    limit: int = 200,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    """Get all messages in a conversation."""
    messages = await repo.get_messages(conversation_id, limit=limit)
    return {"conversation_id": conversation_id, "messages": messages}


@router.patch("/{user_id}/{conversation_id}")
async def rename_conversation(
    user_id: str,
    conversation_id: str,
    req: RenameRequest,
    session: AsyncSession = Depends(get_session),
):
    """Rename a conversation."""
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = req.title[:512]
    await session.commit()
    return {"id": conversation_id, "title": conv.title}


@router.delete("/{user_id}/{conversation_id}")
async def delete_conversation(
    user_id: str,
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo),
):
    """Delete a conversation and all its messages."""
    deleted = await repo.delete_conversation(conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}
