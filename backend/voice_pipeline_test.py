#!/usr/bin/env python3
"""
voice_pipeline_test.py — интерактивный тест голосового пайплайна с памятью.

Полный пайплайн каждого хода:
  1. Роутер — определяет задачу и модель
  2. Модель — отвечает (с инжектированной памятью из прошлых ходов)
  3. TTS   — синтезирует ответ в MP3 и сохраняет файл
  4. Память — LLM извлекает факты, сохраняет для следующего хода

Запуск:
    cd backend
    python voice_pipeline_test.py
    python voice_pipeline_test.py "расскажи про Python"   # одиночный запрос
"""
import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from app.config import Settings
from app.services.router_client import RouterClient
from app.services.mws_client import MWSClient
from app.services.tts_service import TTSService
from app.models.mws import ChatCompletionRequest, Message

# ── Инициализация ─────────────────────────────────────────────────

settings = Settings(_env_file=os.path.join(os.path.dirname(__file__), ".env"))
router_svc = RouterClient(settings)
mws        = MWSClient(settings)
tts        = TTSService(settings)

# ── ANSI цвета ────────────────────────────────────────────────────

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[36m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
WHITE   = "\033[37m"

def sep(char="─", width=70, color=DIM):
    print(f"{color}{char * width}{RESET}")

def header(text: str):
    sep("═", color=CYAN)
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    sep("═", color=CYAN)


# ── Шаг 1: Роутинг ───────────────────────────────────────────────

async def step_route(message: str) -> tuple[str, str, int]:
    print(f"\n{BOLD}{BLUE}▶ ШАГ 1 — РОУТИНГ{RESET}")
    sep()

    t0 = time.time()
    route = await router_svc.route(message=message, attachments=[])
    latency = time.time() - t0

    pass_labels = {1: "MIME/расширение", 2: "regex-анализ", 3: "LLM llama-3.1-8b"}
    pass_colors = {1: GREEN, 2: YELLOW, 3: MAGENTA}
    pc = pass_colors.get(route.which_pass, RESET)

    print(f"  {DIM}Проход:{RESET}     {pc}{BOLD}Pass {route.which_pass}{RESET} — {pass_labels.get(route.which_pass, '?')}")
    print(f"  {DIM}Task type:{RESET}  {BOLD}{route.task_type}{RESET}")
    print(f"  {DIM}Модель:{RESET}     {BOLD}{route.model_id}{RESET}")
    print(f"  {DIM}Confidence:{RESET} {route.confidence:.2f}   {DIM}Latency:{RESET} {latency*1000:.0f}ms")
    sep()

    return route.task_type, route.model_id, route.which_pass


# ── Шаг 2: Модель ────────────────────────────────────────────────

async def step_model(
    history: list[dict],
    model_id: str,
    memory_block: str | None,
) -> str:
    print(f"\n{BOLD}{BLUE}▶ ШАГ 2 — ЗАПРОС К МОДЕЛИ{RESET}")
    sep()

    msg_objs = []
    if memory_block:
        msg_objs.append(Message(role="system", content=memory_block))
        print(f"  {MAGENTA}💾 Память инжектирована ({len(memory_block)} симв.){RESET}")

    # Добавляем системный промпт для голосового режима (краткие ответы)
    voice_system = "Отвечай кратко, не более 3–4 предложений. Ответ будет зачитан вслух."
    if memory_block:
        msg_objs[0] = Message(role="system", content=msg_objs[0].content + "\n\n" + voice_system)
    else:
        msg_objs.append(Message(role="system", content=voice_system))

    for m in history:
        msg_objs.append(Message(role=m["role"], content=m["content"]))

    print(f"  {DIM}Модель:{RESET}   {BOLD}{model_id}{RESET}")
    print(f"  {DIM}История:{RESET}  {len(history)} сообщений")
    sep()

    request = ChatCompletionRequest(
        model=model_id,
        messages=msg_objs,
        temperature=0.4,
        max_tokens=300,   # ограничено для TTS — длинный текст = долгий синтез
        stream=False,
    )

    t0 = time.time()
    raw = await mws.chat(request)
    latency = time.time() - t0

    choice = (raw.get("choices") or [{}])[0]
    msg    = choice.get("message", {}) or {}
    answer = msg.get("content") or msg.get("reasoning_content") or ""
    usage  = raw.get("usage", {})

    print(f"  {DIM}Latency:{RESET}   {latency:.2f}s")
    print(f"  {DIM}Токены:{RESET}    prompt={usage.get('prompt_tokens','?')}  completion={usage.get('completion_tokens','?')}")
    sep()

    return answer.strip()


# ── Шаг 3: TTS ───────────────────────────────────────────────────

async def step_tts(text: str, turn: int) -> str | None:
    """Синтезирует ответ в MP3, сохраняет файл. Возвращает путь или None."""
    print(f"\n{BOLD}{BLUE}▶ ШАГ 3 — TTS (edge-tts){RESET}")
    sep()

    print(f"  {DIM}Голос:{RESET}   {settings.TTS_VOICE}")
    print(f"  {DIM}Текст:{RESET}   {text[:80]}{'...' if len(text) > 80 else ''}")

    t0 = time.time()
    try:
        audio_bytes, mime = await tts.synthesize(text)
        latency = time.time() - t0

        out_path = os.path.join(os.path.dirname(__file__), f"tts_turn_{turn}.mp3")
        with open(out_path, "wb") as f:
            f.write(audio_bytes)

        print(f"  {GREEN}✓ Синтез:{RESET}  {len(audio_bytes):,} байт  {DIM}({latency:.1f}s){RESET}")
        print(f"  {GREEN}✓ Файл:{RESET}    {out_path}")
        sep()
        return out_path

    except Exception as e:
        latency = time.time() - t0
        print(f"  {RED}✗ Ошибка TTS:{RESET} {e}  {DIM}({latency:.1f}s){RESET}")
        sep()
        return None


# ── Шаг 4: Извлечение фактов ─────────────────────────────────────

async def step_extract(user_message: str, assistant_answer: str) -> list[dict]:
    print(f"\n{BOLD}{BLUE}▶ ШАГ 4 — ИЗВЛЕЧЕНИЕ ФАКТОВ{RESET}")
    sep()

    combined = f"Пользователь: {user_message}\nАссистент: {assistant_answer}"
    if len(combined) < 20:
        print(f"  {DIM}Слишком короткий текст, пропускаем{RESET}")
        sep()
        return []

    system = (
        "Ты система извлечения фактов. Проанализируй диалог и найди факты о пользователе. "
        "Верни ТОЛЬКО JSON-массив [{\"key\": str, \"value\": str, \"category\": str}] или []. "
        "Категории: preferences, projects, facts, links."
    )

    t0 = time.time()
    raw = await mws.chat_simple(
        model="llama-3.1-8b-instruct",
        system=system,
        user=f"Диалог:\n{combined[:2000]}",
    )
    latency = time.time() - t0

    m = re.search(r"\[.*?\]", raw, re.DOTALL)
    facts = []
    if m:
        try:
            parsed = json.loads(m.group())
            if isinstance(parsed, list):
                facts = [f for f in parsed if isinstance(f, dict) and f.get("key") and f.get("value")]
        except json.JSONDecodeError:
            pass

    print(f"  {DIM}Экстрактор:{RESET} llama-3.1-8b-instruct  {DIM}({latency:.1f}s){RESET}")
    if facts:
        print(f"  {GREEN}Найдено: {len(facts)} фактов{RESET}")
        for f in facts:
            cat_col = CYAN if f.get("category") == "preferences" else (YELLOW if f.get("category") == "projects" else WHITE)
            print(f"    {cat_col}▸ {f['key']}{RESET}: {f['value']}  {DIM}[{f.get('category','?')}]{RESET}")
    else:
        print(f"  {DIM}Фактов не найдено{RESET}")
    sep()
    return facts


# ── Шаг 5: Обновление памяти ─────────────────────────────────────

def step_memory(memory: dict, new_facts: list[dict]) -> dict:
    print(f"\n{BOLD}{BLUE}▶ ШАГ 5 — ПАМЯТЬ{RESET}")
    sep()

    added = updated = 0
    for fact in new_facts:
        key = fact.get("key", "").strip()
        value = fact.get("value", "").strip()
        category = fact.get("category", "general").strip()
        if not key or not value:
            continue
        if key in memory and memory[key]["value"] != value:
            memory[key] = {"value": value, "category": category}
            updated += 1
        elif key not in memory:
            memory[key] = {"value": value, "category": category}
            added += 1

    if added or updated:
        print(f"  {GREEN}+{added} новых  ~{updated} обновлённых{RESET}")
    else:
        print(f"  {DIM}Без изменений{RESET}")

    if memory:
        print(f"\n  {BOLD}Память ({len(memory)} фактов):{RESET}")
        for key, v in memory.items():
            cat_col = CYAN if v["category"] == "preferences" else (YELLOW if v["category"] == "projects" else WHITE)
            print(f"    {cat_col}▸ {key}{RESET}: {v['value']}  {DIM}[{v['category']}]{RESET}")
    else:
        print(f"  {DIM}Память пуста{RESET}")
    sep()
    return memory


def build_memory_block(memory: dict) -> str | None:
    if not memory:
        return None
    lines = ["Факты о пользователе:"]
    lines += [f"- {k}: {v['value']}" for k, v in memory.items()]
    return "\n".join(lines)


# ── Главный пайплайн одного хода ─────────────────────────────────

async def run_turn(
    user_message: str,
    history: list[dict],
    memory: dict,
    turn: int,
) -> tuple[str, dict]:
    sep("═", color=BOLD + CYAN)
    print(f"{BOLD}{CYAN}  ХОД {turn}  •  {time.strftime('%H:%M:%S')}{RESET}")
    sep("═", color=BOLD + CYAN)

    task_type, model_id, _ = await step_route(user_message)
    memory_block = build_memory_block(memory)
    answer = await step_model(history, model_id, memory_block)

    # Вывод ответа
    print(f"\n{BOLD}{GREEN}  Ответ модели:{RESET}")
    sep(color=GREEN)
    for line in answer.splitlines()[:30]:
        print(f"  {line}")
    sep(color=GREEN)

    await step_tts(answer, turn)
    facts = await step_extract(user_message, answer)
    memory = step_memory(memory, facts)

    return answer, memory


# ── Одиночный запрос ─────────────────────────────────────────────

async def run_once(message: str):
    header(f"VOICE PIPELINE TEST  •  {time.strftime('%H:%M:%S')}")
    print(f"  {BOLD}Запрос:{RESET} {message[:200]}")
    sep("═", color=CYAN)
    await run_turn(message, [{"role": "user", "content": message}], {}, 1)
    print(f"\n{DIM}  Готово. Файл tts_turn_1.mp3 сохранён.{RESET}\n")


# ── Интерактивный режим ───────────────────────────────────────────

async def interactive():
    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   Voice Pipeline — Роутер → Модель → TTS → Память      ║{RESET}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════╝{RESET}")
    print(f"  {DIM}Каждый ход: роутер → модель → TTS (MP3) → факты → память{RESET}")
    print(f"  {DIM}MP3 файлы сохраняются как tts_turn_N.mp3 рядом со скриптом{RESET}")
    print(f"  {DIM}Команды: 'memory' — память, 'reset' — сброс, 'exit' — выход{RESET}\n")

    history: list[dict] = []
    memory: dict = {}
    turn = 0

    while True:
        try:
            user_input = input(f"\n{BOLD}{GREEN}Вы:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Выход.{RESET}")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q", "выход"}:
            print(f"{DIM}Выход.{RESET}")
            break
        if user_input.lower() in {"memory", "mem", "память"}:
            if memory:
                print(f"\n{BOLD}Память ({len(memory)} фактов):{RESET}")
                for k, v in memory.items():
                    print(f"  {CYAN}▸ {k}{RESET}: {v['value']}  {DIM}[{v['category']}]{RESET}")
            else:
                print(f"  {DIM}Память пуста{RESET}")
            continue
        if user_input.lower() in {"reset", "сброс"}:
            history.clear(); memory.clear(); turn = 0
            print(f"  {YELLOW}История и память сброшены.{RESET}")
            continue

        turn += 1
        history.append({"role": "user", "content": user_input})

        try:
            answer, memory = await run_turn(user_input, history, memory, turn)
            history.append({"role": "assistant", "content": answer})
        except Exception as e:
            print(f"\n  {RED}Ошибка: {e}{RESET}")
            history.pop()
            turn -= 1

    print(f"\n{DIM}Диалог завершён. Ходов: {turn}  Фактов: {len(memory)}{RESET}\n")


# ── Точка входа ───────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(run_once(" ".join(sys.argv[1:])))
    else:
        asyncio.run(interactive())
