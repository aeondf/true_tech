"""
TTS Service.

Priority:
  1. Silero TTS (local, high quality Russian, works in Docker)
  2. edge-tts fallback (requires Bing WebSocket — may fail in Docker)
"""
import asyncio
import io
import logging
from functools import lru_cache

from fastapi import Depends
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_silero_model = None
_silero_lock: asyncio.Lock | None = None


async def _get_silero():
    """Lazy-load Silero model (cached after first load)."""
    global _silero_model, _silero_lock
    if _silero_lock is None:
        _silero_lock = asyncio.Lock()
    if _silero_model is not None:
        return _silero_model
    async with _silero_lock:
        if _silero_model is not None:
            return _silero_model
        loop = asyncio.get_running_loop()
        _silero_model = await loop.run_in_executor(None, _load_silero)
    return _silero_model


def _load_silero():
    import torch
    model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v4_ru",
        trust_repo=True,
    )
    return model


def _split_sentences(text: str, max_chars: int = 150) -> list[str]:
    """Split text into chunks safe for Silero (max ~250 chars per chunk)."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            # If single sentence is too long — split by comma
            if len(s) > max_chars:
                parts = re.split(r"(?<=,)\s+", s)
                part_buf = ""
                for p in parts:
                    if len(part_buf) + len(p) + 1 <= max_chars:
                        part_buf = (part_buf + " " + p).strip()
                    else:
                        if part_buf:
                            chunks.append(part_buf)
                        part_buf = p[:max_chars]
                if part_buf:
                    chunks.append(part_buf)
            else:
                current = s
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def _silero_synthesize(model, text: str, speaker: str = "baya", sample_rate: int = 24000) -> bytes:
    """Run Silero inference in thread (CPU, sync). Splits long text into chunks."""
    import torch
    import wave
    import numpy as np

    chunks = _split_sentences(text)
    all_audio = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        try:
            audio = model.apply_tts(text=chunk, speaker=speaker, sample_rate=sample_rate)
            all_audio.append(audio.numpy())
        except Exception:
            continue  # skip problematic chunk

    if not all_audio:
        raise RuntimeError("Silero produced no audio")

    combined = np.concatenate(all_audio)
    pcm = (combined * 32767).astype("int16").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


class TTSService:
    def __init__(self, settings: Settings):
        self.voice = settings.TTS_VOICE  # used by edge-tts fallback

    async def synthesize(self, text: str) -> tuple[bytes, str]:
        """
        Returns (audio_bytes, mime_type).
        mime_type is "audio/wav" for Silero, "audio/mpeg" for edge-tts.
        """
        # 1. Try Silero
        try:
            model = await _get_silero()
            loop = asyncio.get_running_loop()
            wav_bytes = await loop.run_in_executor(
                None, _silero_synthesize, model, text[:1000]
            )
            return wav_bytes, "audio/wav"
        except Exception as e:
            logger.warning("Silero TTS failed: %s", e)

        # 2. Fallback: edge-tts
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, self.voice)
            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            return buf.getvalue(), "audio/mpeg"
        except Exception as e2:
            import traceback
            logger.error("edge-tts also failed: %s\n%s", e2, traceback.format_exc())
            raise


def get_tts_service(settings: Settings = Depends(get_settings)) -> TTSService:
    return TTSService(settings)
