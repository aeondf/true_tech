from __future__ import annotations

"""
Auth, Chat History, and Long-term Memory endpoints.

Routes:
  POST /auth/register
  POST /auth/login
  GET  /auth/me

  GET  /history/{user_id}
  GET  /history/{user_id}/{conv_id}
  POST /history/{user_id}/{conv_id}
  DELETE /history/{user_id}/{conv_id}

  GET    /memory/{user_id}
  POST   /memory/{user_id}
  DELETE /memory/{user_id}/{key}
  POST   /memory/extract
"""
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.database import SessionLocal
from app.db.models import Conversation, Message, User, UserMemory
from app.services.mws_client import MWSClient, get_mws_client

_log = logging.getLogger(__name__)

router = APIRouter()

ALGORITHM = "HS256"


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _create_token(user_id: str, email: str, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _memory_to_dict(memory: UserMemory | dict) -> dict:
    if isinstance(memory, dict):
        updated_at = memory.get("updated_at")
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()
        return {
            "key": memory.get("key"),
            "value": memory.get("value"),
            "category": memory.get("category", "general"),
            "score": memory.get("score", 1.0),
            "updated_at": updated_at,
        }
    return {
        "key": memory.key,
        "value": memory.value,
        "category": memory.category,
        "score": memory.score,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


def _parse_memory_facts(raw: str) -> list[dict]:
    match = re.search(r"\[.*?\]", raw or "", re.DOTALL)
    if not match:
        return []
    try:
        facts = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    return facts if isinstance(facts, list) else []


def _normalize_memory_fact(fact: dict) -> dict | None:
    if not isinstance(fact, dict):
        return None
    key = str(fact.get("key", "")).strip()
    value = str(fact.get("value", "")).strip()
    category = str(fact.get("category", "general")).strip() or "general"
    if not key or not value:
        return None
    return {"key": key, "value": value, "category": category}


def _build_memory_extraction_prompt(user_message: str | None, assistant_message: str) -> str:
    parts: list[str] = []
    if user_message:
        parts.append(f"Сообщение пользователя:\n{user_message[:1200]}")
    if assistant_message:
        parts.append(f"Ответ ассистента:\n{assistant_message[:1800]}")
    return "\n\n".join(parts).strip()


async def _upsert_memory_fact(
    session: AsyncSession,
    user_id: str,
    key: str,
    value: str,
    category: str,
    score: float = 1.0,
) -> dict:
    now = datetime.utcnow()
    existing = await session.scalar(
        select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.key == key,
        )
    )
    if existing:
        await session.execute(
            update(UserMemory)
            .where(UserMemory.user_id == user_id, UserMemory.key == key)
            .values(value=value, category=category, updated_at=now)
        )
    else:
        session.add(UserMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            score=score,
            updated_at=now,
        ))
    return _memory_to_dict({
        "key": key,
        "value": value,
        "category": category,
        "score": score,
        "updated_at": now,
    })


async def _extract_and_save(
    user_id: str,
    user_message: str | None,
    assistant_message: str,
    mws: MWSClient,
) -> list[dict]:
    """Ask LLM to extract user facts from the latest turn and persist them."""
    prompt = _build_memory_extraction_prompt(user_message, assistant_message)
    if len(prompt) < 30:
        return []

    system = (
        "Ты система извлечения пользовательской памяти. Проанализируй последнее сообщение пользователя "
        "и ответ ассистента, сохрани только устойчивые факты о пользователе. "
        "Верни ТОЛЬКО JSON-массив объектов [{\"key\": str, \"value\": str, \"category\": str}] или []. "
        "Категории: preferences, projects, facts, links. "
        "Не сохраняй одноразовые просьбы, общие фразы, догадки и факты не о пользователе."
    )

    try:
        raw = await mws.chat_simple(
            model="llama-3.1-8b-instruct",
            system=system,
            user=prompt,
        )
        facts = _parse_memory_facts(raw)
        if not facts:
            return []

        persisted: list[dict] = []
        async with SessionLocal() as session:
            for fact in facts:
                normalized = _normalize_memory_fact(fact)
                if not normalized:
                    continue
                persisted.append(
                    await _upsert_memory_fact(
                        session=session,
                        user_id=user_id,
                        key=normalized["key"],
                        value=normalized["value"],
                        category=normalized["category"],
                    )
                )
            await session.commit()
        return persisted
    except Exception as e:
        _log.debug("Memory extraction skipped: %s", e)
        return []


class AuthRequest(BaseModel):
    email: str
    password: str


