from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./tutor.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-only-secret-change-me-now"
    access_token_minutes: int = 1440
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    llm_provider: str = "openai"
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"))
    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: float = Field(default=30.0, ge=5, le=120)
    llm_max_output_tokens: int = Field(default=500, ge=100, le=2000)
    llm_reasoning_effort: str = "low"
    cors_origins: str = "http://localhost:5173"
    admin_emails: str = ""
    api_prefix: str = "/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        return {item.strip().casefold() for item in self.admin_emails.split(",") if item.strip()}

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env.casefold() == "production" and len(self.secret_key.encode()) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 bytes in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
