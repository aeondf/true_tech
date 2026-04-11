"""Client for faster-whisper media-service."""
import httpx
from fastapi import Depends
from app.config import Settings, get_settings


class ASRClient:
    def __init__(self, settings: Settings):
        self.url = settings.ASR_URL

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.url}/transcribe",
                files={"file": (filename, audio_bytes)},
            )
            r.raise_for_status()
        return r.json()["text"]


def get_asr_client(settings: Settings = Depends(get_settings)) -> ASRClient:
    return ASRClient(settings)
