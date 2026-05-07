"""Tests for LLM config resolution and factory construction."""

from __future__ import annotations

from ainews.core.config import Settings
from ainews.llm.config import LLMConfig
from ainews.llm.factory import get_llm_config


class TestGetLLMConfigEnvOnly:
    """Test config resolution from Settings (env) alone."""

    def test_resolves_from_settings_defaults(self) -> None:
        """Should produce LLMConfig from Settings defaults."""
        settings = Settings(
            llm_base_url="http://localhost:8080/v1",
            llm_api_key="env-key",
            llm_model="env-model",
            llm_temperature=0.1,
            llm_max_tokens=2048,
            llm_timeout=60,
        )
        config = get_llm_config(settings)
        assert isinstance(config, LLMConfig)
        assert config.base_url == "http://localhost:8080/v1"
        assert config.api_key == "env-key"
        assert config.model == "env-model"
        assert config.temperature == 0.1
        assert config.max_tokens == 2048
        assert config.timeout == 60

    def test_extra_headers_from_settings(self) -> None:
        """Settings extra_headers should pass through."""
        settings = Settings(
            llm_extra_headers={"X-Custom": "val"},
        )
        config = get_llm_config(settings)
        assert config.extra_headers == {"X-Custom": "val"}


class TestGetLLMConfigDBOverrides:
    """Test db_overrides layer takes precedence over Settings."""

    def test_db_overrides_model(self) -> None:
        """db_overrides should override model from Settings."""
        settings = Settings(llm_model="env-model")
        config = get_llm_config(
            settings,
            db_overrides={"model": "db-model"},
        )
        assert config.model == "db-model"

    def test_db_overrides_temperature(self) -> None:
        """db_overrides should override temperature."""
        settings = Settings(llm_temperature=0.0)
        config = get_llm_config(
            settings,
            db_overrides={"temperature": 0.9},
        )
        assert config.temperature == 0.9

    def test_db_overrides_partial(self) -> None:
        """db_overrides should only override specified keys."""
        settings = Settings(
            llm_model="env-model",
            llm_api_key="env-key",
        )
        config = get_llm_config(
            settings,
            db_overrides={"model": "db-model"},
        )
        assert config.model == "db-model"
        assert config.api_key == "env-key"  # not overridden

    def test_db_overrides_all_fields(self) -> None:
        """db_overrides can override all overridable fields."""
        settings = Settings()
        config = get_llm_config(
            settings,
            db_overrides={
                "base_url": "http://db:9090/v1",
                "api_key": "db-key",
                "model": "db-model",
                "temperature": 1.0,
                "max_tokens": 512,
                "timeout": 30,
            },
        )
        assert config.base_url == "http://db:9090/v1"
        assert config.api_key == "db-key"
        assert config.model == "db-model"
        assert config.temperature == 1.0
        assert config.max_tokens == 512
        assert config.timeout == 30


class TestGetLLMConfigModelOverride:
    """Test model_override takes highest precedence."""

    def test_model_override_beats_settings(self) -> None:
        """model_override should override Settings model."""
        settings = Settings(llm_model="env-model")
        config = get_llm_config(settings, model_override="override-model")
        assert config.model == "override-model"

    def test_model_override_beats_db_overrides(self) -> None:
        """model_override should override db_overrides model."""
        settings = Settings(llm_model="env-model")
        config = get_llm_config(
            settings,
            db_overrides={"model": "db-model"},
            model_override="override-model",
        )
        assert config.model == "override-model"


class TestGetLLMConfigFullChain:
    """Test the full priority chain."""

    def test_full_chain(self) -> None:
        """Priority: model_override > db_overrides > Settings."""
        settings = Settings(
            llm_base_url="http://env:8080/v1",
            llm_api_key="env-key",
            llm_model="env-model",
            llm_temperature=0.1,
            llm_max_tokens=1000,
            llm_timeout=100,
        )
        config = get_llm_config(
            settings,
            db_overrides={
                "api_key": "db-key",
                "model": "db-model",
                "temperature": 0.5,
            },
            model_override="final-model",
        )
        # model_override wins for model
        assert config.model == "final-model"
        # db_overrides wins for api_key, temperature
        assert config.api_key == "db-key"
        assert config.temperature == 0.5
        # Settings wins for the rest
        assert config.base_url == "http://env:8080/v1"
        assert config.max_tokens == 1000
        assert config.timeout == 100

    def test_empty_overrides_are_noops(self) -> None:
        """Empty dicts and None model_override should not change anything."""
        settings = Settings(llm_model="env-model")
        config = get_llm_config(
            settings,
            db_overrides={},
            model_override=None,
        )
        assert config.model == "env-model"
