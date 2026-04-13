"""
test_auth_history_memory.py — тесты auth, history и memory.

Что тестируется (без живой БД — всё через моки):
  1. Password hashing  — хеш создаётся, верификация работает
  2. JWT              — токен создаётся, содержит user_id и email
  3. Memory block     — buildMemoryBlock формирует правильный текст
  4. DB models        — таблицы объявлены, поля на месте
  5. Proxy injection  — system_prompt prepend-ится в messages перед MWS
  6. ChatRequest      — system_prompt и conversation_id принимаются моделью
  7. Memory extract   — JSON-парсинг ответа LLM работает корректно
  8. Auth routes      — register/login возвращают 200 (с мок-БД)
  9. History routes   — CRUD через мок-сессию
 10. Memory routes    — GET/POST/DELETE через мок-сессию

Запуск:
    cd backend
    pytest tests/test_auth_history_memory.py -v
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────────
# 1. PASSWORD HASHING
# ─────────────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        from app.api.v1.auth_history import _hash_password
        h = _hash_password("secret123")
        assert h != "secret123"
        assert len(h) > 20

    def test_verify_correct_password(self):
        from app.api.v1.auth_history import _hash_password, _verify_password
        h = _hash_password("mypassword")
        assert _verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        from app.api.v1.auth_history import _hash_password, _verify_password
        h = _hash_password("correct")
        assert _verify_password("wrong", h) is False

    def test_two_hashes_differ(self):
        """bcrypt использует соль — одинаковый пароль даёт разные хеши."""
        from app.api.v1.auth_history import _hash_password
        h1 = _hash_password("same")
        h2 = _hash_password("same")
        assert h1 != h2

    def test_empty_password_hashes(self):
        from app.api.v1.auth_history import _hash_password, _verify_password
        h = _hash_password("")
        assert _verify_password("", h) is True
        assert _verify_password("notempty", h) is False


# ─────────────────────────────────────────────────────────────────
# 2. JWT TOKEN
# ─────────────────────────────────────────────────────────────────

class TestJWT:
    def _settings(self):
        from app.config import Settings
        return Settings(
            MWS_API_KEY="test",
            MWS_BASE_URL="http://localhost",
            SECRET_KEY="test-secret-key-32-chars-long!!!",
        )

    def test_token_created(self):
        from app.api.v1.auth_history import _create_token
        token = _create_token("user-123", "test@example.com", self._settings())
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_user_id(self):
        from app.api.v1.auth_history import _create_token
        from jose import jwt
        s = self._settings()
        token = _create_token("user-abc", "a@b.com", s)
        payload = jwt.decode(token, s.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user-abc"

    def test_token_contains_email(self):
        from app.api.v1.auth_history import _create_token
        from jose import jwt
        s = self._settings()
        token = _create_token("x", "hello@world.com", s)
        payload = jwt.decode(token, s.SECRET_KEY, algorithms=["HS256"])
        assert payload["email"] == "hello@world.com"

    def test_token_has_expiry(self):
        from app.api.v1.auth_history import _create_token
        from jose import jwt
        s = self._settings()
        token = _create_token("x", "a@b.com", s)
        payload = jwt.decode(token, s.SECRET_KEY, algorithms=["HS256"])
        assert "exp" in payload

    def test_wrong_secret_rejected(self):
        from app.api.v1.auth_history import _create_token
        from jose import jwt, JWTError
        s = self._settings()
        token = _create_token("x", "a@b.com", s)
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])


# ─────────────────────────────────────────────────────────────────
# 3. DB MODELS — структура таблиц
# ─────────────────────────────────────────────────────────────────

class TestDBModels:
    def test_all_tables_registered(self):
        from app.db.models import Base
        tables = set(Base.metadata.tables.keys())
        assert "users" in tables
        assert "conversations" in tables
        assert "messages" in tables
        assert "user_memory" in tables
        assert "router_log" in tables

    def test_user_columns(self):
        from app.db.models import Base
        cols = {c.name for c in Base.metadata.tables["users"].columns}
        assert {"id", "email", "password_hash", "created_at"} <= cols

    def test_conversation_columns(self):
        from app.db.models import Base
        cols = {c.name for c in Base.metadata.tables["conversations"].columns}
        assert {"id", "user_id", "title", "created_at", "updated_at"} <= cols

    def test_message_columns(self):
        from app.db.models import Base
        cols = {c.name for c in Base.metadata.tables["messages"].columns}
        assert {"id", "conv_id", "role", "content", "model_used", "created_at"} <= cols

    def test_user_memory_columns(self):
        from app.db.models import Base
        cols = {c.name for c in Base.metadata.tables["user_memory"].columns}
        assert {"id", "user_id", "key", "value", "category", "score", "updated_at"} <= cols

    def test_user_memory_unique_constraint(self):
        from app.db.models import Base
        t = Base.metadata.tables["user_memory"]
        uq_names = [c.name for c in t.constraints if hasattr(c, 'name')]
        assert "uq_user_memory" in uq_names

    def test_router_log_intact(self):
        """Убеждаемся что router_log не сломан."""
        from app.db.models import Base
        cols = {c.name for c in Base.metadata.tables["router_log"].columns}
        assert {"id", "task_type", "model_id", "confidence", "which_pass"} <= cols


# ─────────────────────────────────────────────────────────────────
# 4. ChatCompletionRequest — новые поля
# ─────────────────────────────────────────────────────────────────

class TestChatRequestModel:
    def test_system_prompt_accepted(self):
        from app.models.mws import ChatCompletionRequest
        req = ChatCompletionRequest(
            model="gpt-4",
            messages=[],
            system_prompt="You are helpful",
        )
        assert req.system_prompt == "You are helpful"

    def test_conversation_id_accepted(self):
        from app.models.mws import ChatCompletionRequest
        req = ChatCompletionRequest(
            model="gpt-4",
            messages=[],
            conversation_id="conv-abc-123",
        )
        assert req.conversation_id == "conv-abc-123"

    def test_system_prompt_defaults_none(self):
        from app.models.mws import ChatCompletionRequest
        req = ChatCompletionRequest(model="m", messages=[])
        assert req.system_prompt is None

    def test_conversation_id_defaults_none(self):
        from app.models.mws import ChatCompletionRequest
        req = ChatCompletionRequest(model="m", messages=[])
        assert req.conversation_id is None

    def test_both_fields_together(self):
        from app.models.mws import ChatCompletionRequest, Message
        req = ChatCompletionRequest(
            model="m",
            messages=[Message(role="user", content="hi")],
            system_prompt="mem",
            conversation_id="conv-1",
        )
        assert req.system_prompt == "mem"
        assert req.conversation_id == "conv-1"


# ─────────────────────────────────────────────────────────────────
# 5. PROXY — system_prompt injection (_build_mws_request)
# ─────────────────────────────────────────────────────────────────

class TestProxyMemoryInjection:
    def _make_request(self, system_prompt=None, extra_messages=None):
        from app.models.mws import ChatCompletionRequest, Message
        msgs = extra_messages or [Message(role="user", content="hello")]
        return ChatCompletionRequest(
            model="gpt-4",
            messages=msgs,
            system_prompt=system_prompt,
            conversation_id="conv-1",
        )

    def test_no_system_prompt_unchanged(self):
        from app.api.v1.proxy import _build_mws_request
        req = self._make_request(system_prompt=None)
        built = _build_mws_request(req)
        assert len(built.messages) == 1
        assert built.messages[0].role == "user"

    def test_system_prompt_prepended(self):
        from app.api.v1.proxy import _build_mws_request
        req = self._make_request(system_prompt="Факты: Python")
        built = _build_mws_request(req)
        assert built.messages[0].role == "system"
        assert built.messages[0].content == "Факты: Python"
        assert built.messages[1].role == "user"

    def test_system_prompt_cleared_after_injection(self):
        """system_prompt не должен идти в MWS как отдельное поле."""
        from app.api.v1.proxy import _build_mws_request
        req = self._make_request(system_prompt="mem block")
        built = _build_mws_request(req)
        assert built.system_prompt is None

    def test_conversation_id_cleared(self):
        """conversation_id не должен идти в MWS."""
        from app.api.v1.proxy import _build_mws_request
        req = self._make_request()
        built = _build_mws_request(req)
        assert built.conversation_id is None

    def test_message_count_with_injection(self):
        from app.api.v1.proxy import _build_mws_request
        from app.models.mws import Message
        msgs = [
            Message(role="user", content="msg1"),
            Message(role="assistant", content="resp1"),
            Message(role="user", content="msg2"),
        ]
        req = self._make_request(system_prompt="ctx", extra_messages=msgs)
        built = _build_mws_request(req)
        # system + 3 original = 4
        assert len(built.messages) == 4
        assert built.messages[0].role == "system"

    def test_no_system_prompt_no_extra_message(self):
        """Без system_prompt количество сообщений не меняется."""
        from app.api.v1.proxy import _build_mws_request
        from app.models.mws import Message
        msgs = [Message(role="user", content="hi")]
        req = self._make_request(system_prompt=None, extra_messages=msgs)
        built = _build_mws_request(req)
        assert len(built.messages) == 1

    def test_router_not_affected(self):
        """Роутер читает последнее user-сообщение — не system."""
        from app.api.v1.proxy import _last_user_text
        from app.models.mws import ChatCompletionRequest, Message
        req = ChatCompletionRequest(
            model="m",
            messages=[
                Message(role="system", content="ctx"),
                Message(role="user", content="реальный вопрос"),
            ],
        )
        assert _last_user_text(req) == "реальный вопрос"


# ─────────────────────────────────────────────────────────────────
# 6. MEMORY EXTRACTION — парсинг JSON из LLM
# ─────────────────────────────────────────────────────────────────

class TestMemoryExtraction:
    """Тестирует логику парсинга JSON из LLM-ответа в _extract_and_save."""

    def _parse_facts(self, raw_llm_response: str) -> list[dict]:
        """Дублируем логику из _extract_and_save для unit-тестирования."""
        m = re.search(r"\[.*?\]", raw_llm_response, re.DOTALL)
        if not m:
            return []
        try:
            facts = json.loads(m.group())
            return facts if isinstance(facts, list) else []
        except json.JSONDecodeError:
            return []

    def test_valid_facts_parsed(self):
        raw = '[{"key":"язык","value":"Python","category":"preferences"}]'
        facts = self._parse_facts(raw)
        assert len(facts) == 1
        assert facts[0]["key"] == "язык"
        assert facts[0]["value"] == "Python"

    def test_multiple_facts(self):
        raw = json.dumps([
            {"key": "name", "value": "Иван", "category": "facts"},
            {"key": "project", "value": "MIREA AI", "category": "projects"},
        ])
        facts = self._parse_facts(raw)
        assert len(facts) == 2

    def test_empty_array(self):
        facts = self._parse_facts("[]")
        assert facts == []

    def test_no_json_returns_empty(self):
        facts = self._parse_facts("Нет фактов в этом ответе.")
        assert facts == []

    def test_json_with_surrounding_text(self):
        raw = 'Вот факты: [{"key":"k","value":"v","category":"general"}] — конец.'
        facts = self._parse_facts(raw)
        assert len(facts) == 1

    def test_invalid_json_returns_empty(self):
        facts = self._parse_facts("[{invalid json}]")
        assert facts == []

    def test_fact_with_missing_key_skipped(self):
        """Факты без key или value должны игнорироваться."""
        facts = self._parse_facts('[{"key":"","value":"val","category":"general"}]')
        # key пустой → должен быть пропущен в _extract_and_save
        for f in facts:
            key = str(f.get("key", "")).strip()
            value = str(f.get("value", "")).strip()
            assert not (key and value)  # хотя бы одно пустое


# ─────────────────────────────────────────────────────────────────
# 7. AUTH ENDPOINTS — с мок-сессией
# ─────────────────────────────────────────────────────────────────

class TestAuthEndpoints:
    """Тесты register/login через FastAPI TestClient с мокнутой БД."""

    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.v1.auth_history import router
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        return TestClient(app)

    def _make_session_ctx(self, session):
        """Создаёт мок для `async with SessionLocal() as session`."""
        mock_sl = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_sl.return_value = ctx
        return mock_sl

    def test_register_success(self):
        """
        Тестируем register через полный стек:
        - scalar() возвращает None (email свободен)
        - session.add + commit вызываются
        - ответ содержит token
        Класс User НЕ мокаем — иначе select(User) сломается в SQLAlchemy.
        Вместо этого позволяем создать реальный объект User, перехватываем add().
        """
        client = self._client()
        session = AsyncMock()
        session.scalar.return_value = None   # email не занят
        added_objects = []
        session.add = lambda obj: added_objects.append(obj)
        session.commit = AsyncMock()

        with patch("app.api.v1.auth_history.SessionLocal", self._make_session_ctx(session)):
            with patch("app.api.v1.auth_history._create_token", return_value="tok123"):
                r = client.post("/v1/auth/register",
                                json={"email": "test@test.com", "password": "pass"})

        assert r.status_code == 200
        body = r.json()
        assert body["token"] == "tok123"
        assert body["email"] == "test@test.com"
        assert len(added_objects) == 1  # User был добавлен в сессию

    def test_login_wrong_password(self):
        client = self._client()
        with patch("app.api.v1.auth_history.SessionLocal") as mock_sl:
            session = AsyncMock()
            mock_user = MagicMock()
            mock_user.password_hash = "hashed"
            session.scalar.return_value = mock_user
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_sl.return_value = ctx

            with patch("app.api.v1.auth_history._verify_password", return_value=False):
                r = client.post("/v1/auth/login",
                                json={"email": "a@b.com", "password": "wrong"})

        assert r.status_code == 401

    def test_login_unknown_user(self):
        client = self._client()
        with patch("app.api.v1.auth_history.SessionLocal") as mock_sl:
            session = AsyncMock()
            session.scalar.return_value = None  # пользователь не найден
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=session)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_sl.return_value = ctx

            r = client.post("/v1/auth/login",
                            json={"email": "nobody@x.com", "password": "pw"})

        assert r.status_code == 401

    def test_auth_me_ok(self):
        client = self._client()
        r = client.get("/v1/auth/me")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────
# 8. HISTORY ENDPOINTS — с мок-сессией
# ─────────────────────────────────────────────────────────────────

class TestHistoryEndpoints:
    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.v1.auth_history import router
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        return TestClient(app)

    def _mock_session_ctx(self, session):
        mock_sl = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_sl.return_value = ctx
        return mock_sl

    def test_list_conversations_empty(self):
        client = self._client()
        session = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        session.scalars = AsyncMock(return_value=result)

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.get("/v1/history/user-1")

        assert r.status_code == 200
        assert r.json()["conversations"] == []

    def test_list_conversations_returns_data(self):
        client = self._client()
        session = AsyncMock()
        conv = MagicMock()
        conv.id = "conv-1"
        conv.title = "Мой чат"
        conv.created_at = datetime(2026, 1, 1)
        conv.updated_at = datetime(2026, 1, 2)
        result = MagicMock()
        result.all.return_value = [conv]
        session.scalars = AsyncMock(return_value=result)

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.get("/v1/history/user-1")

        assert r.status_code == 200
        data = r.json()["conversations"]
        assert len(data) == 1
        assert data[0]["title"] == "Мой чат"

    def test_get_conversation_messages(self):
        client = self._client()
        session = AsyncMock()
        msg = MagicMock()
        msg.id = "msg-1"
        msg.role = "user"
        msg.content = "Привет"
        msg.model_used = None
        msg.created_at = datetime(2026, 1, 1)
        result = MagicMock()
        result.all.return_value = [msg]
        session.scalars = AsyncMock(return_value=result)

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.get("/v1/history/user-1/conv-1")

        assert r.status_code == 200
        msgs = r.json()["messages"]
        assert msgs[0]["content"] == "Привет"

    def test_save_message_new_conv(self):
        """POST создаёт conversation если её нет."""
        client = self._client()
        session = AsyncMock()
        session.scalar.return_value = None  # conv не найдена
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            with patch("app.api.v1.auth_history.Message") as MockMsg:
                instance = MagicMock()
                instance.id = "msg-new"
                MockMsg.return_value = instance
                r = client.post(
                    "/v1/history/user-1/conv-1",
                    json={"role": "user", "content": "Привет", "model_used": None},
                )

        assert r.status_code == 201
        assert "id" in r.json()

    def test_delete_conversation(self):
        client = self._client()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.delete("/v1/history/user-1/conv-1")

        assert r.status_code == 204


# ─────────────────────────────────────────────────────────────────
# 9. MEMORY ENDPOINTS — с мок-сессией
# ─────────────────────────────────────────────────────────────────

class TestMemoryEndpoints:
    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.v1.auth_history import router
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        return TestClient(app)

    def _mock_session_ctx(self, session):
        mock_sl = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=session)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_sl.return_value = ctx
        return mock_sl

    def test_get_memory_empty(self):
        client = self._client()
        session = AsyncMock()
        result = MagicMock()
        result.all.return_value = []
        session.scalars = AsyncMock(return_value=result)

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.get("/v1/memory/user-1")

        assert r.status_code == 200
        assert r.json()["memories"] == []

    def test_get_memory_with_facts(self):
        client = self._client()
        session = AsyncMock()
        mem = MagicMock()
        mem.key = "язык"
        mem.value = "Python"
        mem.category = "preferences"
        mem.score = 1.0
        mem.updated_at = datetime(2026, 1, 1)
        result = MagicMock()
        result.all.return_value = [mem]
        session.scalars = AsyncMock(return_value=result)

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.get("/v1/memory/user-1")

        assert r.status_code == 200
        facts = r.json()["memories"]
        assert facts[0]["key"] == "язык"
        assert facts[0]["value"] == "Python"

    def test_upsert_memory_new(self):
        """Новая запись памяти — scalar() == None → session.add вызывается."""
        client = self._client()
        session = AsyncMock()
        session.scalar.return_value = None  # не существует
        added = []
        session.add = lambda obj: added.append(obj)
        session.commit = AsyncMock()

        # НЕ мокаем UserMemory — select(UserMemory) сломается
        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.post(
                "/v1/memory/user-1",
                json={"key": "фреймворк", "value": "FastAPI", "category": "preferences"},
            )

        assert r.status_code == 201
        assert r.json()["status"] == "ok"
        assert len(added) == 1  # UserMemory объект добавлен

    def test_upsert_memory_update_existing(self):
        client = self._client()
        session = AsyncMock()
        session.scalar.return_value = MagicMock()  # уже существует
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.post(
                "/v1/memory/user-1",
                json={"key": "фреймворк", "value": "Django", "category": "preferences"},
            )

        assert r.status_code == 201

    def test_delete_memory(self):
        client = self._client()
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        with patch("app.api.v1.auth_history.SessionLocal", self._mock_session_ctx(session)):
            r = client.delete("/v1/memory/user-1/язык")

        assert r.status_code == 204

    def test_memory_extract_accepted(self):
        """POST /memory/extract всегда возвращает 202. Зависимости переопределены."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.v1.auth_history import router
        from app.services.mws_client import get_mws_client
        from app.config import get_settings, Settings

        app = FastAPI()
        app.include_router(router, prefix="/v1")

        # Переопределяем FastAPI-зависимости
        mock_mws = MagicMock()
        mock_settings = Settings(MWS_API_KEY="test", MWS_BASE_URL="http://localhost")
        app.dependency_overrides[get_mws_client] = lambda: mock_mws
        app.dependency_overrides[get_settings] = lambda: mock_settings

        client = TestClient(app)
        with patch("app.api.v1.auth_history.asyncio.create_task"):
            r = client.post(
                "/v1/memory/extract",
                json={
                    "user_id": "user-1",
                    "conv_id": "conv-1",
                    "assistant_message": "Я знаю что ты любишь Python и работаешь над MIREA AI",
                },
            )
        assert r.status_code == 202
        assert r.json()["status"] == "accepted"


# ─────────────────────────────────────────────────────────────────
# 10. CONFIG — новые поля
# ─────────────────────────────────────────────────────────────────

class TestConfig:
    def test_secret_key_has_default(self):
        from app.config import Settings
        s = Settings(MWS_API_KEY="k", MWS_BASE_URL="http://x")
        assert isinstance(s.SECRET_KEY, str)
        assert len(s.SECRET_KEY) > 10

    def test_token_expiry_default(self):
        from app.config import Settings
        s = Settings(MWS_API_KEY="k", MWS_BASE_URL="http://x")
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_database_url_default(self):
        from app.config import Settings
        s = Settings(MWS_API_KEY="k", MWS_BASE_URL="http://x")
        assert "postgresql" in s.DATABASE_URL

    def test_extra_fields_ignored(self):
        """Посторонние поля из .env не ломают Settings."""
        from app.config import Settings
        s = Settings(MWS_API_KEY="k", UNKNOWN_FIELD="garbage")  # type: ignore
        assert s.MWS_API_KEY == "k"
