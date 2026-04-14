from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_settings = get_settings()
engine = create_async_engine(_settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _run_migrations_sync() -> None:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    command.upgrade(config, "head")


async def init_db() -> None:
    await asyncio.to_thread(_run_migrations_sync)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
