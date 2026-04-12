# MTS AI Hub — True Tech Hack

Умный AI-ассистент в стиле МТС: чат, голос, файлы, Deep Research, генерация презентаций.

## Быстрый старт

```bash
cp backend/.env.example backend/.env
# Вставьте MWS_API_KEY в backend/.env
docker compose up -d --build
```

| Сервис | Адрес |
|--------|-------|
| **API (Swagger)** | http://localhost:8000/docs |
| **Health check** | http://localhost:8000/v1/health |

---

## Архитектура

```
docker-compose.yml
├── backend     :8000  — FastAPI (AI Gateway → MWS API)
├── postgres    :5432  — PostgreSQL + pgvector
└── redis       :6379  — кэш памяти и rate limiting
```

Все LLM-запросы идут через **MWS API** (`api.gpt.mws.ru`) — облачный inference.
Локальных моделей нет, Ollama не требуется.

---

## Модели

Полный каталог доступных моделей MWS API — в [MODELS.md](MODELS.md).

Основные модели проекта:

| Задача | Модель |
|--------|--------|
| Чат, роутинг | mws-gpt-alpha |
| Код | qwen3-coder-480b-a35b |
| Deep Research | qwen2.5-72b-instruct |
| Эмбеддинги (RAG, память) | bge-m3 |
| Распознавание речи | whisper-turbo-local |
| Анализ изображений (VLM) | qwen2.5-vl |
| Генерация изображений | qwen-image |

---

## API эндпоинты

```
POST /v1/chat/completions     — чат со стримингом (OpenAI-совместимый)
POST /v1/files/upload         — загрузить PDF/DOCX/TXT для RAG
POST /v1/voice/message        — голос → ASR → LLM → TTS → MP3
WS   /v1/ws/voice             — голосовой чат через WebSocket
POST /v1/research             — Deep Research с SSE прогрессом
POST /v1/tools/generate-pptx  — сгенерировать PowerPoint
POST /v1/tools/web-search     — поиск DuckDuckGo
POST /v1/tools/web-parse      — парсинг веб-страницы
POST /v1/image/generate       — генерация изображения (qwen-image)
POST /v1/vlm/analyze          — анализ изображения (VLM)
POST /v1/embeddings           — эмбеддинги (bge-m3)
GET  /v1/models               — список доступных моделей
GET  /v1/health               — статус сервисов
GET  /v1/memory/{user_id}     — воспоминания пользователя
POST /v1/memory/{user_id}/search — семантический поиск по памяти
```

---

## Разработка (без Docker)

```bash
# Бэкенд
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # добавить MWS_API_KEY
uvicorn app.main:app --reload

# Тесты
pytest backend/tests/
python backend/tests/test_voice_full.py   # голосовой пайплайн
python backend/tests/test_pptx_gen.py     # генерация PPTX
```

---

## Что реализовано

### Бэкенд
- **Роутер** — детерминированные правила + MWS LLM для неоднозначных случаев. Confidence < 0.7 → fallback на mws-gpt-alpha
- **Каскадная маршрутизация** — web_search + web_parse параллельно с таймаутами и семафорами
- **Память** — извлекает факты из разговоров, хранит в pgvector, подкладывает в контекст
- **Сжатие контекста** — история > 8000 токенов → LLM делает саммари старых сообщений
- **RAG** — PDF/DOCX/TXT → чанки → pgvector → поиск по содержимому
- **Deep Research** — 5 параллельных запросов + парсинг страниц + синтез с источниками (SSE)
- **Голос** — аудио → Whisper (MWS) → LLM → edge-tts → MP3
- **Генерация PPTX** — LLM генерирует структуру → python-pptx собирает файл
- **Генерация изображений** — qwen-image через MWS `/v1/images/generations`
- **Анализ изображений (VLM)** — qwen2.5-vl через MWS chat completions с image_url
- **БД** — PostgreSQL + pgvector, IVFFlat индексы
