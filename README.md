# MTS AI Gateway

AI-платформа с умным роутингом запросов, долгосрочной памятью, Deep Research и голосовым вводом/выводом. Работает поверх MWS API (OpenAI-совместимый).

---

## Стек

| Слой | Технология |
|---|---|
| Backend | FastAPI · SQLAlchemy async · PostgreSQL + pgvector · Redis |
| Frontend | Vanilla JS (модули) · nginx |
| AI | MWS API (Qwen3, Llama 3.3, DeepSeek-R1, …) |
| TTS | edge-tts |
| Deploy | Docker Compose |

---

## Быстрый старт

```bash
# 1. Клонировать и настроить переменные
cp backend/.env.example backend/.env
# Вписать MWS_API_KEY и другие ключи в .env

# 2. Запустить
docker compose up --build -d

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

> При первом запуске Alembic автоматически создаёт схему БД. При повторном — безопасно пропускает.

---

## Архитектура

```
Browser (localhost:3000)
    └── nginx
        ├── /          → static (index.html + js/ + styles/)
        └── /v1/*      → backend:8000

Backend (FastAPI)
    ├── /v1/auth/              JWT-регистрация и вход
    ├── /v1/chat/completions   SSE-стриминг через MWS API + роутер
    ├── /v1/research           Deep Research (SSE: subqueries → parse → synthesis)
    ├── /v1/voice/message      STT (Whisper) + LLM + TTS (edge-tts)
    ├── /v1/memory/{user_id}   Долгосрочная память (pgvector)
    ├── /v1/history/{user_id}  История диалогов
    ├── /v1/files/upload       Загрузка документов (RAG-чанки)
    ├── /v1/image/generate     Генерация изображений
    └── /v1/health             Статус сервисов
```

### Умный роутер (3 прохода)

1. **MIME** — если есть файл/изображение → VLM-модель
2. **Regex** — паттерны кода, исследования, генерации → нужная модель
3. **LLM** — неоднозначный запрос классифицирует `llama-3.1-8b-instruct`

### Память

Ответы ассистента → экстракция фактов (llama-3.1-8b) → pgvector. При следующем сообщении топ-10 фактов инжектируются в system prompt.

---

## Frontend (js/)

| Файл | Назначение |
|---|---|
| `api.js` | `API = '/v1'`, auth headers, uuid, fileToBase64 |
| `memory.js` | Загрузка/инжект памяти |
| `history.js` | Сохранение и загрузка истории |
| `chat.js` | Отправка сообщений, SSE-стриминг |
| `voice.js` | Запись микрофона, отправка voice API |
| `research.js` | Deep Research SSE, Image Gen |
| `ui.js` | Модели, агенты, панели, темы, профиль, Auth |

---

## Переменные окружения (`backend/.env`)

```env
MWS_API_KEY=...
MWS_BASE_URL=https://api.gpt.mws.ru/v1
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mirea
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=...
```

---

## Что работает

| Фича | Статус |
|---|---|
| Чат с роутингом по моделям | ✅ |
| Стриминг ответов (SSE) | ✅ |
| Auth (JWT) + профиль | ✅ |
| История диалогов | ✅ |
| Долгосрочная память | ✅ |
| Загрузка файлов / RAG | ✅ |
| Анализ изображений (VLM) | ✅ |
| Deep Research | ✅ |
| Голосовой ввод + TTS | ✅ (edge-tts) |
| Генерация изображений | ✅ |
| Docker (все ОС) | ✅ |

---

## Тесты

```bash
cd backend

# Unit + integration
.venv/bin/python -m pytest tests/ -v

```
