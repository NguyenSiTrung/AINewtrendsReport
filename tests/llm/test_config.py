"""Tests for LLMConfig pydantic model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ainews.llm.config import LLMConfig


class TestLLMConfigConstruction:
    """Test LLMConfig model construction with various inputs."""

    def test_construct_with_all_fields(self) -> None:
        """LLMConfig should accept all defined fields."""
        config = LLMConfig(
            base_url="http://localhost:8080/v1",
            api_key="test-key",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            timeout=60,
            extra_headers={"X-Custom": "value"},
        )
        assert config.base_url == "http://localhost:8080/v1"
        assert config.api_key == "test-key"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.timeout == 60
        assert config.extra_headers == {"X-Custom": "value"}

    def test_construct_with_minimal_fields(self) -> None:
        """LLMConfig should work with only required fields."""
        config = LLMConfig(
            base_url="http://localhost:8080/v1",
            api_key="key",
            model="local-model",
        )
        assert config.base_url == "http://localhost:8080/v1"
        assert config.api_key == "key"
        assert config.model == "local-model"

    def test_defaults_applied(self) -> None:
        """LLMConfig should apply sensible defaults for optional fields."""
        config = LLMConfig(
            base_url="http://localhost:8080/v1",
            api_key="key",
            model="local-model",
        )
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.timeout == 120
        assert config.extra_headers is None

    def test_extra_headers_none_by_default(self) -> None:
        """extra_headers should default to None."""
        config = LLMConfig(
            base_url="http://x",
            api_key="k",
            model="m",
        )
        assert config.extra_headers is None


class TestLLMConfigImmutability:
    """Test that LLMConfig is frozen (immutable)."""

    def test_cannot_set_field(self) -> None:
        """Attempting to set a field should raise ValidationError."""
        config = LLMConfig(
            base_url="http://x",
            api_key="k",
            model="m",
        )
        with pytest.raises(ValidationError):
            config.model = "other"  # type: ignore[misc]

    def test_cannot_set_api_key(self) -> None:
        """api_key should also be immutable."""
        config = LLMConfig(
            base_url="http://x",
            api_key="k",
            model="m",
        )
        with pytest.raises(ValidationError):
            config.api_key = "new"  # type: ignore[misc]


class TestLLMConfigSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self) -> None:
        """LLMConfig should serialize to dict."""
        config = LLMConfig(
            base_url="http://localhost:8080/v1",
            api_key="secret",
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1024,
            timeout=30,
            extra_headers={"Authorization": "Bearer token"},
        )
        data = config.model_dump()
        assert data["base_url"] == "http://localhost:8080/v1"
        assert data["api_key"] == "secret"
        assert data["model"] == "gpt-4o"
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 1024
        assert data["timeout"] == 30
        assert data["extra_headers"] == {"Authorization": "Bearer token"}

    def test_model_dump_json(self) -> None:
        """LLMConfig should serialize to JSON string."""
        config = LLMConfig(
            base_url="http://localhost:8080/v1",
            api_key="key",
            model="m",
        )
        json_str = config.model_dump_json()
        assert '"base_url"' in json_str
        assert '"api_key"' in json_str

    def test_roundtrip(self) -> None:
        """Serialize and deserialize should produce equivalent config."""
        original = LLMConfig(
            base_url="http://localhost:8080/v1",
            api_key="key",
            model="gpt-4o",
            temperature=0.3,
            max_tokens=512,
            timeout=45,
            extra_headers={"X-Test": "1"},
        )
        restored = LLMConfig.model_validate(original.model_dump())
        assert restored == original

    def test_masked_display(self) -> None:
        """masked_api_key should hide the key for display purposes."""
        config = LLMConfig(
            base_url="http://x",
            api_key="sk-1234567890abcdef",
            model="m",
        )
        masked = config.masked_api_key
        assert "sk-1234" not in masked or masked.endswith("***")
        assert len(masked) < len(config.api_key) or "***" in masked

    def test_masked_display_short_key(self) -> None:
        """Short api keys should be fully masked."""
        config = LLMConfig(
            base_url="http://x",
            api_key="abc",
            model="m",
        )
        masked = config.masked_api_key
        assert "***" in masked


class TestLLMConfigValidation:
    """Test field validation."""

    def test_temperature_must_be_non_negative(self) -> None:
        """temperature should not accept negative values."""
        with pytest.raises(ValidationError):
            LLMConfig(
                base_url="http://x",
                api_key="k",
                model="m",
                temperature=-0.1,
            )

    def test_temperature_max_bound(self) -> None:
        """temperature should not exceed 2.0."""
        with pytest.raises(ValidationError):
            LLMConfig(
                base_url="http://x",
                api_key="k",
                model="m",
                temperature=2.1,
            )

    def test_max_tokens_must_be_positive(self) -> None:
        """max_tokens should be positive."""
        with pytest.raises(ValidationError):
            LLMConfig(
                base_url="http://x",
                api_key="k",
                model="m",
                max_tokens=0,
            )

    def test_timeout_must_be_positive(self) -> None:
        """timeout should be positive."""
        with pytest.raises(ValidationError):
            LLMConfig(
                base_url="http://x",
                api_key="k",
                model="m",
                timeout=0,
            )
