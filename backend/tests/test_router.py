"""
test_router.py — 50 примеров для проверки трёхпроходного роутера.

Тестирует только Проход 1 и Проход 2 (детерминированные).
Проход 3 (LLM) не тестируется здесь — он требует живого MWS.

Запуск:
    cd backend
    pip install pytest pytest-asyncio
    pytest tests/test_router.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.router_client import RouterClient, RouteResult
from app.config import Settings


def make_router() -> RouterClient:
    settings = Settings(MWS_API_KEY="test", MWS_BASE_URL="http://localhost")
    return RouterClient(settings)


def route_sync(message: str = "", attachments: list[dict] | None = None) -> RouteResult:
    """Синхронная обёртка для детерминированных проходов (1 и 2)."""
    router = make_router()
    attachments = attachments or []
    result = router._pass1(attachments)
    if result:
        return result
    result = router._pass2(message)
    if result:
        return result
    # Возвращаем text как дефолт (pass 3 не вызываем без MWS)
    return RouteResult("text", "qwen2.5-72b-instruct", 0.5, 3)


# ═══════════════════════════════════════════════════════
# ПРОХОД 1 — MIME / расширение (15 примеров)
# ═══════════════════════════════════════════════════════

class TestPass1Mime:

    def test_audio_mp3(self):
        r = route_sync(attachments=[{"name": "song.mp3", "mime": "audio/mpeg"}])
        assert r.task_type == "asr"
        assert r.which_pass == 1

    def test_audio_wav(self):
        r = route_sync(attachments=[{"name": "record.wav", "mime": "audio/wav"}])
        assert r.task_type == "asr"

    def test_audio_ogg(self):
        r = route_sync(attachments=[{"name": "voice.ogg", "mime": "audio/ogg"}])
        assert r.task_type == "asr"

    def test_audio_m4a(self):
        r = route_sync(attachments=[{"name": "clip.m4a", "mime": ""}])
        assert r.task_type == "asr"

    def test_audio_mime_only(self):
        # mime без расширения
        r = route_sync(attachments=[{"name": "audiofile", "mime": "audio/flac"}])
        assert r.task_type == "asr"

    def test_image_jpg(self):
        r = route_sync(attachments=[{"name": "photo.jpg", "mime": "image/jpeg"}])
        assert r.task_type == "vlm"
        assert r.which_pass == 1

    def test_image_png(self):
        r = route_sync(attachments=[{"name": "screenshot.png", "mime": "image/png"}])
        assert r.task_type == "vlm"

    def test_image_webp(self):
        r = route_sync(attachments=[{"name": "pic.webp", "mime": ""}])
        assert r.task_type == "vlm"

    def test_image_gif(self):
        r = route_sync(attachments=[{"name": "anim.gif", "mime": "image/gif"}])
        assert r.task_type == "vlm"

    def test_image_mime_only(self):
        r = route_sync(attachments=[{"name": "img", "mime": "image/png"}])
        assert r.task_type == "vlm"

    def test_pdf(self):
        r = route_sync(attachments=[{"name": "report.pdf", "mime": "application/pdf"}])
        assert r.task_type == "file_qa"
        assert r.which_pass == 1

    def test_docx(self):
        r = route_sync(attachments=[{"name": "doc.docx", "mime": ""}])
        assert r.task_type == "file_qa"

    def test_txt(self):
        r = route_sync(attachments=[{"name": "notes.txt", "mime": "text/plain"}])
        assert r.task_type == "file_qa"

    def test_audio_overrides_message(self):
        # Даже если сообщение про код — аудио-файл побеждает
        r = route_sync(
            message="напиши функцию",
            attachments=[{"name": "voice.wav", "mime": "audio/wav"}],
        )
        assert r.task_type == "asr"

    def test_image_overrides_research(self):
        # Даже если текст — исследовательский — картинка побеждает
        r = route_sync(
            message="изучи тему квантовых вычислений",
            attachments=[{"name": "chart.png", "mime": "image/png"}],
        )
        assert r.task_type == "vlm"


# ═══════════════════════════════════════════════════════
# ПРОХОД 2 — структурный анализ (30 примеров)
# ═══════════════════════════════════════════════════════

class TestPass2Structural:

    # ── deep_research (8 примеров) ──────────────────────

    def test_research_izuchi(self):
        r = route_sync("изучи тему квантовых вычислений подробно")
        assert r.task_type == "deep_research"
        assert r.which_pass == 2

    def test_research_glubok_analiz(self):
        r = route_sync("глубокий анализ рынка электромобилей в 2025 году")
        assert r.task_type == "deep_research"

    def test_research_podrobno_razberi(self):
        r = route_sync("подробно разбери принципы работы трансформеров в ML")
        assert r.task_type == "deep_research"

    def test_research_deep_research_en(self):
        r = route_sync("deep research on climate change effects on agriculture")
        assert r.task_type == "deep_research"

    def test_research_detalniy(self):
        r = route_sync("детальный анализ конкурентов в нише SaaS-продуктов")
        assert r.task_type == "deep_research"

    def test_research_proanaliziruimy(self):
        r = route_sync("проанализируй текущее состояние рынка NFT")
        assert r.task_type == "deep_research"

    def test_research_razberi_podrobno(self):
        r = route_sync("разбери подробно архитектуру микросервисов")
        assert r.task_type == "deep_research"

    def test_research_rasskazhi_podrobno(self):
        r = route_sync("расскажи подробно про историю Второй мировой войны")
        assert r.task_type == "deep_research"

    # ── image_gen (4 примера) ───────────────────────────

    def test_image_gen_narisuy(self):
        r = route_sync("нарисуй закат над морем в стиле импрессионизма")
        assert r.task_type == "image_gen"
        assert r.which_pass == 2

    def test_image_gen_sgeneriruy(self):
        r = route_sync("сгенерируй изображение робота в городе")
        assert r.task_type == "image_gen"

    def test_image_gen_sozdai(self):
        r = route_sync("создай картинку уютного кафе зимой")
        assert r.task_type == "image_gen"

    def test_image_gen_en(self):
        r = route_sync("draw a futuristic city at night")
        assert r.task_type == "image_gen"

    # ── web_parse (4 примера) ───────────────────────────

    def test_web_parse_otkroi(self):
        r = route_sync("открой https://habr.com/ru/articles/123 и перескажи")
        assert r.task_type == "web_parse"
        assert r.which_pass == 2

    def test_web_parse_prochitay(self):
        r = route_sync("прочитай https://example.com/article и сделай выжимку")
        assert r.task_type == "web_parse"

    def test_web_parse_proanaliziruimy_link(self):
        r = route_sync("проанализируй ссылку https://openai.com/blog/gpt4")
        assert r.task_type == "web_parse"

    def test_web_parse_summarize(self):
        r = route_sync("summarize https://arxiv.org/abs/2303.08774")
        assert r.task_type == "web_parse"

    # ── web_search (3 примера) ──────────────────────────

    def test_web_search_naydi_url(self):
        r = route_sync("найди информацию на https://google.com про Python")
        assert r.task_type == "web_search"
        assert r.which_pass == 2

    def test_web_search_poischi(self):
        r = route_sync("поищи на https://stackoverflow.com ответ про asyncio")
        assert r.task_type == "web_search"

    def test_web_search_en(self):
        r = route_sync("search https://github.com for best Python frameworks")
        assert r.task_type == "web_search"

    # ── code (6 примеров) ───────────────────────────────

    def test_code_napishy_funkciyu(self):
        r = route_sync("напиши функцию для парсинга JSON в Python")
        assert r.task_type == "code"
        assert r.which_pass == 2

    def test_code_napishy_skript(self):
        r = route_sync("напиши скрипт для автоматической отправки писем")
        assert r.task_type == "code"

    def test_code_class_keyword(self):
        r = route_sync("как правильно написать class в Python с наследованием")
        assert r.task_type == "code"

    def test_code_def_keyword(self):
        r = route_sync("def calculate_distance что не так в этой функции")
        assert r.task_type == "code"

    def test_code_sql(self):
        r = route_sync("SELECT * FROM users WHERE age > 18 — как оптимизировать?")
        assert r.task_type == "code"

    def test_code_algoritm(self):
        r = route_sync("напиши алгоритм сортировки пузырьком")
        assert r.task_type == "code"

    # ── text (5 примеров — дефолт) ──────────────────────

    def test_text_privet(self):
        r = route_sync("привет, как дела?")
        assert r.task_type == "text"

    def test_text_chto_takoe(self):
        r = route_sync("что такое фотосинтез?")
        assert r.task_type == "text"

    def test_text_perevedi(self):
        r = route_sync("переведи на английский: я очень рад тебя видеть")
        assert r.task_type == "text"

    def test_text_sovet(self):
        r = route_sync("посоветуй книгу по психологии")
        assert r.task_type == "text"

    def test_text_empty(self):
        r = route_sync("")
        assert r.task_type == "text"


# ═══════════════════════════════════════════════════════
# Проверка моделей в RouteResult (5 примеров)
# ═══════════════════════════════════════════════════════

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
        r = route_sync("изучи тему машинного обучения")
        assert r.model_id == "qwen2.5-72b-instruct"