class MessageSaveRequest(BaseModel):
    role: str
    content: str
    model_used: str | None = None


class ChangePasswordRequest(BaseModel):
    user_id: str
    current_password: str
    new_password: str


class MemoryUpsertRequest(BaseModel):
    key: str
    value: str
    category: str = "general"


class MemoryExtractRequest(BaseModel):
    user_id: str
    conv_id: str | None = None
    user_message: str | None = None
    assistant_message: str


@router.post("/auth/register")
async def register(
    body: AuthRequest,
    settings: Settings = Depends(get_settings),
):
    async with SessionLocal() as session:
        existing = await session.scalar(select(User).where(User.email == body.email))
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            id=str(uuid.uuid4()),
            email=body.email,
            password_hash=_hash_password(body.password),
        )
        session.add(user)
        await session.commit()

        token = _create_token(user.id, user.email, settings)
        return {"user_id": user.id, "email": user.email, "token": token}


@router.post("/auth/login")
async def login(
    body: AuthRequest,
    settings: Settings = Depends(get_settings),
):
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == body.email))
        if not user or not _verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = _create_token(user.id, user.email, settings)
        return {"user_id": user.id, "email": user.email, "token": token}


@router.put("/auth/password")
async def change_password(body: ChangePasswordRequest):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Минимум 6 символов")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.id == body.user_id))
        if not user or not _verify_password(body.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Неверный текущий пароль")
        await session.execute(
            update(User).where(User.id == body.user_id)
            .values(password_hash=_hash_password(body.new_password))
        )
        await session.commit()
    return {"status": "ok"}


@router.get("/auth/me")
async def get_me():
    return {"status": "ok"}


@router.get("/history/{user_id}")
async def list_conversations(user_id: str, limit: int = 50):
    async with SessionLocal() as session:
        rows = await session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        convs = rows.all()
        return {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in convs
            ]
        }


@router.get("/history/{user_id}/{conv_id}")
async def get_conversation(user_id: str, conv_id: str, limit: int = 200):
    async with SessionLocal() as session:
        msgs = await session.scalars(
            select(Message)
            .where(Message.conv_id == conv_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return {
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "model_used": m.model_used,
                    "timestamp": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs.all()
            ]
        }


@router.post("/history/{user_id}/{conv_id}", status_code=201)
async def save_message(user_id: str, conv_id: str, body: MessageSaveRequest):
    async with SessionLocal() as session:
        conv = await session.scalar(select(Conversation).where(Conversation.id == conv_id))
        if not conv:
            title = body.content[:60] if body.role == "user" else "Новый чат"
            conv = Conversation(
                id=conv_id,
                user_id=user_id,
                title=title,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(conv)
        else:
            await session.execute(
                update(Conversation)
                .where(Conversation.id == conv_id)
                .values(updated_at=datetime.utcnow())
            )

        msg = Message(
            id=str(uuid.uuid4()),
            conv_id=conv_id,
            role=body.role,
            content=body.content,
            model_used=body.model_used,
            created_at=datetime.utcnow(),
        )
        session.add(msg)
        await session.commit()
        return {"id": msg.id}


@router.delete("/history/{user_id}/{conv_id}", status_code=204)
async def delete_conversation(user_id: str, conv_id: str):
    async with SessionLocal() as session:
        await session.execute(
            delete(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
            )
        )
        await session.commit()


@router.post("/memory/extract")
async def extract_memory(
    body: MemoryExtractRequest,
    mws: MWSClient = Depends(get_mws_client),
):
    memories = await _extract_and_save(
        user_id=body.user_id,
        user_message=body.user_message,
        assistant_message=body.assistant_message,
        mws=mws,
    )
    return {"status": "ok", "memories": memories}


@router.get("/memory/{user_id}")
async def get_memory(user_id: str):
    async with SessionLocal() as session:
        rows = await session.scalars(
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.score.desc(), UserMemory.updated_at.desc())
        )
        mems = rows.all()
        return {"memories": [_memory_to_dict(m) for m in mems]}


@router.post("/memory/{user_id}", status_code=201)
async def upsert_memory(user_id: str, body: MemoryUpsertRequest):
    async with SessionLocal() as session:
        await _upsert_memory_fact(
            session=session,
            user_id=user_id,
            key=body.key,
            value=body.value,
            category=body.category,
        )
        await session.commit()
        return {"status": "ok"}


@router.delete("/memory/{user_id}/{key}", status_code=204)
async def delete_memory(user_id: str, key: str):
    async with SessionLocal() as session:
        await session.execute(
            delete(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.key == key,
            )
        )
        await session.commit()
