# Доступные модели MWS API

Все модели доступны через `https://api.gpt.mws.ru` (OpenAI-совместимый API).

## Текстовые (Chat / Completion)

| Модель | Параметры | Назначение |
|--------|-----------|------------|
| **mws-gpt-alpha** | — | Основная текстовая модель MWS. Роутинг запросов, общие вопросы, суммаризация |
| **qwen2.5-72b-instruct** | 72B | Длинный контекст, Deep Research, аналитика, сложные рассуждения |
| **qwen3-32b** | 32B | Универсальная Qwen3, баланс качества и скорости |
| **Qwen3-235B-A22B-Instruct-2507-FP8** | 235B (MoE, 22B active) | Флагман Qwen3, максимальное качество |
| **QwQ-32B** | 32B | Reasoning-модель (chain-of-thought), математика, логика |
| **deepseek-r1-distill-qwen-32b** | 32B | DeepSeek R1 дистиллят, reasoning и анализ |
| **llama-3.1-8b-instruct** | 8B | Лёгкая Meta Llama, быстрые ответы, черновики |
| **llama-3.3-70b-instruct** | 70B | Мощная Meta Llama, сложные задачи |
| **gemma-3-27b-it** | 27B | Google Gemma 3, мультиязычность |
| **glm-4.6-357b** | 357B | GLM-4 от Zhipu, большая модель для сложных задач |
| **gpt-oss-20b** | 20B | Компактная open-source GPT |
| **gpt-oss-120b** | 120B | Мощная open-source GPT |
| **kimi-k2-instruct** | — | Moonshot Kimi K2, длинный контекст |
| **T-pro-it-1.0** | — | T-Pro Instruct, русскоязычная модель |

## Кодинг

| Модель | Параметры | Назначение |
|--------|-----------|------------|
| **qwen3-coder-480b-a35b** | 480B (MoE, 35B active) | Специализированная модель для генерации и анализа кода |

## Vision (анализ изображений)

| Модель | Параметры | Назначение |
|--------|-----------|------------|
| **cotype-pro-vl-32b** | 32B | Vision-Language модель, анализ изображений, описание |
| **qwen2.5-vl** | — | Qwen 2.5 Vision, распознавание и анализ изображений |
| **qwen2.5-vl-72b** | 72B | Qwen 2.5 Vision большая, высокое качество анализа |
| **qwen3-vl-30b-a3b-instruct** | 30B (MoE, 3B active) | Qwen3 Vision, лёгкая и быстрая |

Использование через `/v1/chat/completions` с `image_url` в content:
```json
{
  "model": "qwen2.5-vl",
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "Что на картинке?"},
    {"type": "image_url", "image_url": {"url": "https://..."}}
  ]}]
}
```

## Генерация изображений

| Модель | Назначение |
|--------|------------|
| **qwen-image** | Генерация изображений по текстовому описанию |
| **qwen-image-lightning** | Быстрая генерация (меньше качество, выше скорость) |

Эндпоинт: `/v1/images/generations`
```json
{"model": "qwen-image", "prompt": "закат над морем", "size": "1024x1024"}
```

## Распознавание речи (ASR)

| Модель | Назначение |
|--------|------------|
| **whisper-turbo-local** | Whisper Turbo, основная модель ASR |
| **whisper-medium** | Whisper Medium, fallback |

Эндпоинт: `/v1/audio/transcriptions`
```bash
curl -X POST .../v1/audio/transcriptions \
  -F file=@audio.wav -F model=whisper-turbo-local
```

## Эмбеддинги (RAG, память, поиск)

| Модель | Назначение |
|--------|------------|
| **bge-m3** | BAAI BGE-M3, мультиязычные эмбеддинги (основная) |
| **BAAI/bge-multilingual-gemma2** | BGE на базе Gemma2, альтернативные эмбеддинги |
| **qwen3-embedding-8b** | Qwen3 эмбеддинги, 8B параметров |

Эндпоинт: `/v1/embeddings`
```json
{"model": "bge-m3", "input": "текст для эмбеддинга"}
```

---

## Какие модели используются в проекте

| Задача | Модель | Настройка в `.env` |
|--------|--------|--------------------|
| Чат, роутинг | mws-gpt-alpha | `MODEL_TEXT` |
| Код | qwen3-coder-480b-a35b | `MODEL_CODE` |
| Deep Research | qwen2.5-72b-instruct | `MODEL_LONG` |
| Эмбеддинги | bge-m3 | `MODEL_EMBED` |
| ASR | whisper-turbo-local | hardcoded |
| VLM | qwen2.5-vl | default в API |
| Генерация картинок | qwen-image | default в API |
