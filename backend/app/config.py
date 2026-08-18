from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./tutor.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-only-secret-change-me"
    access_token_minutes: int = 1440
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    cors_origins: str = "http://localhost:5173"
    api_prefix: str = "/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

