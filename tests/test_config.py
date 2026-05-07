"""Tests for ainews.core.config — Settings class."""

from __future__ import annotations

from pathlib import Path

import pytest

from ainews.core.config import Settings


class TestSettingsDefaults:
    """Settings should work with sensible defaults when no env is set."""

    def test_db_path_default(self) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.db_path == Path("./var/ainews.db")

    def test_valkey_url_default(self) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.valkey_url == "redis://127.0.0.1:6379/0"

    def test_log_level_default(self) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.log_level == "INFO"

    def test_llm_temperature_default(self) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_temperature == 0.0

    def test_llm_max_tokens_default(self) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_max_tokens == 4096

    def test_llm_timeout_default(self) -> None:
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_timeout == 120


class TestSettingsEnvOverride:
    """Settings should be overridable via AINEWS_* env vars."""

    def test_llm_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_LLM_BASE_URL", "http://localhost:8080/v1")
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_base_url == "http://localhost:8080/v1"

    def test_llm_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_LLM_API_KEY", "sk-test-key")
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_api_key == "sk-test-key"

    def test_llm_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_LLM_MODEL", "qwen2.5-32b")
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_model == "qwen2.5-32b"

    def test_db_path_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_DB_PATH", "/tmp/test.db")
        s = Settings()  # type: ignore[call-arg]
        assert s.db_path == Path("/tmp/test.db")

    def test_log_level_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_LOG_LEVEL", "DEBUG")
        s = Settings()  # type: ignore[call-arg]
        assert s.log_level == "DEBUG"

    def test_tavily_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_TAVILY_API_KEY", "tvly-test")
        s = Settings()  # type: ignore[call-arg]
        assert s.tavily_api_key == "tvly-test"

    def test_llm_extra_headers_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AINEWS_LLM_EXTRA_HEADERS", '{"X-Custom": "value"}')
        s = Settings()  # type: ignore[call-arg]
        assert s.llm_extra_headers == {"X-Custom": "value"}


class TestSettingsEnvFile:
    """Settings should load from .env file."""

    def test_loads_from_dotenv(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("AINEWS_LOG_LEVEL=WARNING\nAINEWS_LLM_MODEL=test-model\n")
        s = Settings(_env_file=env_file)  # type: ignore[call-arg]
        assert s.log_level == "WARNING"
        assert s.llm_model == "test-model"
