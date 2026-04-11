"""edge-tts: text → MP3 bytes."""
import io
import edge_tts
from fastapi import Depends
from app.config import Settings, get_settings


class TTSService:
    def __init__(self, settings: Settings):
        self.voice = settings.TTS_VOICE

    async def synthesize(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, self.voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()


def get_tts_service(settings: Settings = Depends(get_settings)) -> TTSService:
    return TTSService(settings)
