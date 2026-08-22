"""Application configuration.

A single, validated :class:`Settings` object sourced from environment
variables (and an optional ``.env`` file). Import the module-level
:data:`settings` singleton everywhere — never read ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root (…/backend) — used to resolve relative paths like the sqlite file.
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed, immutable-ish application settings."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:3000")

    # --- Database --------------------------------------------------------
    database_url: str = Field(default="sqlite:///./data/parcelpilot.db")

    # --- LLM (OpenRouter / OpenAI-compatible) ----------------------------
    llm_base_url: str = Field(default="https://openrouter.ai/api/v1")
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="openai/gpt-4o-mini")
    llm_temperature: float = Field(default=0.1)
    llm_max_tokens: int = Field(default=1200)
    llm_timeout_seconds: int = Field(default=60)
    openrouter_referer: str = Field(default="http://localhost:3000")
    openrouter_title: str = Field(default="ParcelPilot Support Intelligence")

    # --- Embeddings ------------------------------------------------------
    embeddings_base_url: str = Field(default="")
    embeddings_api_key: str = Field(default="")
    embeddings_model: str = Field(default="text-embedding-3-small")
    embedding_dim: int = Field(default=256)

    # --- Security --------------------------------------------------------
    auth_secret: str = Field(default="dev-secret-change-me")
    rate_limit_per_minute: int = Field(default=60)

    # --- Domain time -----------------------------------------------------
    # The dataset snapshot is the reference "now" for all time-based logic
    # (SLA elapsed, cancellation windows, pickup delays). From the workbook
    # README: "2026-08-16 11:00 Asia/Kolkata".
    reference_time: str = Field(default="2026-08-16 11:00")
    business_day_start_hour: int = Field(default=9)
    business_day_end_hour: int = Field(default=18)

    # --- Retrieval tuning ------------------------------------------------
    retrieval_top_k: int = Field(default=6)
    retrieval_candidate_k: int = Field(default=24)
    hybrid_alpha: float = Field(default=0.55)
    mmr_lambda: float = Field(default=0.7)

    # ---------------------------------------------------------------------
    # Derived / convenience
    # ---------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def use_mock_llm(self) -> bool:
        """True when no LLM key is configured — the app runs fully offline."""
        return not self.llm_api_key.strip()

    @property
    def use_remote_embeddings(self) -> bool:
        return bool(self.embeddings_base_url.strip() and self.embeddings_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        """Create the parent directory for a local sqlite file if needed, and
        normalise a bare Postgres URL to the psycopg3 driver.

        Managed Postgres hosts (Render, Heroku-style ``postgres://``, Neon)
        hand back a driver-less ``postgres://`` or ``postgresql://`` URL.
        SQLAlchemy's default dialect for that scheme assumes ``psycopg2``,
        which isn't installed — ``requirements.txt`` installs ``psycopg``
        (psycopg3) instead — so left alone this only fails at runtime, in
        production, after the app has otherwise built and deployed fine.
        """
        prefix = "sqlite:///"
        if value.startswith(prefix):
            raw = value[len(prefix):]
            db_path = Path(raw)
            if not db_path.is_absolute():
                db_path = (BACKEND_ROOT / raw).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{prefix}{db_path}"
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""
    return Settings()


settings = get_settings()
