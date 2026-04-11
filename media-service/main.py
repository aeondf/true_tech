"""
media-service — единый сервис для всех медиа-операций.

Эндпоинты:
  POST /asr/transcribe    — аудио → текст (faster-whisper)
  POST /tts/synthesize    — текст → MP3 (edge-tts)
  POST /image/generate    — текст → картинка (Stable Diffusion через Ollama/AUTOMATIC1111)
  POST /vlm/analyze       — картинка + вопрос → текст (LLaVA через Ollama)
  GET  /health            — статус всех компонентов
"""
import asyncio
import base64
import io
import os
import tempfile
from functools import partial

import httpx
import edge_tts
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="media-service", version="1.0.0")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
TTS_VOICE = os.getenv("TTS_VOICE", "ru-RU-SvetlanaNeural")
SD_URL = os.getenv("SD_URL", "")  # Stable Diffusion AUTOMATIC1111 API, если есть


# ── ASR ──────────────────────────────────────────────────────────

@app.post("/asr/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Аудио файл → текст через faster-whisper."""
    try:
        import faster_whisper
    except ImportError:
        raise HTTPException(status_code=503, detail="faster-whisper не установлен")

    audio_bytes = await audio.read()

    def _run() -> str:
        model = faster_whisper.WhisperModel(WHISPER_MODEL, device="cpu")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            segments, _ = model.transcribe(f.name)
            return "".join(s.text for s in segments).strip()

    loop = asyncio.get_event_loop()
    try:
        text = await loop.run_in_executor(None, _run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR ошибка: {e}")

    return {"text": text}


# ── TTS ──────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    voice: str = TTS_VOICE


@app.post("/tts/synthesize")
async def synthesize(req: TTSRequest):
    """Текст → MP3 через edge-tts."""
    buf = io.BytesIO()
    try:
        communicate = edge_tts.Communicate(req.text, req.voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS ошибка: {e}")

    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/mpeg")


# ── Image Generation ─────────────────────────────────────────────

class ImageGenRequest(BaseModel):
    prompt: str
    width: int = 512
    height: int = 512
    steps: int = 20


@app.post("/image/generate")
async def generate_image(req: ImageGenRequest):
    """Генерация изображения через Stable Diffusion (AUTOMATIC1111 API)."""
    if not SD_URL:
        # Fallback — текстовое описание
        return {
            "image_b64": None,
            "mime": None,
            "fallback": True,
            "description": (
                f"Сервис генерации изображений не настроен (SD_URL не задан).\n"
                f"Описание: {req.prompt}"
            ),
        }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{SD_URL}/sdapi/v1/txt2img",
                json={
                    "prompt": req.prompt,
                    "width": req.width,
                    "height": req.height,
                    "steps": req.steps,
                },
            )
            r.raise_for_status()
            data = r.json()
            image_b64 = data["images"][0]
    except Exception as e:
        return {
            "image_b64": None,
            "mime": None,
            "fallback": True,
            "description": f"Stable Diffusion недоступен: {e}\nЗапрос: {req.prompt}",
        }

    return {"image_b64": image_b64, "mime": "image/png", "fallback": False}


# ── VLM ──────────────────────────────────────────────────────────

@app.post("/vlm/analyze")
async def vlm_analyze(
    image: UploadFile = File(...),
    question: str = Form(...),
):
    """Анализ изображения через LLaVA (Ollama)."""
    image_bytes = await image.read()
    image_b64 = base64.b64encode(image_bytes).decode()

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llava",
                    "prompt": question,
                    "images": [image_b64],
                    "stream": False,
                },
            )
            r.raise_for_status()
            answer = r.json().get("response", "")
    except Exception as e:
        return {
            "answer": None,
            "fallback": True,
            "message": f"VLM (LLaVA) недоступен: {e}",
        }

    return {"answer": answer, "fallback": False}


# ── Health ───────────────────────────────────────────────────────

@app.get("/health")
async def health():
    status: dict[str, str] = {}

    # Проверяем Ollama (нужен для LLaVA)
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            status["ollama"] = "ok"
            status["llava"] = "ok" if any("llava" in m for m in models) else "model_not_pulled"
    except Exception:
        status["ollama"] = "unavailable"
        status["llava"] = "unavailable"

    # Проверяем edge-tts
    try:
        import edge_tts  # noqa
        status["tts"] = "ok"
    except ImportError:
        status["tts"] = "not_installed"

    # Проверяем faster-whisper
    try:
        import faster_whisper  # noqa
        status["asr"] = "ok"
    except ImportError:
        status["asr"] = "not_installed"

    # Stable Diffusion
    if SD_URL:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                await client.get(f"{SD_URL}/sdapi/v1/sd-models")
            status["image_gen"] = "ok"
        except Exception:
            status["image_gen"] = "unavailable"
    else:
        status["image_gen"] = "not_configured"

    overall = "ok" if all(v in ("ok", "not_configured") for v in status.values()) else "degraded"
    return {"status": overall, "services": status}
