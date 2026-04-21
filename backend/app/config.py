"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/order_supervisor"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/order_supervisor"

    # Groq
    GROQ_API_KEY: str = "gsk_your-key-here"

    # Agent
    AGENT_MODEL: str = "llama-3.3-70b-versatile"
    CLASSIFIER_MODEL: str = "llama-3.3-70b-versatile"
    MAX_RUN_AGE_HOURS: int = 72
    DEFAULT_WAKE_INTERVAL_MINUTES: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
