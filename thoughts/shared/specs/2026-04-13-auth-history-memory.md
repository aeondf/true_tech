# Auth + History + Memory Specification

## Executive Summary

Добавить в MIREA AI Gateway реальную аутентификацию (email + пароль + JWT), хранение истории чатов в Postgres и долгосрочную память пользователя с автоматической инъекцией в каждый запрос. Фронтенд — vanilla JS в index.html из ветки `route`. Ядро бэкенда (роутер, MWS proxy, research) не изменяется.

---

## Ограничения (железные)

- Роутер (`router_client.py`) не знает о памяти, auth, истории — не трогаем
- `MWSClient` — не трогаем
- Формат запросов к MWS API — идентичен текущему
- Фронтенд берётся из ветки `route` (файл `frontend/index.html`)
- Всё новое на фронтенде — добавляется в тот же `index.html`
- Никакой сборки, никаких npm, всё vanilla JS

---

## Поток данных (полный)

```
Login → Load History (sidebar) → Load Memory (top-10 facts)
  ↓
User types → doSend()
  → compose messages[]
  → prepend {role:system, content: memoryBlock} если есть факты
  → POST /v1/chat/completions {messages, system_prompt: memoryBlock, ...}
  ↓
Backend (proxy.py):
  → router.route(last_user_message)  ← без изменений
  → if system_prompt: prepend {role:system} to messages before forwarding
  → forward to MWS  ← без изменений
  → stream response to client
  → fire-and-forget: save message to DB, run memory extraction
  ↓
Frontend receives stream:
  → render tokens
  → save to currentMessages[]
  → POST /v1/memory/extract (fire-and-forget, не ждём)
  → setTimeout loadHistory (sidebar refresh)
```

---

## Бэкенд

### Новые таблицы (новый файл `app/db/models_auth.py` или расширение `models.py`)

```sql
-- Пользователи
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT now()
);

-- Чаты
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT DEFAULT 'Новый чат',
    created_at  TIMESTAMP DEFAULT now(),
    updated_at  TIMESTAMP DEFAULT now()
);

-- Сообщения
CREATE TABLE messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conv_id     UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,   -- user | assistant | system
    content     TEXT NOT NULL,
    model_used  TEXT,
    created_at  TIMESTAMP DEFAULT now()
);

-- Долгосрочная память
CREATE TABLE user_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    category    TEXT DEFAULT 'general',  -- preferences|projects|facts|links
    score       FLOAT DEFAULT 1.0,
    updated_at  TIMESTAMP DEFAULT now(),
    UNIQUE(user_id, key)
);
```

### Новые API роуты (новый файл `app/api/v1/auth_history.py`)

```
POST /v1/auth/register    { email, password } → { user_id, token }
POST /v1/auth/login       { email, password } → { user_id, token }
GET  /v1/auth/me          Bearer → { user_id, email }

GET  /v1/history/{user_id}                  → { conversations: [{id, title, updated_at}] }
GET  /v1/history/{user_id}/{conv_id}        → { messages: [{id, role, content, model_used, timestamp}] }
POST /v1/history/{user_id}/{conv_id}        { role, content, model_used } → { id }
DELETE /v1/history/{user_id}/{conv_id}      → 204

GET  /v1/memory/{user_id}                   → { memories: [{key, value, category, score}] }
POST /v1/memory/{user_id}                   { key, value, category } → { id }
DELETE /v1/memory/{user_id}/{key}           → 204
POST /v1/memory/extract                     { user_id, conv_id, assistant_message } → 202 Accepted
```

### Изменения в существующих файлах (минимальные)

**`app/models/mws.py`** — добавить поле:
```python
class ChatCompletionRequest(BaseModel):
    ...
    system_prompt: str | None = None          # новое поле — память
    conversation_id: str | None = None        # уже есть на фронтенде
```

**`app/api/v1/proxy.py`** — в `chat_completions()`:
```python
# Если есть system_prompt — prepend в messages
if request.system_prompt:
    from app.models.mws import Message
    sys_msg = Message(role="system", content=request.system_prompt)
    request = request.model_copy(
        update={"messages": [sys_msg] + list(request.messages)}
    )
# Далее — без изменений
```

**`app/api/router.py`** — включить новый роутер:
```python
from app.api.v1 import auth_history
api_router.include_router(auth_history.router, prefix="/v1", tags=["auth"])
```

