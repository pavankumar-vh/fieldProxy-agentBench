"""Application settings, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/agentbench"
    redis_url: str = "redis://localhost:6379"
    # Comma-separated. When the frontend is deployed (e.g. Vercel), append
    # its production URL here so the browser may call this API.
    cors_origins: str = "http://localhost:3000"

    # Gemini provider (free API keys: https://aistudio.google.com).
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-3.5-flash"

    # Groq provider (OpenAI-compatible, fast free tier: console.groq.com).
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"

    @model_validator(mode="after")
    def _normalize_database_url(self):
        # Render (and some hosts) hand out postgres:// URLs; SQLAlchemy
        # needs the explicit psycopg dialect.
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace(
                "postgres://", "postgresql+psycopg://", 1
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
