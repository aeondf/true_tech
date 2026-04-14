"""Deterministic tests for the first two router passes."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import Settings
from app.services.router_client import RouteResult, RouterClient


def make_router() -> RouterClient:
    settings = Settings(MWS_API_KEY="test", MWS_BASE_URL="http://localhost")
    return RouterClient(settings)


def route_sync(message: str = "", attachments: list[dict] | None = None) -> RouteResult:
    router = make_router()
    attachments = attachments or []
    result = router._pass1(attachments)
    if result:
        return result
    result = router._pass2(message)
    if result:
        return result
    return RouteResult("text", "qwen2.5-72b-instruct", 0.5, 3)


class TestPass1Mime:
    def test_audio_mp3(self):
        r = route_sync(attachments=[{"name": "song.mp3", "mime": "audio/mpeg"}])
        assert r.task_type == "asr"
        assert r.which_pass == 1

    def test_audio_mime_only(self):
        r = route_sync(attachments=[{"name": "voice", "mime": "audio/flac"}])
        assert r.task_type == "asr"

    def test_image_png(self):
        r = route_sync(attachments=[{"name": "chart.png", "mime": "image/png"}])
        assert r.task_type == "vlm"
        assert r.which_pass == 1

    def test_image_mime_only(self):
        r = route_sync(attachments=[{"name": "image", "mime": "image/webp"}])
        assert r.task_type == "vlm"

    def test_pdf(self):
        r = route_sync(attachments=[{"name": "report.pdf", "mime": "application/pdf"}])
        assert r.task_type == "file_qa"
        assert r.which_pass == 1

    def test_docx(self):
        r = route_sync(attachments=[{"name": "notes.docx", "mime": ""}])
        assert r.task_type == "file_qa"

    def test_audio_overrides_message(self):
        r = route_sync(
            message="write a Python function",
            attachments=[{"name": "voice.wav", "mime": "audio/wav"}],
        )
        assert r.task_type == "asr"

    def test_image_overrides_research(self):
        r = route_sync(
            message="do deep research on battery technology",
            attachments=[{"name": "photo.jpg", "mime": "image/jpeg"}],
        )
        assert r.task_type == "vlm"


class TestPass2Structural:
    def test_research_explicit_phrase(self):
        r = route_sync("do deep research on climate change effects on agriculture")
        assert r.task_type == "deep_research"
        assert r.which_pass == 2

    def test_research_english_source_backed(self):
        r = route_sync("do research on the LLM tooling market with sources")
        assert r.task_type == "deep_research"

    def test_research_izuchi_temu(self):
        r = route_sync("изучи тему квантовых вычислений")
        assert r.task_type == "deep_research"

    def test_research_glubokiy_analiz(self):
        r = route_sync("глубокий анализ рынка электромобилей в 2025 году")
        assert r.task_type == "deep_research"

    def test_research_detalny_analiz(self):
        r = route_sync("детальный анализ конкурентов в нише SaaS")
        assert r.task_type == "deep_research"

    def test_research_with_sources_signal(self):
        r = route_sync("разбери рынок RAG со ссылками на источники")
        assert r.task_type == "deep_research"

    def test_text_rasskazhi_podrobno_stays_text(self):
        r = route_sync("расскажи подробно про историю Второй мировой войны")
        assert r.task_type == "text"

    def test_code_proanaliziruy_kod_stays_code(self):
        r = route_sync("проанализируй этот код на Python и найди баги")
        assert r.task_type == "code"

    def test_image_gen_ru(self):
        r = route_sync("нарисуй закат над морем в стиле импрессионизма")
        assert r.task_type == "image_gen"
        assert r.which_pass == 2

    def test_image_gen_en(self):
        r = route_sync("draw a futuristic city at night")
        assert r.task_type == "image_gen"

    def test_image_gen_generate(self):
        r = route_sync("generate image of a robot in the rain")
        assert r.task_type == "image_gen"

    def test_web_parse_ru(self):
        r = route_sync("открой https://habr.com/ru/articles/123 и перескажи")
        assert r.task_type == "web_parse"
        assert r.which_pass == 2

    def test_web_parse_en(self):
        r = route_sync("summarize https://arxiv.org/abs/2303.08774")
        assert r.task_type == "web_parse"

    def test_web_parse_analyze_link(self):
        r = route_sync("проанализируй ссылку https://openai.com/blog/gpt4")
        assert r.task_type == "web_parse"

    def test_web_search_with_url_ru(self):
        r = route_sync("найди информацию на https://google.com про Python")
        assert r.task_type == "web_search"
        assert r.which_pass == 2

    def test_web_search_with_url_en(self):
        r = route_sync("search https://github.com for best Python frameworks")
        assert r.task_type == "web_search"

    def test_code_write_function(self):
        r = route_sync("напиши функцию для парсинга JSON в Python")
        assert r.task_type == "code"
        assert r.which_pass == 2

    def test_code_script(self):
        r = route_sync("напиши скрипт для автоматической отправки писем")
        assert r.task_type == "code"

    def test_code_class_keyword(self):
        r = route_sync("как правильно написать class в Python с наследованием")
        assert r.task_type == "code"

    def test_code_def_keyword(self):
        r = route_sync("def calculate_distance что не так в этой функции")
        assert r.task_type == "code"

    def test_code_sql(self):
        r = route_sync("SELECT * FROM users WHERE age > 18 how can I optimize it?")
        assert r.task_type == "code"

    def test_code_algorithm(self):
        r = route_sync("напиши алгоритм сортировки пузырьком")
        assert r.task_type == "code"

    def test_text_privet(self):
        r = route_sync("привет, как дела?")
        assert r.task_type == "text"

    def test_text_chto_takoe(self):
        r = route_sync("что такое фотосинтез?")
        assert r.task_type == "text"

    def test_text_translate(self):
        r = route_sync("переведи на английский: я очень рад тебя видеть")
        assert r.task_type == "text"

    def test_text_book_advice(self):
        r = route_sync("посоветуй книгу по психологии")
        assert r.task_type == "text"

    def test_text_empty(self):
        r = route_sync("")
        assert r.task_type == "text"


class TestRouteModels:
    def test_asr_model(self):
        r = route_sync(attachments=[{"name": "a.wav", "mime": "audio/wav"}])
        assert r.model_id == "whisper-turbo-local"

    def test_vlm_model(self):
        r = route_sync(attachments=[{"name": "img.png", "mime": "image/png"}])
        assert r.model_id == "cotype-pro-vl-32b"

    def test_code_model(self):
        r = route_sync("напиши функцию на Go")
        assert r.model_id == "qwen3-coder-480b-a35b"

    def test_image_gen_model(self):
        r = route_sync("нарисуй кота")
        assert r.model_id == "qwen-image"

    def test_deep_research_model(self):
        r = route_sync("сделай глубокое исследование рынка open-source LLM")
        assert r.model_id == "qwen2.5-72b-instruct"
