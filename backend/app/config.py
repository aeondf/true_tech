from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MWS API
    MWS_BASE_URL: str = "https://api.gpt.mws.ru"
    MWS_API_KEY: str = ""

    # Models
    MODEL_TEXT: str = "qwen2.5-72b-instruct"
    MODEL_CODE: str = "qwen3-coder-480b-a35b"
    MODEL_LONG: str = "qwen2.5-72b-instruct"

    # ASR (whisper через MWS)
    ASR_URL: str = "http://localhost:8001"

    # TTS
    TTS_VOICE: str = "ru-RU-SvetlanaNeural"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # игнорируем неизвестные переменные из .env


@lru_cache
def get_settings() -> Settings:
    return Settings()
