# MTS AI Hub — True Tech Hack

Умный AI-ассистент: чат, голос, файлы, Deep Research, генерация изображений.
Все LLM-запросы идут через **MWS API** (`api.gpt.mws.ru`) — локальных моделей нет.

---

## Быстрый старт

```bash
cp backend/.env.example backend/.env
# Заполнить MWS_API_KEY в backend/.env
docker compose up --build
```

| Сервис | Адрес |
|--------|-------|
| API (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/v1/health |

---

## Архитектура

```
docker-compose.yml
├── backend   :8000  — FastAPI (AI Gateway → MWS API)
├── postgres  :5432  — PostgreSQL + pgvector
└── redis     :6379  — rate limiting
```

Каждый запрос проходит через **роутер** → подбирается модель и инструменты → запрос уходит в MWS API.

```
Запрос
  └─ RouterClient (детерминированные правила → LLM fallback)
       └─ CascadeRouter (параллельный web_search + web_parse если нужно)
            └─ MemoryRetriever (pgvector cosine search → system prompt)
                 └─ ContextCompressor (саммари истории > 8000 токенов)
                      └─ MWSClient → MWS API
```

---

## Модели

| Задача | Модель |
|--------|--------|
| Чат, роутинг | mws-gpt-alpha |
| Код | qwen3-coder-480b-a35b |
| Deep Research / длинный контекст | qwen2.5-72b-instruct |
| Эмбеддинги (RAG, память) | bge-m3 |
| Распознавание речи | whisper-turbo-local |
| Анализ изображений (VLM) | cotype-pro-vl-32b |
| Генерация изображений | qwen-image |

Полный каталог MWS — в [MODELS.md](MODELS.md).

---

## API

```
POST /v1/chat/completions       — чат со стримингом (OpenAI-совместимый)
POST /v1/research               — Deep Research с SSE прогрессом
POST /v1/voice/message          — голос → ASR → LLM → TTS → MP3
WS   /v1/voice/ws/voice         — голосовой чат через WebSocket
POST /v1/files/upload           — загрузить PDF/DOCX/TXT для RAG
POST /v1/image/generate         — генерация изображения (qwen-image)
POST /v1/vlm/analyze            — анализ изображения по URL (cotype-pro-vl-32b)
POST /v1/embeddings             — эмбеддинги (bge-m3)
POST /v1/tools/web-search       — поиск DuckDuckGo
POST /v1/tools/web-parse        — парсинг веб-страницы
GET  /v1/memory/{user_id}       — факты о пользователе
POST /v1/memory/{user_id}/search — семантический поиск по памяти
GET  /v1/history/{user_id}      — история разговоров
GET  /v1/models                 — список доступных моделей
GET  /v1/health                 — статус сервисов
```

### Deep Research (`/v1/research`)

SSE-стрим из 5 событий:

```
event: progress  {"step": 1, "message": "Генерирую подзапросы…"}
event: progress  {"step": 2, "sub_queries": [...]}
event: progress  {"step": 3, "message": "Ищу и парсю страницы…"}
event: progress  {"step": 4, "pages_fetched": N}
event: progress  {"step": 5, "message": "Синтезирую ответ…"}
event: done      {"answer": "..."}
# или
event: error     {"message": "..."}
```

Пайплайн: генерация 5 под-запросов → параллельный поиск + парсинг страниц → синтез с источниками.

---

## Что реализовано

### Роутинг
- **Детерминированные правила** — вложение аудио → ASR, изображение → VLM, файл → RAG, URL → web_parse, кодовые ключевые слова → code. Без LLM-вызова.
- **LLM fallback** — mws-gpt-alpha с temperature=0, если правила не сработали. Confidence < 0.7 → text.
- **CascadeRouter** — параллельный web_search + web_parse за один запрос, результат подкладывается в system-промпт.

### Память и контекст
- **MemoryExtractor** — после каждого ответа LLM извлекает факты о пользователе (имя, интересы, профессия), эмбеддит и хранит в pgvector.
- **MemoryRetriever** — cosine-поиск по фактам, топ-K вставляется в system-промпт.
- **ContextCompressor** — история > 8000 токенов → LLM делает саммари старых сообщений.

### RAG
- Загрузка PDF / DOCX / TXT → чанки по 512 токенов с overlap 64 → bge-m3 эмбеддинги → pgvector (IVFFlat).
- При `task_type=file_qa` — cosine-поиск top-5 чанков → в system-промпт.

### Голос
- HTTP: аудио → Whisper (MWS) → LLM (max 300 токенов, кратко для TTS) → edge-tts → MP3.
- WebSocket: бинарные чанки → транскрипт → стриминг токенов → MP3.
- Валидация MIME-типа на входе.

### Изображения
- Генерация: промпт → qwen-image → URL картинки.
- Анализ: URL + вопрос → cotype-pro-vl-32b → текст.

### Инфраструктура
- Rate limiting через Redis (60 req/min по умолчанию).
- Retry с экспоненциальным backoff на 429/503 от MWS.
- MWSClient с единым `httpx.AsyncClient` на все запросы.

---

## Что не работает / известные проблемы

- **MemoryExtractor не вызывается** — `extract_and_store` нигде не вызывается после ответа LLM. Факты не накапливаются автоматически.
- **Генерация PPTX** — эндпоинт упоминается в тестах (`/v1/tools/generate-pptx`), но `tools.py` содержит только `web-search` и `web-parse`. Либо удалён, либо не подключён к роутеру.
- **WebSocket голос без истории** — каждый чанк обрабатывается отдельно, контекст разговора не накапливается.
- **images.py использует прямой httpx** вместо `MWSClient` — нет retry, нет единого timeout-конфига.
- **`voice.py` не валидирует размер файла** — теоретически можно залить большой аудиофайл и положить память.
- **Нет аутентификации** — все эндпоинты открыты, `user_id` передаётся клиентом.

---

## Что можно улучшить

### Приоритетное
1. **Вызвать MemoryExtractor** в `proxy.py` после получения ответа — сейчас память не пишется.
2. **Аутентификация** — хотя бы API-ключ / JWT, иначе любой может писать в память и историю любого user_id.
3. **images.py → MWSClient** — унифицировать, чтобы retry и таймауты работали как везде.
4. **Ограничить размер аудио** в `voice.py` (как уже сделано в `files.py`).

### Архитектурное
5. **Кэш роутера в Redis** — одинаковые фразы роутируются по-новому каждый раз, хотя ответ детерминирован.
6. **WebSocket голос с историей** — накапливать `full_text` между чанками одной сессии.
7. **Streaming для Deep Research через WebSocket** — сейчас только HTTP SSE.
8. **Очередь задач** (Celery / ARQ) для long-running операций: research, генерация изображений — освободит воркеры FastAPI.
9. **Метрики** (Prometheus) — сейчас нет счётчиков latency / error rate по моделям.
10. **Тесты** — только ноутбук-тестер, нет pytest-unit тестов для роутера, pipeline и бизнес-логики.

---

## Локальная разработка (без Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # добавить MWS_API_KEY
uvicorn app.main:app --reload
```

Нужны запущенные PostgreSQL (с расширением pgvector) и Redis, либо только Docker для них:

```bash
docker compose up postgres redis -d
```
