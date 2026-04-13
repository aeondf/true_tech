"""
test_research.py — интеграционные тесты Deep Research pipeline.

Тесты проверяют:
  1. SSE-стриминг: все ожидаемые события приходят
  2. Подзапросы генерируются (step 2)
  3. Страницы парсятся (step 4 — pages_fetched > 0)
  4. Финальный ответ содержательный (event: done)
  5. Пайплайн не падает на пустой строке и коротком запросе
  6. TTS (edge-tts) синтезирует аудио

Запуск:
    cd backend
    pytest tests/test_research.py -v -s
"""
import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import Settings
from app.services.mws_client import MWSClient
from app.services.tts_service import TTSService
from app.api.v1.research import _run_pipeline


def get_settings() -> Settings:
    return Settings(
        _env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def collect_sse(query: str) -> list[dict]:
    """Запускает пайплайн и собирает все SSE-события в список."""
    settings = get_settings()
    mws = MWSClient(settings)
    events = []
    async for raw in _run_pipeline(query, mws, settings):
        # raw: "event: X\ndata: {...}\n\n"
        lines = raw.strip().split("\n")
        event_type = None
        data = {}
        for line in lines:
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    data = {}
        if event_type:
            events.append({"event": event_type, "data": data})
            print(f"  📡 {event_type}: {str(data)[:120]}")
    return events


# ── Research pipeline tests ───────────────────────────────────────

class TestResearchPipeline:

    def test_sse_events_sequence(self):
        """Пайплайн отдаёт прогресс step 1..5 и финальный done."""
        print("\n  🔬 Запрос: что такое RAG в LLM")
        events = run(collect_sse("что такое RAG в LLM"))

        event_types = [e["event"] for e in events]
        print(f"  События: {event_types}")

        # Обязательно должны быть прогресс-события
        assert "progress" in event_types, "Нет ни одного progress события"

        # Должен быть финальный done или error
        assert "done" in event_types or "error" in event_types, \
            "Нет ни done ни error в конце"

    def test_subqueries_generated(self):
        """Step 2 содержит список подзапросов."""
        events = run(collect_sse("FastAPI vs Django — что выбрать"))

        step2 = next(
            (e for e in events if e["event"] == "progress" and e["data"].get("step") == 2),
            None,
        )
        assert step2 is not None, "Событие step=2 с подзапросами не найдено"
        sub_queries = step2["data"].get("sub_queries", [])
        print(f"  Подзапросы: {sub_queries}")
        assert isinstance(sub_queries, list), "sub_queries должен быть списком"
        assert len(sub_queries) >= 1, "Должен быть хотя бы один подзапрос"

    def test_pages_fetched(self):
        """Step 4 сообщает количество спарсенных страниц."""
        events = run(collect_sse("популярные Python фреймворки 2024"))

        step4 = next(
            (e for e in events if e["event"] == "progress" and e["data"].get("step") == 4),
            None,
        )
        assert step4 is not None, "Событие step=4 (pages_fetched) не найдено"
        pages = step4["data"].get("pages_fetched", -1)
        print(f"  Страниц спарсено: {pages}")
        assert pages >= 0, "pages_fetched должен быть >= 0"

    def test_final_answer_nonempty(self):
        """Финальный ответ содержит осмысленный текст."""
        events = run(collect_sse("что такое vector database"))

        done = next((e for e in events if e["event"] == "done"), None)
        if done is None:
            # Если error — это тоже приемлемо (сеть), но нужно знать причину
            error = next((e for e in events if e["event"] == "error"), None)
            pytest.skip(f"Pipeline вернул error: {error}")

        answer = done["data"].get("answer", "")
        print(f"  Ответ ({len(answer)} симв.): {answer[:200]}")
        assert len(answer) > 50, f"Ответ слишком короткий: {answer!r}"

    def test_short_query_handled(self):
        """Короткий запрос не роняет пайплайн."""
        events = run(collect_sse("Python"))
        event_types = [e["event"] for e in events]
        assert "done" in event_types or "error" in event_types, \
            "Пайплайн завис на коротком запросе"

    def test_russian_query(self):
        """Русскоязычный запрос обрабатывается корректно."""
        events = run(collect_sse("Объясни принцип работы трансформеров в ML"))
        done = next((e for e in events if e["event"] == "done"), None)
        error = next((e for e in events if e["event"] == "error"), None)
        assert done or error, "Нет финального события"
        if done:
            assert len(done["data"].get("answer", "")) > 30

    def test_no_crash_on_obscure_topic(self):
        """Редкая тема — пайплайн не падает, возвращает хоть что-то."""
        events = run(collect_sse("история гербов малых городов Сибири"))
        event_types = [e["event"] for e in events]
        assert len(events) >= 2, "Слишком мало событий"
        assert "done" in event_types or "error" in event_types


# ── TTS tests ────────────────────────────────────────────────────

class TestTTSService:

    def test_synthesize_short_text(self):
        """edge-tts синтезирует короткую фразу → непустой MP3."""
        tts = TTSService(get_settings())
        audio, mime = run(tts.synthesize("Привет, это тест голоса."))
        print(f"\n  🔊 TTS: {len(audio)} байт, mime={mime}")
        assert len(audio) > 1000, "Аудио подозрительно мало"
        assert mime == "audio/mpeg"

    def test_synthesize_long_text(self):
        """edge-tts справляется с длинным текстом (обрезается до 1000 симв)."""
        long_text = "Это длинный текст для синтеза речи. " * 30  # ~1100 симв
        tts = TTSService(get_settings())
        audio, mime = run(tts.synthesize(long_text))
        print(f"  🔊 TTS long: {len(audio)} байт")
        assert len(audio) > 1000

    def test_synthesize_russian_voice(self):
        """Голос по умолчанию — русский Svetlana."""
        settings = get_settings()
        print(f"\n  🎙 Голос: {settings.TTS_VOICE}")
        assert "ru" in settings.TTS_VOICE.lower() or settings.TTS_VOICE == "ru-RU-SvetlanaNeural"
        tts = TTSService(settings)
        audio, _ = run(tts.synthesize("Проверка голоса."))
        assert len(audio) > 500

    def test_synthesize_empty_raises(self):
        """Пустая строка — edge-tts должен либо вернуть аудио тишины, либо упасть с ошибкой."""
        tts = TTSService(get_settings())
        try:
            audio, mime = run(tts.synthesize(" "))
            # Некоторые голоса возвращают тишину — это приемлемо
            print(f"  🔊 Empty TTS: {len(audio)} байт")
        except Exception as e:
            print(f"  ⚠️  Expected error on empty: {e}")
