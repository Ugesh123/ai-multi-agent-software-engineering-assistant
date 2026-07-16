"""Centralized application configuration.

All runtime configuration is sourced from environment variables (or a `.env`
file) through a single Pydantic settings object. No module in the codebase
should read `os.environ` directly -- everything flows through `get_settings()`
so behaviour stays predictable and testable.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderKind(str, Enum):
    """Supported LLM backends."""

    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class Environment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application-wide configuration.

    Values are loaded from environment variables first, falling back to a
    `.env` file in the backend root, and finally to the defaults declared
    below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MACA_",
        extra="ignore",
    )

    # --- General -----------------------------------------------------
    app_name: str = "Multi-Agent Coding Assistant"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Persistence ---------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./data/maca.db"
    sql_echo: bool = False

    # --- LLM -------------------------------------------------------------
    llm_provider: LLMProviderKind = LLMProviderKind.OLLAMA
    # 127.0.0.1 rather than "localhost" deliberately: on some platforms
    # (notably Windows) "localhost" resolves to both 127.0.0.1 and ::1,
    # and httpx/httpcore/anyio's parallel dual-stack ("happy eyeballs")
    # connection attempt can hit a cancellation race that raises a
    # confusing `ValueError: second argument (exceptions) must be a
    # non-empty sequence` from deep inside anyio instead of a clean
    # connection error. Using the unambiguous literal address avoids the
    # dual-stack lookup entirely rather than merely tolerating its failure.
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:14b"
    ollama_timeout_seconds: float = 120.0
    llm_temperature: float = 0.2
    llm_max_retries: int = 2

    # Alternate hosted-API provider. Model string intentionally has no
    # hardcoded default -- check https://docs.claude.com for current model
    # names and set MACA_ANTHROPIC_MODEL explicitly if using this provider.
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"

    # --- RAG / embeddings --------------------------------------------------
    embedding_provider: LLMProviderKind = LLMProviderKind.OLLAMA
    ollama_embedding_model: str = "nomic-embed-text"
    rag_top_k: int = 5

    # --- Agent workflow ---------------------------------------------------
    max_review_iterations: int = 2
    max_test_repair_iterations: int = 2
    workspace_root: Path = Path("./workspaces")

    # --- CORS --------------------------------------------------------------
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # --- Logging -----------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False

    @field_validator("workspace_root", mode="after")
    @classmethod
    def _ensure_workspace_exists(cls, value: Path) -> Path:
        resolved = value.resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    @property
    def is_test(self) -> bool:
        return self.environment is Environment.TEST


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached settings instance.

    `lru_cache` gives us a cheap singleton without global mutable state,
    and tests can call `get_settings.cache_clear()` to force a reload
    after monkey-patching environment variables.
    """

    return Settings()
