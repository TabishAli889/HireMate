"""Application settings loaded from environment variables (and an optional .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration. Secrets use SecretStr so they never print in logs."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HireMate API"
    app_version: str = "1.0.0"
    environment: str = "development"
    # Shared secret the Next.js proxy sends as X-API-Key. Required in production: without it,
    # anyone who finds the API URL could read your profile and spend your Groq quota.
    api_key: SecretStr | None = None
    cors_origins: str = "http://localhost:3000"

    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    # Optional separate model for the agent's tool-choosing planner (e.g. openai/gpt-oss-20b).
    # Groq rate limits are per model, so this moves planner tokens off the main model's quota.
    groq_planner_model: str = ""
    # gpt-oss models "think" before answering; low effort is faster and uses fewer tokens.
    # Only sent to openai/gpt-oss-* models. Empty = the model's default.
    groq_reasoning_effort: Literal["", "low", "medium", "high"] = "low"
    # The planner makes small, high-stakes decisions (which tool next), so it gets a bit more thinking.
    groq_planner_reasoning_effort: Literal["", "low", "medium", "high"] = "medium"
    llm_max_retries: int = 2
    agent_max_steps: int = 12

    database_url: str = "sqlite:///./hiremate.db"
    seed_demo_data: bool = False

    max_upload_mb: int = 5
    upload_rate_limit_per_minute: int = 5
    analysis_rate_limit_per_minute: int = 10

    @field_validator("database_url")
    @classmethod
    def _postgres_driver(cls, url: str) -> str:
        """Hosts hand out postgres:// URLs; SQLAlchemy needs the psycopg (v3) driver named."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def api_key_value(self) -> str:
        return self.api_key.get_secret_value().strip() if self.api_key else ""

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS split on commas, blanks removed."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        """True when a non-empty Groq API key is present."""
        return bool(self.groq_api_key and self.groq_api_key.get_secret_value().strip())

    @property
    def max_upload_bytes(self) -> int:
        """Upload size limit in bytes."""
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance; override with `app.dependency_overrides` in tests."""
    return Settings()
