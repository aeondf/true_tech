# MTS AI Hub — True Tech Hack

Умный AI-ассистент в стиле МТС: чат, голос, файлы, Deep Research, генерация презентаций.

## Быстрый старт — одна команда

```bash
cp backend/.env.example backend/.env
# Вставьте MWS_API_KEY в backend/.env
docker compose up -d
```

| Интерфейс | Адрес |
|-----------|-------|
| **MTS AI Hub (фронтенд)** | http://localhost:3001 |
| **API документация** | http://localhost:8000/docs |
| **OpenWebUI** (альтернатив.) | http://localhost:3000 |
| **Media service health** | http://localhost:8010/health |

> Первый запуск скачивает модель `qwen2.5:3b` (~2 GB). Ожидание ~60 сек.

### После запуска — применить миграции БД

```bash
docker compose exec backend alembic upgrade head
```

### Опционально — скачать LLaVA для анализа изображений

```bash
docker compose exec ollama ollama pull llava
```

---

## Архитектура

```
docker-compose.yml (корневой)
├── frontend        :3001  — React + Vite + Three.js (UI)
├── backend         :8000  — FastAPI (AI Gateway)
├── media-service   :8010  — ASR + TTS + VLM + Image Gen
├── postgres        :5432  — PostgreSQL + pgvector
├── redis           :6379  — кэш памяти и rate limiting
├── ollama          :11434 — локальный LLM роутер (qwen2.5:3b)
└── openwebui       :3000  — альтернативный чат-интерфейс
```

### Как фронтенд связан с бэком

В **dev-режиме** (`npm run dev`): Vite proxy перенаправляет `/v1/*` → `localhost:8000`.

В **Docker**: nginx внутри контейнера проксирует `/v1/*` → `backend:8000`.

Переменная `VITE_API_URL` в `frontend/.env` — пустая для Docker (nginx берёт управление), или `http://localhost:8000` для локальной разработки.

---

## Таблица моделей

| Задача | Модель |
|--------|--------|
| Текст, вопросы | mws-gpt-alpha |
| Код | kodify-2.0 |
| Deep Research, длинный контекст | cotype-preview-32k |
| Эмбеддинги (RAG, память) | bge-m3 |
| Распознавание речи | faster-whisper |
| Анализ изображений | LLaVA (Ollama) |
| Генерация изображений | Stable Diffusion |
| Роутинг запросов | qwen2.5:3b (Ollama) |

---

## API эндпоинты

```
POST /v1/chat/completions     — чат со стримингом (OpenAI-совместимый)
POST /v1/files/upload         — загрузить PDF/DOCX/TXT для RAG
POST /v1/voice/message        — голос → LLM → MP3
POST /v1/research             — Deep Research с SSE прогрессом
POST /v1/tools/generate-pptx  — сгенерировать PowerPoint
POST /v1/tools/web-search     — поиск DuckDuckGo
POST /v1/tools/web-parse      — парсинг веб-страницы
POST /v1/image/generate       — генерация изображения
POST /v1/vlm/analyze          — анализ изображения
GET  /v1/health               — статус всех сервисов
GET  /v1/memory/{user_id}     — воспоминания пользователя
```

---

## Разработка (без Docker)

```bash
# Бэкенд
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # добавить MWS_API_KEY
alembic upgrade head
uvicorn app.main:app --reload

# Фронтенд
cd frontend
npm install
npm run dev   # http://localhost:3001
```

```bash
# Другие команды бэкенда
make test      # тесты
make lint      # линтинг
make migrate   # миграции
```

---

## Что реализовано

### Бэкенд
- **Роутер** — детерминированные правила + Qwen LLM для неоднозначных случаев. Confidence < 0.7 → fallback на mws-gpt-alpha. Логирует в `router_logs`
- **Каскадная маршрутизация** — web_search + web_parse запускаются параллельно одним запросом
- **Память** — извлекает факты из разговоров, хранит в pgvector, подкладывает в контекст
- **Сжатие контекста** — история > 8000 токенов → LLM делает саммари старых сообщений
- **RAG** — PDF/DOCX/TXT → чанки → pgvector → поиск по содержимому
- **Deep Research** — 5 параллельных запросов + парсинг страниц + синтез с источниками
- **Голос** — аудио → Whisper → LLM → edge-tts → MP3
- **Генерация PPTX** — LLM генерирует структуру → python-pptx собирает файл
- **Медиа** — Stable Diffusion (генерация), LLaVA (анализ), fallback при недоступности
- **БД** — PostgreSQL + pgvector, IVFFlat индексы, HASH-партиционирование messages

### Фронтенд
- **Чат** — стриминг ответов, Markdown с подсветкой кода, история по дням
- **3D сцена** — Three.js: куб МТС + частицы на экране входа
- **Голосовой ввод** — Web MediaRecorder + анимация волн в реальном времени
- **Deep Research UI** — SSE трекер шагов прямо в чате
- **Настройки** — язык (RU/EN), тема, размер шрифта, авто-маршрутизация, профиль
- **Cmd+K** — палитра команд с поиском
- **Тема** — светлая/тёмная с плавным переключением
- **Drag & Drop** — загрузка файлов перетаскиванием
- **Docker** — nginx проксирует запросы к бэку, SPA fallback

---

## Что ещё нужно сделать

- [ ] **Нагрузочный тест** — 100 воспоминаний + RAG < 200ms
- [ ] **50 тест-кейсов на роутере** — точность > 90%
- [ ] **In-memory векторный индекс** для Deep Research (шаг 4 из ТЗ)
- [ ] **Партиционирование messages** — миграция `002` готова, нужно применить на проде
