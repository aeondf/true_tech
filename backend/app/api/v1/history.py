"""
Chat history API.

GET  /v1/history/{user_id}                       — list conversations
GET  /v1/history/{user_id}/{conversation_id}      — get messages
DELETE /v1/history/{user_id}/{conversation_id}    — delete conversation
PATCH  /v1/history/{user_id}/{conversation_id}    — rename conversation
"""
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Conversation, Message, User
from app.db.repositories.conversation_repo import ConversationRepository, get_conversation_repo

router = APIRouter()


class RenameRequest(BaseModel):
    title: str


class SaveMessagesRequest(BaseModel):
    messages: list[dict]  # [{role, content}]
    title: str | None = None


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


@router.post("/{user_id}/{conversation_id}/messages")
async def save_messages(
    user_id: str,
    conversation_id: str,
    req: SaveMessagesRequest,
    session: AsyncSession = Depends(get_session),
):
    """Directly save messages to a conversation (used for image gen, etc.)."""
    # Upsert user
    u = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        session.add(User(id=user_id))

    # Upsert conversation
    conv = (await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()
    if not conv:
        first_user = next((m["content"] for m in req.messages if m.get("role") == "user"), "")
        session.add(Conversation(
            id=conversation_id,
            user_id=user_id,
            title=(req.title or first_user[:80] or "Беседа"),
        ))
    elif req.title and not conv.title:
        conv.title = req.title[:80]

    for m in req.messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role and content:
            session.add(Message(
                id=str(_uuid.uuid4()),
                conversation_id=conversation_id,
                role=role,
                content=content,
            ))

    await session.commit()
    return {"saved": len(req.messages)}


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
