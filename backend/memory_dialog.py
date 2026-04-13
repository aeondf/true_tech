#!/usr/bin/env python3
"""
memory_dialog.py — интерактивный диалог с полным пайплайном: роутер → модель → память.

Каждый ход:
  1. Роутер определяет задачу и модель
  2. Модель отвечает (с инжектированной памятью из прошлых ходов)
  3. LLM извлекает факты из ответа
  4. Факты сохраняются в памяти и будут инжектированы в следующий запрос

Запуск:
    cd backend
    python memory_dialog.py
"""
import asyncio
import json
import os
import re
import sys
import time

# ── Загрузка .env ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__))

from app.config import Settings
from app.services.router_client import RouterClient
from app.services.mws_client import MWSClient
from app.models.mws import ChatCompletionRequest, Message

# ── Инициализация ─────────────────────────────────────────────────

settings = Settings(_env_file=os.path.join(os.path.dirname(__file__), ".env"))
router   = RouterClient(settings)
mws      = MWSClient(settings)

# ── Цвета ANSI ────────────────────────────────────────────────────

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
    """Возвращает (task_type, model_id, which_pass)."""
    print(f"\n{BOLD}{BLUE}▶ ШАГ 1 — РОУТИНГ{RESET}")
    sep()

    t0 = time.time()
    route = await router.route(message=message, attachments=[])
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


# ── Шаг 2: Запрос к модели ───────────────────────────────────────

async def step_model(
    history: list[dict],
    model_id: str,
    memory_block: str | None,
) -> str:
    """Отправляет историю в модель, возвращает ответ."""
    print(f"\n{BOLD}{BLUE}▶ ШАГ 2 — ЗАПРОС К МОДЕЛИ{RESET}")
    sep()

    msg_objs = []
    if memory_block:
        msg_objs.append(Message(role="system", content=memory_block))
        print(f"  {MAGENTA}💾 Инжектирована память ({len(memory_block)} символов){RESET}")

    for m in history:
        msg_objs.append(Message(role=m["role"], content=m["content"]))

    print(f"  {DIM}Модель:{RESET}   {BOLD}{model_id}{RESET}")
    print(f"  {DIM}История:{RESET}  {len(history)} сообщений")
    sep()

    request = ChatCompletionRequest(
        model=model_id,
        messages=msg_objs,
        temperature=0.4,
        max_tokens=512,
        stream=False,
    )

    t0 = time.time()
    raw = await mws.chat(request)
    latency = time.time() - t0

    choice = (raw.get("choices") or [{}])[0]
    msg    = choice.get("message", {}) or {}
    answer = msg.get("content") or msg.get("reasoning_content") or ""
    usage  = raw.get("usage", {})

    print(f"  {DIM}Статус:{RESET}   {GREEN}200 OK{RESET}   {DIM}Latency:{RESET} {latency:.2f}s")
    print(f"  {DIM}Токены:{RESET}   prompt={usage.get('prompt_tokens','?')}  "
          f"completion={usage.get('completion_tokens','?')}")
    sep()

    return answer.strip()


# ── Шаг 3: Извлечение фактов ─────────────────────────────────────

async def step_extract(user_message: str, assistant_answer: str) -> list[dict]:
    """LLM ищет факты о пользователе в диалоге."""
    print(f"\n{BOLD}{BLUE}▶ ШАГ 3 — ИЗВЛЕЧЕНИЕ ФАКТОВ{RESET}")
    sep()

    combined = f"Пользователь: {user_message}\nАссистент: {assistant_answer}"
    if len(combined) < 20:
        print(f"  {DIM}Слишком короткий текст, пропускаем{RESET}")
        sep()
        return []

    system = (
        "Ты система извлечения фактов. Проанализируй диалог и найди факты о пользователе. "
        "Верни ТОЛЬКО JSON-массив [{\"key\": str, \"value\": str, \"category\": str}] или []. "
        "Категории: preferences, projects, facts, links. "
        "Примеры: имя, язык программирования, текущий проект, любимый фреймворк. "
        "Если фактов нет — верни []."
    )

    print(f"  {DIM}Экстрактор:{RESET} llama-3.1-8b-instruct")

    t0 = time.time()
    raw_facts = await mws.chat_simple(
        model="llama-3.1-8b-instruct",
        system=system,
        user=f"Диалог:\n{combined[:2000]}",
    )
    latency = time.time() - t0

    m = re.search(r"\[.*?\]", raw_facts, re.DOTALL)
    facts = []
    if m:
        try:
            parsed = json.loads(m.group())
            if isinstance(parsed, list):
                facts = [f for f in parsed if isinstance(f, dict) and f.get("key") and f.get("value")]
        except json.JSONDecodeError:
            pass

    print(f"  {DIM}Latency:{RESET}    {latency:.2f}s")
    if facts:
        print(f"  {GREEN}Найдено фактов: {len(facts)}{RESET}")
        for f in facts:
            cat_color = CYAN if f.get("category") == "preferences" else (
                YELLOW if f.get("category") == "projects" else WHITE
            )
            print(f"    {cat_color}▸ {f['key']}{RESET}: {f['value']}  {DIM}[{f.get('category','?')}]{RESET}")
    else:
        print(f"  {DIM}Фактов не найдено{RESET}")

    sep()
    return facts


