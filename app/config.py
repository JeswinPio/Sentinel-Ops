from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


class Settings(BaseSettings):
    """Environment-driven configuration. Values come from env vars or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ops"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "playbooks"
    embedding_provider: str = "fastembed"

    llm_provider: Literal["mock", "anthropic", "openai", "ollama"] = "mock"
    llm_model: str = ""
    llm_api_key: SecretStr | None = None

    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None

    jwt_secret: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
