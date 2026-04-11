"""Unit tests for the deterministic router (no Ollama needed)."""
import pytest
from app.services.router_client import RouterClient
from app.config import get_settings

settings = get_settings()


@pytest.fixture
def router():
    return RouterClient(settings)


@pytest.mark.parametrize(
    "message, attachments, expected_task",
    [
        # Audio attachments → ASR
        ("", [{"name": "voice.mp3", "mime": "audio/mpeg"}], "asr"),
        ("", [{"name": "rec.wav", "mime": "audio/wav"}], "asr"),
        ("", [{"name": "note.ogg", "mime": "audio/ogg"}], "asr"),
        # Image attachments → VLM
        ("What's in the photo?", [{"name": "img.jpg", "mime": "image/jpeg"}], "vlm"),
        ("", [{"name": "screen.png", "mime": "image/png"}], "vlm"),
        # Document → file_qa
        ("Summarise this", [{"name": "doc.pdf", "mime": "application/pdf"}], "file_qa"),
        ("", [{"name": "report.docx", "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}], "file_qa"),
        ("", [{"name": "notes.txt", "mime": "text/plain"}], "file_qa"),
        # Deep research keywords
        ("Исследуй влияние ИИ на рынок труда", [], "deep_research"),
        ("Глубокий анализ квантовых компьютеров", [], "deep_research"),
        ("Подробно разбери историю Python", [], "deep_research"),
        # URL in message → web_parse
        ("Зайди на https://example.com и расскажи", [], "web_parse"),
        ("Что написано на http://site.ru?", [], "web_parse"),
        # Code keywords
        ("Напиши функцию сортировки на Python", [], "code"),
        ("Реализуй алгоритм Дейкстры", [], "code"),
        ("Напиши класс для работы с файлами", [], "code"),
    ],
)
def test_deterministic_routing(router, message, attachments, expected_task):
    result = router._deterministic(message, attachments)
    assert result is not None, f"Expected deterministic match for: {message!r}"
    assert result.task_type == expected_task, (
        f"Got {result.task_type!r}, expected {expected_task!r} "
        f"for message={message!r}"
    )


@pytest.mark.parametrize(
    "message",
    [
        "Привет, как дела?",
        "Сколько планет в солнечной системе?",
        "Что такое нейронные сети?",
    ],
)
def test_no_deterministic_match(router, message):
    """Plain questions must fall through to LLM router."""
    result = router._deterministic(message, [])
    assert result is None, f"Should NOT match deterministically: {message!r}"


def test_correct_model_assigned(router):
    """ASR routes to faster-whisper model."""
    result = router._deterministic("", [{"name": "a.mp3", "mime": "audio/mpeg"}])
    assert result is not None
    assert result.model_id == "faster-whisper"


def test_code_model_assigned(router):
    result = router._deterministic("Напиши функцию сортировки", [])
    assert result is not None
    assert result.model_id == "kodify-2.0"


def test_deep_research_tools(router):
    result = router._deterministic("Исследуй тему квантовых компьютеров", [])
    assert result is not None
    assert "web_search" in result.tools
    assert "web_parse" in result.tools
