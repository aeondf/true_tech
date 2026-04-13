#!/usr/bin/env python3
"""
research_pipeline_test.py — интерактивный тест Deep Research пайплайна.

Пайплайн:
  1. Генерация 5 подзапросов (LLM)
  2. Параллельный поиск (DuckDuckGo) + парсинг страниц
  3. Синтез финального ответа с источниками

Показывает каждый шаг в реальном времени через SSE-стриминг.

Запуск:
    cd backend
    python research_pipeline_test.py
    python research_pipeline_test.py "что такое RAG в LLM"   # одиночный запрос
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from app.config import Settings
from app.services.mws_client import MWSClient
from app.api.v1.research import _run_pipeline

# ── Инициализация ─────────────────────────────────────────────────

settings = Settings(_env_file=os.path.join(os.path.dirname(__file__), ".env"))
mws      = MWSClient(settings)

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

def sep(char="─", width=70, color=DIM):
    print(f"{color}{char * width}{RESET}")

def header(text: str):
    sep("═", color=CYAN)
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    sep("═", color=CYAN)


# ── SSE-парсер ───────────────────────────────────────────────────

def _parse_sse(raw: str) -> tuple[str, dict]:
    """Разбирает одно SSE-сообщение → (event_type, data)."""
    event_type = "unknown"
    data = {}
    for line in raw.strip().splitlines():
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                pass
    return event_type, data


# ── Отображение событий ──────────────────────────────────────────

STEP_LABELS = {
    1: ("Генерация подзапросов",  BLUE),
    2: ("Подзапросы готовы",      GREEN),
    3: ("Поиск и парсинг",        YELLOW),
    4: ("Страницы получены",      GREEN),
    5: ("Синтез ответа",          MAGENTA),
}


def show_event(event_type: str, data: dict, t_start: float):
    elapsed = time.time() - t_start

    if event_type == "progress":
        step = data.get("step", "?")
        label, color = STEP_LABELS.get(step, (f"Step {step}", DIM))

        print(f"\n{BOLD}{color}▶ ШАГ {step} — {label}{RESET}  {DIM}+{elapsed:.1f}s{RESET}")
        sep()

        if step == 2:
            sub_queries = data.get("sub_queries", [])
            print(f"  {DIM}Подзапросов:{RESET} {len(sub_queries)}")
            for i, q in enumerate(sub_queries, 1):
                print(f"  {CYAN}{i}.{RESET} {q}")

        elif step == 4:
            pages = data.get("pages_fetched", 0)
            color_pages = GREEN if pages > 0 else YELLOW
            print(f"  {DIM}Спарсено страниц:{RESET} {color_pages}{BOLD}{pages}{RESET}")

        elif "message" in data:
            print(f"  {DIM}{data['message']}{RESET}")

        sep()

    elif event_type == "done":
        answer = data.get("answer", "")
        print(f"\n{BOLD}{GREEN}▶ РЕЗУЛЬТАТ  {DIM}+{elapsed:.1f}s{RESET}")
        sep("═", color=GREEN)
        lines = answer.splitlines()
        for line in lines[:80]:
            print(f"  {line}")
        if len(lines) > 80:
            print(f"  {DIM}… ещё {len(lines) - 80} строк{RESET}")
        sep("═", color=GREEN)

    elif event_type == "error":
        msg = data.get("message", "неизвестная ошибка")
        print(f"\n  {RED}✗ ОШИБКА:{RESET} {msg}  {DIM}+{elapsed:.1f}s{RESET}")


# ── Главный пайплайн ─────────────────────────────────────────────

async def run_research(query: str):
    header(f"DEEP RESEARCH  •  {time.strftime('%H:%M:%S')}")
    print(f"  {BOLD}Запрос:{RESET} {query[:200]}")
    sep("═", color=CYAN)

    t_start = time.time()
    final_answer = ""
    events_seen = []

    async for raw in _run_pipeline(query, mws, settings):
        event_type, data = _parse_sse(raw)
        events_seen.append(event_type)
        show_event(event_type, data, t_start)
        if event_type == "done":
            final_answer = data.get("answer", "")

    total = time.time() - t_start
    print(f"\n{DIM}  Готово за {total:.1f}s  •  события: {events_seen}{RESET}\n")
    return final_answer


# ── Интерактивный режим ───────────────────────────────────────────

async def interactive():
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   Deep Research Pipeline Tester                           ║{RESET}")
    print(f"{BOLD}{CYAN}║   Подзапросы → Поиск + Парсинг → Синтез ответа            ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print(f"  {DIM}Введите тему для исследования. Выход: 'exit'{RESET}\n")

    while True:
        try:
            query = input(f"{BOLD}{GREEN}Research:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Выход.{RESET}")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q", "выход"}:
            print(f"{DIM}Выход.{RESET}")
            break

        try:
            await run_research(query)
        except Exception as e:
            print(f"\n  {RED}Критическая ошибка: {e}{RESET}\n")


# ── Точка входа ───────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(run_research(" ".join(sys.argv[1:])))
    else:
        asyncio.run(interactive())