# ── Шаг 4: Обновление памяти ─────────────────────────────────────

def step_memory_update(memory: dict[str, dict], new_facts: list[dict]) -> dict[str, dict]:
    """Обновляет in-memory хранилище фактов."""
    print(f"\n{BOLD}{BLUE}▶ ШАГ 4 — ПАМЯТЬ{RESET}")
    sep()

    updated = 0
    added = 0
    for fact in new_facts:
        key = fact.get("key", "").strip()
        value = fact.get("value", "").strip()
        category = fact.get("category", "general").strip()
        if not key or not value:
            continue
        if key in memory:
            if memory[key]["value"] != value:
                memory[key] = {"value": value, "category": category}
                updated += 1
        else:
            memory[key] = {"value": value, "category": category}
            added += 1

    if added or updated:
        print(f"  {GREEN}+{added} новых  ~{updated} обновлённых{RESET}")
    else:
        print(f"  {DIM}Изменений нет{RESET}")

    if memory:
        print(f"\n  {BOLD}Вся память ({len(memory)} фактов):{RESET}")
        for key, v in memory.items():
            cat_color = CYAN if v["category"] == "preferences" else (
                YELLOW if v["category"] == "projects" else WHITE
            )
            print(f"    {cat_color}▸ {key}{RESET}: {v['value']}  {DIM}[{v['category']}]{RESET}")
    else:
        print(f"  {DIM}Память пуста{RESET}")

    sep()
    return memory


def build_memory_block(memory: dict[str, dict]) -> str | None:
    """Формирует system block из накопленных фактов."""
    if not memory:
        return None
    lines = ["Факты о пользователе:"]
    for key, v in memory.items():
        lines.append(f"- {key}: {v['value']}")
    return "\n".join(lines)


# ── Главный пайплайн (один ход) ──────────────────────────────────

async def run_turn(
    user_message: str,
    history: list[dict],
    memory: dict[str, dict],
    turn_num: int,
) -> tuple[str, dict[str, dict]]:
    """Полный пайплайн одного хода. Возвращает (ответ, обновлённая память)."""

    sep("═", color=BOLD + CYAN)
    print(f"{BOLD}{CYAN}  ХОД {turn_num}  •  {time.strftime('%H:%M:%S')}{RESET}")
    sep("═", color=BOLD + CYAN)

    # Шаг 1: роутинг
    task_type, model_id, which_pass = await step_route(user_message)

    # Память для инжекции
    memory_block = build_memory_block(memory)

    # Шаг 2: запрос к модели
    answer = await step_model(history, model_id, memory_block)

    # Показываем ответ модели
    print(f"\n{BOLD}{GREEN}  Ответ модели:{RESET}")
    sep(color=GREEN)
    lines = answer.splitlines()
    for line in lines[:50]:
        print(f"  {line}")
    if len(lines) > 50:
        print(f"  {DIM}… ещё {len(lines)-50} строк{RESET}")
    sep(color=GREEN)

    # Шаг 3: извлечение фактов
    new_facts = await step_extract(user_message, answer)

    # Шаг 4: обновление памяти
    memory = step_memory_update(memory, new_facts)

    return answer, memory


# ── Интерактивный цикл ────────────────────────────────────────────

async def interactive():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   MWS Memory Dialog  —  Роутер → Модель → Память  ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════╝{RESET}")
    print(f"  {DIM}Каждый ход: роутер → модель → извлечение фактов → память{RESET}")
    print(f"  {DIM}Команды: 'memory' — показать память, 'reset' — сбросить, 'exit' — выход{RESET}\n")

    history: list[dict] = []       # история диалога
    memory: dict[str, dict] = {}   # накопленные факты
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
                print(f"\n{BOLD}Текущая память ({len(memory)} фактов):{RESET}")
                for key, v in memory.items():
                    print(f"  {CYAN}▸ {key}{RESET}: {v['value']}  {DIM}[{v['category']}]{RESET}")
            else:
                print(f"  {DIM}Память пуста{RESET}")
            continue

        if user_input.lower() in {"reset", "сброс"}:
            history.clear()
            memory.clear()
            turn = 0
            print(f"  {YELLOW}История и память сброшены.{RESET}")
            continue

        if user_input.lower() in {"history", "история"}:
            if history:
                print(f"\n{BOLD}История ({len(history)} сообщений):{RESET}")
                for m in history:
                    role_color = GREEN if m["role"] == "user" else BLUE
                    print(f"  {role_color}{m['role'].upper()}{RESET}: {m['content'][:100]}")
            else:
                print(f"  {DIM}История пуста{RESET}")
            continue

        turn += 1

        # Добавляем сообщение пользователя в историю
        history.append({"role": "user", "content": user_input})

        try:
            answer, memory = await run_turn(
                user_message=user_input,
                history=history,
                memory=memory,
                turn_num=turn,
            )
            # Добавляем ответ ассистента в историю
            history.append({"role": "assistant", "content": answer})

        except Exception as e:
            print(f"\n  {RED}Ошибка: {e}{RESET}")
            # Откатываем последнее сообщение пользователя
            history.pop()
            turn -= 1

    print(f"\n{DIM}Диалог завершён. Ходов: {turn}  Фактов в памяти: {len(memory)}{RESET}\n")


# ── Точка входа ───────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(interactive())