**`app/db/database.py`** — `init_db()` уже вызывает `Base.metadata.create_all` — новые таблицы подтянутся автоматически.

**`app/config.py`** — добавить:
```python
SECRET_KEY: str = "change-me-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней
```

### Memory extraction logic

`POST /v1/memory/extract` запускает background task:
```
LLM prompt (llama-3.1-8b-instruct, max_tokens=200, temperature=0):
"Из следующего ответа ассистента извлеки факты о пользователе.
Верни JSON-массив [{key, value, category}] или [].
Категории: preferences, projects, facts, links.
Пример: [{key:'язык_программирования', value:'Python', category:'preferences'}]

Ответ ассистента: {message}"
```

Дедупликация: `INSERT ... ON CONFLICT (user_id, key) DO UPDATE SET value=..., updated_at=now()`.

---

## Фронтенд

### Что меняется в `index.html`

#### 1. Auth (заменить заглушку)

```javascript
// Текущий currentUserId = 'demo-user' → заменить на:
let currentUserId = null;
let authToken = localStorage.getItem('mts-token');

async function authLogin(email, password) { ... }
async function authRegister(email, password) { ... }
function authLogout() { localStorage.removeItem('mts-token'); location.reload(); }
```

Экран auth уже есть (authScreen div). Привязать кнопки к реальным API вызовам.

#### 2. История (заменить mock)

```javascript
// Текущий loadHistory() делает fetch но роут не существовал
// Теперь роут есть → работает без изменений кода фронтенда (если user_id правильный)
```

После каждого ответа: `POST /v1/history/{userId}/{convId}` с role+content+model_used.

#### 3. Память

```javascript
let userMemory = []; // [{key, value, category, score}]

async function loadMemory() {
    const r = await fetch(`${API}/memory/${currentUserId}`, { headers: authHeaders() });
    userMemory = (await r.json()).memories || [];
}

function buildMemoryBlock() {
    if (!userMemory.length) return null;
    const top = userMemory.slice(0, 10); // топ по score
    return "Факты о пользователе:\n" + top.map(m => `- ${m.key}: ${m.value}`).join('\n');
}

// В doSend() перед fetch:
const memBlock = buildMemoryBlock();
const body = {
    model: selectedModel,
    messages: [...currentMessages],
    stream: true,
    user: currentUserId,
    conversation_id: currentConvId,
    ...(memBlock && { system_prompt: memBlock })
};

// После ответа (fire-and-forget):
fetch(`${API}/memory/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user_id: currentUserId, conv_id: currentConvId, assistant_message: full })
}).catch(() => {});
```

---

## Точки расширения (безопасные)

| Что | Где | Как |
|-----|-----|-----|
| Auth middleware | `app/api/v1/auth_history.py` | Dependency `get_current_user` на защищённые роуты |
| Memory scoring | `user_memory.score` | Можно добавить decay по времени позже |
| Поиск по истории | `GET /history/{user_id}?q=` | ILIKE запрос по conversations.title |
| Memory → pgvector | Новая колонка `embedding vector(1536)` | Когда потребуется семантический поиск |

---

## Зависимости (новые)

```
python-jose[cryptography]   # JWT
passlib[bcrypt]             # password hashing
```

Добавить в `requirements.txt`.

---

## Out of Scope

- IndexedDB / offline mode (не нужен по решению)
- Refresh tokens (7-дневный access token достаточно)
- OAuth / SSO
- Memory decay / автоудаление старых фактов
- pgvector embeddings для памяти (JSONB достаточно)
- Изменения в роутере, MWSClient, research, voice, images

---

## Open Questions для имплементации

1. `conversation_id` уже передаётся фронтендом в теле запроса — proxy.py его получает но не сохраняет. Нужно сохранять сообщения там же где роутинг, или в отдельном middleware?
   → **Решение:** отдельный эндпоинт `/v1/history/{user_id}/{conv_id}` вызывается с фронтенда явно после получения ответа.

2. Заголовок чата (conversations.title) — откуда берётся?
   → **Решение:** первые 60 символов первого user-сообщения в чате.

3. `model_used` в messages — как узнать реальную модель при стриминге?
   → Фронтенд уже извлекает `json.model` из первого SSE-чанка (переменная `usedModelId`). Передавать при POST сохранения сообщения.
