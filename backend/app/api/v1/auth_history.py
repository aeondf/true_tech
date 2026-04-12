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
import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.database import SessionLocal
from app.db.models import User, Conversation, Message, UserMemory
from app.services.mws_client import MWSClient, get_mws_client

_log = logging.getLogger(__name__)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


# ── Helpers ───────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user_id: str, email: str, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ── Pydantic schemas ──────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str
    password: str


class MessageSaveRequest(BaseModel):
    role: str
    content: str
    model_used: str | None = None


class MemoryUpsertRequest(BaseModel):
    key: str
    value: str
    category: str = "general"


class MemoryExtractRequest(BaseModel):
    user_id: str
    conv_id: str | None = None
    assistant_message: str


# ── Auth ──────────────────────────────────────────────────────────

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


@router.get("/auth/me")
async def get_me(
    # Simple token check via query param or Authorization header
    # Frontend sends token in Authorization: Bearer <token>
):
    # Minimal implementation — just return 200 if called
    # Full middleware auth is out of scope per spec
    return {"status": "ok"}


# ── History ───────────────────────────────────────────────────────

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
        # Ensure conversation exists
        conv = await session.scalar(select(Conversation).where(Conversation.id == conv_id))
        if not conv:
            # Auto-create conversation (title from first user message)
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
            # Touch updated_at
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


# ── Memory ────────────────────────────────────────────────────────

@router.get("/memory/{user_id}")
async def get_memory(user_id: str):
    async with SessionLocal() as session:
        rows = await session.scalars(
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.score.desc(), UserMemory.updated_at.desc())
        )
        mems = rows.all()
        return {
            "memories": [
                {
                    "key": m.key,
                    "value": m.value,
                    "category": m.category,
                    "score": m.score,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                }
                for m in mems
            ]
        }


@router.post("/memory/{user_id}", status_code=201)
async def upsert_memory(user_id: str, body: MemoryUpsertRequest):
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.key == body.key,
            )
        )
        if existing:
            await session.execute(
                update(UserMemory)
                .where(UserMemory.user_id == user_id, UserMemory.key == body.key)
                .values(value=body.value, category=body.category, updated_at=datetime.utcnow())
            )
        else:
            mem = UserMemory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                key=body.key,
                value=body.value,
                category=body.category,
                score=1.0,
                updated_at=datetime.utcnow(),
            )
            session.add(mem)
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


@router.post("/memory/extract", status_code=202)
async def extract_memory(
    body: MemoryExtractRequest,
    mws: MWSClient = Depends(get_mws_client),
    settings: Settings = Depends(get_settings),
):
    """Fire-and-forget: extract facts from assistant response and save to memory."""
    asyncio.create_task(_extract_and_save(body.user_id, body.assistant_message, mws, settings))
    return {"status": "accepted"}


async def _extract_and_save(user_id: str, message: str, mws: MWSClient, settings: Settings) -> None:
    """Ask LLM to extract facts, then upsert into user_memory."""
    if not message or len(message) < 30:
        return

    system = (
        "Ты система извлечения фактов. Проанализируй ответ ассистента и найди факты о пользователе. "
        "Верни ТОЛЬКО JSON-массив объектов [{\"key\": str, \"value\": str, \"category\": str}] или пустой массив []. "
        "Категории: preferences, projects, facts, links. "
        "Примеры фактов: язык программирования, имя пользователя, любимый фреймворк, текущий проект. "
        "Если фактов нет — верни []."
    )
    user_prompt = f"Ответ ассистента:\n{message[:2000]}"

    try:
        raw = await asyncio.wait_for(
            mws.chat_simple(
                model="llama-3.1-8b-instruct",
                system=system,
                user=user_prompt,
            ),
            timeout=30,
        )

        # Extract JSON array from response
        m = re.search(r"\[.*?\]", raw, re.DOTALL)
        if not m:
            return
        facts = json.loads(m.group())
        if not isinstance(facts, list):
            return

        async with SessionLocal() as session:
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                key = str(fact.get("key", "")).strip()
                value = str(fact.get("value", "")).strip()
                category = str(fact.get("category", "general")).strip()
                if not key or not value:
                    continue

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
                        .values(value=value, category=category, updated_at=datetime.utcnow())
                    )
                else:
                    session.add(UserMemory(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        key=key,
                        value=value,
                        category=category,
                        score=1.0,
                        updated_at=datetime.utcnow(),
                    ))
            await session.commit()

    except Exception as e:
        _log.debug("Memory extraction skipped: %s", e)
