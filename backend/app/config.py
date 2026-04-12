from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MWS API
    MWS_BASE_URL: str = "https://api.gpt.mws.ru"
    MWS_API_KEY: str = "sk-ewgiaPC3A6pPDYHwR8siVA"  # empty = requests to MWS will fail, but app starts

    # Models
    MODEL_TEXT: str = "qwen2.5-72b-instruct"
    MODEL_CODE: str = "qwen3-coder-480b-a35b"
    MODEL_LONG: str = "qwen2.5-72b-instruct"
    MODEL_EMBED: str = "bge-m3"

    # PostgreSQL + pgvector
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/mirea"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Router (LLM routing через MWS API)
    ROUTER_URL: str = "http://localhost:11434"  # legacy, не используется
    ROUTER_MODEL: str = "qwen2.5:3b"            # legacy, не используется

    # ASR (whisper-turbo-local через MWS, fallback на media-service)
    ASR_URL: str = "http://localhost:8001"

    # TTS
    TTS_VOICE: str = "ru-RU-SvetlanaNeural"

    # Image generation / VLM
    IMAGE_GEN_URL: str = "http://localhost:8002"
    VLM_URL: str = "http://localhost:8003"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Misc
    MAX_FILE_SIZE_MB: int = 50
    CHUNK_SIZE: int = 512          # tokens per chunk
    CHUNK_OVERLAP: int = 64
    MEMORY_TTL_SECONDS: int = 3600
    MEMORY_TOP_K: int = 10
    CONTEXT_MAX_TOKENS: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
