"""
ASR client.

Priority:
  1. MWS whisper-turbo-local (via /v1/audio/transcriptions OpenAI-compatible)
  2. media-service faster-whisper (local fallback)
"""
import httpx
from fastapi import Depends
from app.config import Settings, get_settings

MWS_ASR_MODEL = "whisper-turbo-local"


class ASRClient:
    def __init__(self, settings: Settings):
        self.mws_base = settings.MWS_BASE_URL
        self.mws_key = settings.MWS_API_KEY
        self.media_url = settings.ASR_URL

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        # 1. MWS whisper-turbo-local
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{self.mws_base}/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.mws_key}"},
                    files={"file": (filename, audio_bytes)},
                    data={"model": MWS_ASR_MODEL},
                )
                r.raise_for_status()
                return r.json()["text"]
        except Exception:
            pass

        # 2. media-service fallback
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.media_url}/transcribe",
                files={"file": (filename, audio_bytes)},
            )
            r.raise_for_status()
        return r.json()["text"]


def get_asr_client(settings: Settings = Depends(get_settings)) -> ASRClient:
    return ASRClient(settings)
