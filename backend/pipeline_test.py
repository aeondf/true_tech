#!/usr/bin/env python3
"""
pipeline_test.py — интерактивный тест полного пайплайна: роутер → модель → ответ.

Запуск:
    cd backend
    python pipeline_test.py
    python pipeline_test.py "напиши функцию сортировки"   # одиночный промпт
"""
import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Настройки ─────────────────────────────────────────────────────

BASE_URL = os.getenv("MWS_BASE_URL", "https://api.gpt.mws.ru")
API_KEY  = os.getenv("MWS_API_KEY", "")

if not API_KEY:
    print("❌ MWS_API_KEY не найден в .env")
    sys.exit(1)

# ── Импорт роутера ────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(__file__))
from app.config import Settings
from app.services.router_client import RouterClient, RouteResult, TASK_MODELS

settings = Settings()
router   = RouterClient(settings)

# ── Цвета ANSI ────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"

def sep(char="─", width=70, color=DIM):
    print(f"{color}{char * width}{RESET}")

def header(text: str):
    sep("═")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    sep("═")


# ── Шаг 1: роутинг ────────────────────────────────────────────────

async def step_route(message: str, attachments: list[dict]) -> RouteResult:
    print(f"\n{BOLD}{BLUE}▶ ШАГ 1 — РОУТИНГ{RESET}")
    sep()

    print(f"  {DIM}Сообщение:{RESET} {message[:120]}")
    if attachments:
        for a in attachments:
            print(f"  {DIM}Attachment:{RESET} name={a.get('name')} mime={a.get('mime')}")

    t0 = time.time()
    route = await router.route(message=message, attachments=attachments)
    latency = time.time() - t0

    pass_labels = {1: "MIME/расширение", 2: "regex-анализ", 3: "LLM llama-3.1-8b"}
    pass_colors = {1: GREEN, 2: YELLOW, 3: MAGENTA}
    pc = pass_colors.get(route.which_pass, RESET)

    print()
    print(f"  {DIM}Проход:{RESET}      {pc}{BOLD}Pass {route.which_pass}{RESET} — {pass_labels.get(route.which_pass, '?')}")
    print(f"  {DIM}Task type:{RESET}   {BOLD}{route.task_type}{RESET}")
    print(f"  {DIM}Модель:{RESET}      {BOLD}{route.model_id}{RESET}")
    print(f"  {DIM}Confidence:{RESET}  {route.confidence:.2f}")
    print(f"  {DIM}Latency:{RESET}     {latency*1000:.0f}ms")

    sep()
    return route


# ── Шаг 2: вызов MWS ──────────────────────────────────────────────

async def step_mws(message: str, model_id: str, task_type: str) -> str:
    import httpx

    print(f"\n{BOLD}{BLUE}▶ ШАГ 2 — ЗАПРОС К MWS API{RESET}")
    sep()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    if task_type == "image_gen":
        endpoint = "/v1/images/generations"
        payload  = {"model": model_id, "prompt": message, "size": "512x512"}
    else:
        endpoint = "/v1/chat/completions"
        payload  = {
            "model": model_id,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 512,
            "temperature": 0.7,
        }

    url = f"{BASE_URL}{endpoint}"
    print(f"  {DIM}URL:{RESET}      {url}")
    print(f"  {DIM}Model:{RESET}    {model_id}")
    print(f"  {DIM}Payload:{RESET}  {json.dumps(payload, ensure_ascii=False)[:200]}…")
    sep()

    t0 = time.time()
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(url, headers=headers, json=payload)
    latency = time.time() - t0

    status_color = GREEN if r.status_code == 200 else RED
    print(f"  {DIM}Status:{RESET}   {status_color}{BOLD}{r.status_code}{RESET}")
    print(f"  {DIM}Latency:{RESET}  {latency:.2f}s")
    print(f"  {DIM}Content-type:{RESET} {r.headers.get('content-type','?')}")

    if r.status_code != 200:
        print(f"\n  {RED}ERROR:{RESET} {r.text[:500]}")
        sep()
        return ""

    data = r.json()

    # ── Разбираем ответ ───────────────────────────────────────────
    if task_type == "image_gen":
        items   = data.get("data", [])
        img_url = items[0].get("url", "") if items else ""
        print(f"  {DIM}Images:{RESET}   {len(items)}")
        print(f"  {DIM}URL:{RESET}      {img_url[:100]}")
        sep()
        return img_url

    choice   = (data.get("choices") or [{}])[0]
    message_ = choice.get("message", {}) or {}
    content  = message_.get("content") or ""
    thinking = message_.get("reasoning_content") or ""
    finish   = choice.get("finish_reason", "?")
    usage    = data.get("usage", {})

    print(f"  {DIM}Finish:{RESET}   {finish}")
    print(f"  {DIM}Tokens:{RESET}   prompt={usage.get('prompt_tokens','?')}  "
          f"completion={usage.get('completion_tokens','?')}  "
          f"total={usage.get('total_tokens','?')}")
    sep()

    return thinking or content


# ── Шаг 3: вывод результата ────────────────────────────────────────

def step_result(result: str, task_type: str):
    print(f"\n{BOLD}{BLUE}▶ ШАГ 3 — РЕЗУЛЬТАТ{RESET}")
    sep()

    if task_type == "image_gen":
        print(f"  {GREEN}Изображение сгенерировано:{RESET}")
        print(f"  {result}")
    elif task_type == "deep_research":
        print(f"  {YELLOW}⚠  task_type=deep_research{RESET}")
        print(f"  Для полного pipeline используй эндпоинт /v1/research")
        print(f"  Ответ через обычный chat:\n")
        _print_answer(result)
    else:
        _print_answer(result)

    sep("═")


def _print_answer(text: str):
    if not text:
        print(f"  {RED}(пустой ответ){RESET}")
        return
    lines = text.splitlines()
    for line in lines[:60]:
        print(f"  {line}")
    if len(lines) > 60:
        print(f"  {DIM}… ещё {len(lines)-60} строк{RESET}")


# ── Главный пайплайн ──────────────────────────────────────────────

async def run_pipeline(message: str, attachments: list[dict] | None = None):
    attachments = attachments or []

    header(f"PIPELINE TEST  •  {time.strftime('%H:%M:%S')}")
    print(f"  {BOLD}Промпт:{RESET} {message[:200]}")
    sep("═")

    # Шаг 1: роутинг
    route = await step_route(message, attachments)

    # Шаг 2: MWS
    result = await step_mws(message, route.model_id, route.task_type)

    # Шаг 3: результат
    step_result(result, route.task_type)

    print(f"\n{DIM}  Всё готово. task_type={route.task_type}  model={route.model_id}  pass={route.which_pass}{RESET}\n")


# ── Интерактивный режим ───────────────────────────────────────────

async def interactive():
    print(f"\n{BOLD}{CYAN}  MWS Pipeline Tester{RESET}")
    print(f"  {DIM}Введите промпт → роутер определит задачу → запрос к модели{RESET}")
    print(f"  {DIM}Выход: Ctrl+C или 'exit'{RESET}\n")

    while True:
        try:
            prompt = input(f"{BOLD}{GREEN}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Выход.{RESET}")
            break

        if not prompt or prompt.lower() in {"exit", "quit", "q"}:
            print(f"{DIM}Выход.{RESET}")
            break

        await run_pipeline(prompt)


# ── Точка входа ───────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Промпт передан аргументом
        prompt = " ".join(sys.argv[1:])
        asyncio.run(run_pipeline(prompt))
    else:
        # Интерактивный режим
        asyncio.run(interactive())
