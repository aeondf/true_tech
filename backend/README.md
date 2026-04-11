# True Tech Hack — AI Gateway Backend

Умный ассистент с роутингом, памятью, RAG, голосом и генерацией медиа.

## Быстрый старт

```bash
cp .env.example .env
# Вставь MWS_API_KEY в .env
docker compose up -d
```

Через ~30 секунд доступно:
- **API**: http://localhost:8000/docs
- **OpenWebUI**: http://localhost:3000

## Что умеет

| Запрос | Модель |
|--------|--------|
| Обычный текст | mws-gpt-alpha |
| Код | kodify-2.0 |
| Исследуй / глубокий анализ | cotype-preview-32k |
| Голосовое сообщение | faster-whisper → LLM → edge-tts |
| Анализ изображения | LLaVA |
| Генерация изображения | Stable Diffusion |

## Ключевые эндпоинты

```
POST /v1/chat/completions     — основной чат (OpenAI-совместимый)
POST /v1/files/upload         — загрузить PDF/DOCX/TXT для RAG
POST /v1/voice/message        — голосовое сообщение → MP3-ответ
POST /v1/research             — Deep Research с SSE-прогрессом
POST /v1/tools/generate-pptx  — сгенерировать PowerPoint
POST /v1/tools/web-search     — поиск в интернете
GET  /v1/health               — статус всех сервисов
```

## Разработка

```bash
make run       # локальный запуск с hot-reload
make migrate   # применить миграции БД
make test      # запустить тесты
make lint      # проверка кода
```
