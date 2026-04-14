# MTS AI — Architecture & UserFlow

## Компонентная схема

```mermaid
graph TB
    subgraph Browser["Браузер (localhost:3000)"]
        UI["Vanilla JS\nchat · voice · research · memory · agents"]
    end

    subgraph Nginx["nginx :3000"]
        Proxy["/v1/* → backend:8000"]
    end

    subgraph Backend["FastAPI :8000"]
        Chat["/v1/chat/completions"]
        Research["/v1/research"]
        Voice["/v1/voice/message"]
        VLM["/v1/vlm/analyze"]
        Image["/v1/image/generate"]
        Mem["/v1/memory/"]
        Hist["/v1/history/"]
        Auth["/v1/auth/"]

        Router["Smart Router\nMIME → Regex → LLM"]
        MemSvc["Memory Service\npgvector scoring"]
        MWSClient["MWSClient\nhttpx + retry"]
        ASR["ASR (Whisper)"]
        TTS["TTS (edge-tts)"]
        WebSearch["DuckDuckGo"]
        WebParser["BS4 + lxml"]
    end

    subgraph Stores["Хранилища"]
        PG[("PostgreSQL\n+ pgvector")]
        Redis[("Redis 7")]
    end

    subgraph MWS["MWS API  api.gpt.mws.ru"]
        LLM["LLM  mws-gpt-alpha · qwen3-coder · llama"]
        VLMAPI["VLM  qwen2.5-vl-72b"]
        ImgAPI["Image Gen"]
    end

    Browser --> Nginx --> Backend

    Chat --> Router --> MWSClient
    Chat --> MemSvc --> PG
    Research --> WebSearch
    Research --> WebParser
    Research --> MWSClient
    Voice --> ASR --> MWSClient --> TTS
    VLM --> MWSClient
    Image --> MWSClient
    Auth --> PG
    Hist --> PG
    Mem --> PG
    Backend --> Redis

    MWSClient --> LLM
    MWSClient --> VLMAPI
    MWSClient --> ImgAPI
```

---

## AI-модели

| Роль | Модель |
|---|---|
| Чат / синтез | `mws-gpt-alpha` |
| Код | `qwen3-coder-480b-a35b` |
| Роутер · экстракция фактов · research-запросы | `llama-3.1-8b-instruct` |
| Vision | `qwen2.5-vl-72b-instruct` |
| Генерация изображений | MWS Image endpoint |
| ASR | Whisper-compatible |
| TTS | edge-tts (SvetlanaNeural) |

Дополнительно в UI: `DeepSeek-R1`, `Llama-3.3-70b`, `GLM-4.6`, `Gemma`, `Kimi K2`.

---

## Внешние зависимости

| | Тип | Назначение |
|---|---|---|
| `api.gpt.mws.ru` | SaaS HTTP/SSE | LLM, VLM, Image Gen |
| DuckDuckGo | Публичный API | Поиск в Deep Research |
| edge-tts | Библиотека | Синтез речи |
| PostgreSQL + pgvector | Docker | История, память, сессии |
| Redis | Docker | Кэш |

---

## Умный роутер — 3 прохода

```mermaid
flowchart LR
    MSG[Запрос] --> P1{MIME}
    P1 -->|файл / фото| VLM_R[VLM · parse]
    P1 -->|текст| P2{Regex}
    P2 -->|код| CODE[qwen3-coder-480b]
    P2 -->|research| RES[Research pipeline]
    P2 -->|нарисуй| IMG[Image Gen]
    P2 -->|?| P3{LLM\nllama-3.1-8b}
    P3 --> MODEL[task_type → модель]
```

---

## Память — жизненный цикл

```
ответ ассистента
  → async: llama-3.1-8b → key/value/category
  → pgvector embed (1536d) → INSERT user_memory
  → следующий запрос: SELECT TOP-8 cosine+recency
  → инжект в system_prompt
```

---

## UserFlow

```mermaid
flowchart TD
    U0([localhost:3000]) --> AUTH{Авторизован?}
    AUTH -->|Нет| LOGIN[POST /v1/auth/login\nJWT → localStorage]
    AUTH -->|Да| CHAT_UI
    LOGIN --> CHAT_UI[Экран чата]

    CHAT_UI --> INPUT{Ввод}

    INPUT -->|Текст| TC[POST /v1/chat/completions]
    TC --> R1[Router: MIME→Regex→llama-3.1-8b] --> MEM[pgvector TOP-8] --> MWSC[mws-gpt-alpha  SSE]
    MWSC -->|tokens| CHAT_UI
    MWSC -.->|async| EXT[extract facts → pgvector]

    INPUT -->|Голос| VC[POST /v1/voice/message]
    VC --> V1[ASR Whisper] --> V2[mws-gpt-alpha] --> V3[edge-tts MP3]
    V3 --> CHAT_UI

    INPUT -->|Файл/Фото| FT{Тип}
    FT -->|PDF/DOCX| PA[POST /v1/parse → chat/completions]
    FT -->|Фото| VA[POST /v1/vlm/analyze\nqwen2.5-vl-72b]
    PA --> CHAT_UI
    VA --> CHAT_UI

    INPUT -->|Research| RA[POST /v1/research  SSE]
    RA --> B1[llama-3.1-8b ×4 подзапроса] --> B2[DuckDuckGo ×4] --> B3[BS4 парсинг] --> B4[mws-gpt-alpha синтез]
    B4 -->|SSE| CHAT_UI

    INPUT -->|Image Gen| IA[POST /v1/image/generate]
    IA -->|PNG| CHAT_UI
```

---

## Контур сервисов по сценариям

```
ТЕКСТОВЫЙ ЧАТ
  Browser → nginx → /v1/chat/completions
    → Router (MIME → Regex → llama-3.1-8b)
    → pgvector TOP-8 → system_prompt
    → MWS API [mws-gpt-alpha | qwen3-coder]  SSE → Browser
    → async: llama-3.1-8b → pgvector
    → PostgreSQL: Message + Conversation

ГОЛОС
  Browser → /v1/voice/message
    → ASR (Whisper) → mws-gpt-alpha → edge-tts → MP3 → Browser

VLM
  Browser → /v1/vlm/analyze
    → qwen2.5-vl-72b → текст → Browser

DEEP RESEARCH
  Browser → /v1/research  SSE
    → llama-3.1-8b (×4 подзапроса)
    → DuckDuckGo (×4 параллельно) → BS4 парсинг
    → mws-gpt-alpha (синтез + сноски) → SSE → Browser

IMAGE GEN
  Browser → /v1/image/generate
    → MWS Image API → base64 PNG → Browser
```
