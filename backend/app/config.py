from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MWS API
    MWS_BASE_URL: str = "https://api.gpt.mws.ru"
    MWS_API_KEY: str = ""

    # Models
    MODEL_TEXT: str = "mws-gpt-alpha"
    MODEL_CODE: str = "qwen3-coder-480b-a35b"
    MODEL_LONG: str = "qwen2.5-72b-instruct"
    MODEL_RESEARCH_QUERY: str = "llama-3.1-8b-instruct"
    MODEL_RESEARCH_SYNTHESIS: str = "qwen2.5-72b-instruct"

    # ASR (whisper через MWS)
    ASR_URL: str = "http://localhost:8001"

    # TTS
    TTS_VOICE: str = "ru-RU-SvetlanaNeural"

    # Research pipeline
    RESEARCH_SUBQUERY_COUNT: int = 4
    RESEARCH_SEARCH_RESULTS: int = 3
    RESEARCH_CONCURRENCY: int = 4
    RESEARCH_PARSE_TIMEOUT: int = 12
    RESEARCH_SEARCH_TIMEOUT: int = 15
    RESEARCH_FETCH_TOTAL_TIMEOUT: int = 60
    RESEARCH_SUBQUERY_TIMEOUT: int = 15
    RESEARCH_SYNTHESIS_TIMEOUT: int = 75
    RESEARCH_MAX_SOURCE_TEXT_CHARS: int = 2000
    RESEARCH_MAX_SOURCES: int = 8
    RESEARCH_MAX_CONTEXT_CHARS: int = 12000
    RESEARCH_MAX_ACTIVE_RUNS: int = 2
    RESEARCH_SEARCH_THREADS: int = 4
    RESEARCH_MAX_PAGE_BYTES: int = 1_500_000

    # Auth
    SECRET_KEY: str = "change-me-in-production-use-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mws_gateway"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # игнорируем неизвестные переменные из .env


@lru_cache
def get_settings() -> Settings:
    return Settings()
