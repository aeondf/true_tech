from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class RouterLog(Base):
    __tablename__ = "router_log"

    id             = Column(String, primary_key=True)
    user_id        = Column(String, nullable=True)
    message_preview = Column(Text, nullable=True)   # первые 512 символов
    task_type      = Column(String, nullable=False)
    model_id       = Column(String, nullable=False)
    confidence     = Column(Float, nullable=True)
    which_pass     = Column(Integer, nullable=True)  # 1, 2 или 3
    latency_ms     = Column(Integer, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
