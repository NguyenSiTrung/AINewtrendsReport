"""Application settings powered by pydantic-settings.

All settings can be overridden via ``AINEWS_*`` environment variables
or a ``.env`` file (auto-discovered in the working directory).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

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
    tavily_max_results: int = 10

    # ── Confluence Wiki ───────────────────────────────────
    wiki_base_url: str = ""
    wiki_username: str = ""
    wiki_password: str = ""
    wiki_verify_ssl: bool = True

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


def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Uses ``functools.lru_cache`` so the ``.env`` file and environment
    variables are parsed at most once per process.  Call
    ``clear_settings_cache()`` in tests to reset.
    """
    return _get_settings_cached()


def clear_settings_cache() -> None:
    """Clear the cached ``Settings`` instance (for test isolation)."""
    _get_settings_cached.cache_clear()


@lru_cache(maxsize=1)
def _get_settings_cached() -> Settings:
    return Settings()


def get_wiki_settings(session: Any = None) -> dict[str, Any]:
    """Return effective wiki settings.

    Only ``base_url`` can be overridden from the admin UI (stored in
    ``SettingsKV("wiki")``).  Security-sensitive settings (``username``,
    ``password``, ``verify_ssl``) are **always** read from environment
    variables — they are never stored in the database.

    Parameters
    ----------
    session
        An optional SQLAlchemy session.  When provided the function reads
        the ``SettingsKV("wiki")`` row for ``base_url`` and falls back to
        env vars.  When *None* only env vars are used.

    Returns
    -------
    dict with keys: ``base_url``, ``username``, ``password``, ``verify_ssl``.
    """
    env = get_settings()
    defaults: dict[str, Any] = {
        "base_url": env.wiki_base_url,
        "username": env.wiki_username,      # always from env
        "password": env.wiki_password,      # always from env
        "verify_ssl": env.wiki_verify_ssl,  # always from env
    }

    if session is None:
        return defaults

    try:
        from ainews.models.settings_kv import SettingsKV

        row = session.get(SettingsKV, "wiki")
        if row and isinstance(row.value, dict):
            db_vals = row.value
            return {
                "base_url": db_vals.get("base_url") or defaults["base_url"],
                "username": defaults["username"],       # env only
                "password": defaults["password"],       # env only
                "verify_ssl": defaults["verify_ssl"],   # env only
            }
    except Exception:
        pass

    return defaults

