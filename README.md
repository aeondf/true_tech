# MTS AI Hub — True Tech Hack

Умный AI-ассистент в стиле МТС: чат с роутингом по задаче, голос, файлы, Deep Research, долгосрочная память, история диалогов.

---

## Быстрый старт (Docker)

```bash
cp backend/.env.example backend/.env
# Вставьте ваш MWS_API_KEY в backend/.env
docker compose up -d --build
```

| Сервис | Адрес |
|--------|-------|
| **Фронтенд (UI)** | http://localhost:3000 |
| **API (Swagger)** | http://localhost:8000/docs |
| **Health check** | http://localhost:8000/v1/health |

---

## Архитектура

```
docker-compose.yml (root)
├── frontend   :3000  — nginx, раздаёт index.html, проксирует /v1/* → backend
├── backend    :8000  — FastAPI (AI Gateway → MWS API)
├── postgres   :5432  — PostgreSQL 16 + pgvector (история, память, роутер-лог)
└── redis      :6379  — кэш и rate limiting
```

Все LLM-запросы идут через **MWS API** (`api.gpt.mws.ru`) — облачный inference.  
Локальных моделей нет, Ollama не требуется.

---

## Что работает

### Бэкенд
| Функция | Статус | Примечание |
|---------|--------|------------|
| 3-pass роутер | ✅ | MIME → regex → LLM llama-3.1-8b |
| Чат (stream + regular) | ✅ | OpenAI-совместимый прокси |
| Авторизация (register/login/JWT) | ✅ | bcrypt + JWT 7 дней |
| История диалогов | ✅ | Postgres, per-user conversations |
| Долгосрочная память | ✅ | LLM-экстракция фактов, инъекция в system |
| Deep Research | ✅ | 5 подзапросов + web-search + SSE-стриминг |
| Голос — ASR | ✅ | MWS whisper-turbo-local (primary) |
| Голос — TTS | ✅ | edge-tts (Silero опционально) |
| Анализ изображений (VLM) | ✅ | qwen2.5-vl через MWS |
| Генерация изображений | ✅ | qwen-image через MWS |
| Эмбеддинги | ✅ | bge-m3 через MWS |
| Web-search + web-parse | ✅ | DuckDuckGo + BeautifulSoup |

### Фронтенд
| Функция | Статус | Примечание |
|---------|--------|------------|
| Чат-интерфейс (stream) | ✅ | |
| Авторизация (login/register) | ✅ | JWT в localStorage |
| Автологин при перезагрузке | ✅ | |
| Голосовые сообщения | ✅ | запись → ASR → TTS воспроизведение |
| Загрузка изображений (VLM) | ✅ | |
| Deep Research с прогрессом | ✅ | SSE |
| История диалогов | ✅ | сохраняется в Postgres |
| Память пользователя | ✅ | fire-and-forget после каждого ответа |

### Что не реализовано / отключено
| Функция | Причина |
|---------|---------|
| Генерация PPTX | убрана из фронтенда (API-эндпоинт есть) |
| RAG (PDF/DOCX upload) | API-эндпоинт есть, UI не подключён |
| WebSocket голос (`/ws/voice`) | только HTTP voice/message в UI |
| Silero TTS в Docker | требует torch 2GB+, слишком тяжёл для сборки; fallback → edge-tts |
| Семантический поиск по памяти | pgvector таблица есть, поиск по эмбеддингам не подключён |

---

## API эндпоинты

```
# Auth
POST /v1/auth/register          — регистрация (email + password)
POST /v1/auth/login             — логин → JWT

# Chat
POST /v1/chat/completions       — чат (stream или regular, OpenAI-формат)
POST /v1/completions            — text completion
POST /v1/embeddings             — эмбеддинги (bge-m3)
GET  /v1/models                 — список моделей MWS

# History
GET  /v1/history/{user_id}                  — список диалогов
GET  /v1/history/{user_id}/{conv_id}        — сообщения диалога
POST /v1/history/{user_id}/{conv_id}        — сохранить сообщение
DELETE /v1/history/{user_id}/{conv_id}      — удалить диалог

# Memory
GET    /v1/memory/{user_id}             — все факты пользователя
POST   /v1/memory/{user_id}             — upsert факта
DELETE /v1/memory/{user_id}/{key}       — удалить факт
POST   /v1/memory/extract               — fire-and-forget LLM-экстракция

# Voice
POST /v1/voice/message          — аудио → ASR → LLM → TTS → MP3
WS   /v1/ws/voice               — WebSocket голосовой чат

# Vision
POST /v1/vlm/analyze            — анализ изображения (qwen2.5-vl)
POST /v1/image/generate         — генерация изображения (qwen-image)

# Research & Tools
POST /v1/research               — Deep Research (SSE стриминг)
POST /v1/tools/web-search       — поиск DuckDuckGo
POST /v1/tools/web-parse        — парсинг веб-страницы

# System
GET  /v1/health                 — статус сервисов
```

---

## Модели

Полный каталог — в [MODELS.md](MODELS.md).

| Задача | Модель |
|--------|--------|
| Чат (text) | mws-gpt-alpha |
| Код | qwen3-coder-480b-a35b |
| Deep Research | qwen2.5-72b-instruct |
| Роутер (LLM pass) | llama-3.1-8b-instruct |
| Память (экстрактор) | llama-3.1-8b-instruct |
| Эмбеддинги | bge-m3 |
| ASR | whisper-turbo-local |
| VLM | qwen2.5-vl |
| Генерация изображений | qwen-image |

---

## Разработка (без Docker)

```bash
# Postgres + Redis локально
docker compose up -d postgres redis

# Бэкенд
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# В .env: DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mirea
uvicorn app.main:app --reload

# Фронтенд (простой HTTP-сервер)
cd frontend
python server.py   # http://localhost:8005

# Интерактивный диалог с пайплайном (роутер → модель → память)
cd backend
python memory_dialog.py

# Интерактивный тест пайплайна (роутер → модель)
cd backend
python pipeline_test.py
```

### Тесты

```bash
cd backend
pytest tests/ -v -s                          # все тесты
pytest tests/test_auth_history_memory.py -v  # auth + история + память
pytest tests/test_router_llm.py -v -s        # живой LLM-роутер
pytest tests/test_memory_pipeline.py -v -s   # память + модели (интеграционные)
```
