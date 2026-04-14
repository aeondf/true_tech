# MTS AI 

AI-платформа с умным роутингом запросов, долгосрочной памятью (pgvector), Deep Research и голосовым вводом/выводом. Работает поверх [MWS API](https://api.gpt.mws.ru) (OpenAI-совместимый).

---

## Возможности

| Сценарий | Описание |
|---|---|
| Текстовый чат | Умный роутинг запросов по 3 проходам → нужная модель → SSE-стриминг |
| Голосовой режим | Микрофон → ASR (Whisper) → LLM → TTS (edge-tts) → MP3 |
| Анализ изображений | Загрузка файла или ссылка → qwen2.5-vl-72b → текстовый ответ |
| Deep Research | Запрос → 4 подзапроса → DuckDuckGo → парсинг → синтез с источниками |
| Генерация изображений | Текстовый промпт → MWS Image API → рендер в чате |
| Разбор документов | PDF / DOCX / TXT → чанки → контекст в чате |
| Долгосрочная память | Факты из ответов → pgvector → инжект в системный промпт |
| Мульти-агентный режим | 8 специализированных агентов с предустановленными промптами |

---

## Стек

| Слой | Технология |
|---|---|
| **Backend** | FastAPI 0.115 · SQLAlchemy 2.0 async · Uvicorn |
| **База данных** | PostgreSQL 16 + pgvector · Alembic migrations |
| **Кэш** | Redis 7 |
| **Frontend** | Vanilla JS (ES6 модули) · nginx alpine |
| **AI-модели** | MWS API — Qwen 2.5/3, Llama 3.3, DeepSeek-R1, Kimi K2 и др. |
| **TTS** | edge-tts (Microsoft SvetlanaNeural) |
| **Deploy** | Docker Compose (4 сервиса) |

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd <repo-dir>

# 2. Создать файл переменных окружения
cp backend/.env.example backend/.env
# Вписать MWS_API_KEY и остальные ключи

# 3. Запустить
docker compose up --build -d
```

- **Frontend:** http://localhost:3000
- **Backend API (Swagger):** http://localhost:8000/docs

> При первом запуске Alembic автоматически создаёт схему БД. При повторном — безопасно пропускает.

---

## Переменные окружения

```env
# MWS API
MWS_API_KEY=sk-...
MWS_BASE_URL=https://api.gpt.mws.ru/v1

# Модели
MODEL_TEXT=mws-gpt-alpha
MODEL_CODE=qwen3-coder-480b-a35b
MODEL_LONG=qwen2.5-72b-instruct
MODEL_RESEARCH_QUERY=llama-3.1-8b-instruct
MODEL_RESEARCH_SYNTHESIS=qwen2.5-72b-instruct

# БД
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/mirea
REDIS_URL=redis://redis:6379/0

# Auth
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 дней

# TTS
TTS_VOICE=ru-RU-SvetlanaNeural

# Deep Research
RESEARCH_SUBQUERY_COUNT=4
RESEARCH_SEARCH_RESULTS=3
RESEARCH_CONCURRENCY=4
RESEARCH_PARSE_TIMEOUT=12
RESEARCH_SYNTHESIS_TIMEOUT=75
RESEARCH_MAX_SOURCES=8
RESEARCH_MAX_CONTEXT_CHARS=12000
RESEARCH_MAX_ACTIVE_RUNS=2
```

---

## Архитектура

```
Browser (localhost:3000)
    └── nginx
        ├── /        → static (index.html + js/ + styles/)
        └── /v1/*    → backend:8000

Backend (FastAPI :8000)
    ├── /v1/auth/              JWT-регистрация и вход
    ├── /v1/chat/completions   SSE-стриминг + умный роутер + память
    ├── /v1/research           Deep Research (SSE: подзапросы → парсинг → синтез)
    ├── /v1/voice/message      ASR → LLM → TTS pipeline
    ├── /v1/vlm/analyze        Анализ изображений (VLM)
    ├── /v1/image/generate     Генерация изображений
    ├── /v1/memory/{user_id}   Долгосрочная память (pgvector)
    ├── /v1/history/{user_id}  История диалогов
    ├── /v1/parse/             Разбор документов (PDF/DOCX/TXT)
    └── /v1/health             Статус сервисов
```

### Умный роутер — 3 прохода

1. **MIME** — файл или изображение в запросе → VLM / parse-модель
2. **Regex** — паттерны кода, исследования, генерации → специализированная модель
3. **LLM** — неоднозначный запрос классифицирует `llama-3.1-8b-instruct`

Каждый запрос логируется в таблицу `router_log`: `task_type`, `model_id`, `confidence`, `which_pass`, `latency_ms`.

### Долгосрочная память

```
Ответ ассистента
  → async: llama-3.1-8b → экстракция фактов (key / value / category)
  → pgvector embed → INSERT user_memory
  → следующий запрос: SELECT TOP-8 по cosine similarity + recency
  → инжект в system_prompt
```

---

## API-эндпоинты

### Аутентификация
| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/auth/register` | Регистрация |
| POST | `/v1/auth/login` | Вход, возвращает JWT |
| GET | `/v1/auth/me` | Текущий пользователь |
| POST | `/v1/auth/profile` | Обновление профиля |

### Чат
| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/chat/completions` | Основной чат (stream/json, OpenAI-совместимый) |

### Research и медиа
| Метод | Путь | Описание |
|---|---|---|
| POST | `/v1/research` | Deep Research (SSE) |
| POST | `/v1/voice/message` | Голос → текст → голос |
| POST | `/v1/vlm/analyze` | Анализ изображения |
| POST | `/v1/image/generate` | Генерация изображения |
| POST | `/v1/parse/pdf` | PDF → текст |
| POST | `/v1/parse/docx` | DOCX → текст |

### Данные пользователя
| Метод | Путь | Описание |
|---|---|---|
| GET/POST/DELETE | `/v1/memory/{user_id}` | Управление памятью |
| GET/POST | `/v1/history/{user_id}` | Список диалогов |
| GET/PUT/DELETE | `/v1/history/{user_id}/{conv_id}` | Операции с диалогом |

---

## Схема базы данных

| Таблица | Ключевые поля |
|---|---|
| `users` | id, email, password_hash, created_at |
| `conversations` | id, user_id (FK), title, created_at, updated_at |
| `messages` | id, conversation_id (FK), role, content, model_used, created_at |
| `user_memory` | id, user_id (FK), key, value, category, score (float), updated_at |
| `router_log` | id, user_id, task_type, model_id, confidence, which_pass, latency_ms, created_at |

---

## Frontend-модули (js/)

| Файл | Назначение |
|---|---|
| `main.js` | Глобальное состояние, инициализация, связка событий |
| `chat.js` | Отправка сообщений, SSE-рендер, markdown |
| `voice.js` | Запись микрофона, отправка, воспроизведение |
| `research.js` | Deep Research SSE, генерация изображений |
| `memory.js` | Загрузка и инжект долгосрочной памяти |
| `history.js` | Сайдбар с историей, поиск, переименование |
| `agents.js` | 8 специализированных агентов |
| `models.js` | Список моделей, группировка по вендору |
| `auth-ui.js` | Форма входа/регистрации |
| `api.js` | API-клиент (auth headers, uuid, fileToBase64) |
| `ui.js` | Панели, тема, язык, адаптив |
| `profile.js` | Настройки пользователя |

---

## Docker Compose

```yaml
services:
  postgres:   pgvector/pgvector:pg16   # :5432
  redis:      redis:7-alpine           # :6379
  backend:    Python 3.12 slim         # :8000
  frontend:   nginx:alpine             # :3000
```

Все сервисы в одной сети `app-network`. Frontend проксирует `/v1/*` на backend через nginx.

---

## Тесты

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

---

## Документация

- [ARCHITECTURE.md](ARCHITECTURE.md) — компонентная схема, модели, зависимости, UserFlow

---

## Статус фич

| Фича | Статус |
|---|---|
| Чат с умным роутингом | ✅ |
| SSE-стриминг ответов | ✅ |
| Auth (JWT) + профиль | ✅ |
| История диалогов | ✅ |
| Долгосрочная память (pgvector) | ✅ |
| Разбор документов (PDF/DOCX/TXT) | ✅ |
| Анализ изображений (VLM) | ✅ |
| Deep Research | ✅ |
| Голосовой ввод + TTS | ✅ |
| Генерация изображений | ✅ |
| Docker (все ОС) | ✅ |
