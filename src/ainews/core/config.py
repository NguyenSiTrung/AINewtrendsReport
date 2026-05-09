"""Application settings powered by pydantic-settings.

All settings can be overridden via ``AINEWS_*`` environment variables
or a ``.env`` file (auto-discovered in the working directory).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_local_timezone() -> str:
    """Detect the system's local timezone, falling back to UTC."""
    try:
        from tzlocal import get_localzone

        return str(get_localzone())
    except Exception:
        import time

        if time.timezone == 0:
            return "UTC"
        # Fallback: try reading /etc/timezone
        try:
            with open("/etc/timezone") as f:
                tz = f.read().strip()
                if tz:
                    return tz
        except FileNotFoundError:
            pass
        return "UTC"


class Settings(BaseSettings):
    """Central configuration for the ainews pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="AINEWS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ───────────────────────────────────────────────
    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "local-model"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    llm_timeout: int = 120
    llm_extra_headers: dict[str, str] | None = None

    # ── Database ──────────────────────────────────────────
    db_path: Path = Path("./var/ainews.db")

    # ── Valkey (cache/broker) ─────────────────────────────
    valkey_url: str = "redis://127.0.0.1:6379/0"

    # ── Tavily search ─────────────────────────────────────
    tavily_api_key: str = ""

    # ── Pipeline ──────────────────────────────────────────
    report_max_sources: int = 50

    # ── Timezone ──────────────────────────────────────────
    timezone: str = _detect_local_timezone()

    # ── Logging ───────────────────────────────────────────
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def database_url(self) -> str:
        """SQLAlchemy-compatible URL derived from db_path."""
        return f"sqlite+pysqlite:///{self.db_path.resolve()}"
