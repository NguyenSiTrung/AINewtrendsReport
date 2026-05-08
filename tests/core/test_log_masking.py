"""Tests for structlog sensitive key masking."""

from __future__ import annotations

from ainews.core.logging import mask_sensitive_keys


class TestMaskSensitiveKeys:
    def test_masks_api_key(self) -> None:
        event = {"event": "test", "api_key": "sk-secret-123"}
        result = mask_sensitive_keys(None, "", event)
        assert result["api_key"] == "***REDACTED***"

    def test_masks_tavily_api_key(self) -> None:
        event = {"event": "test", "tavily_api_key": "tvly-abc"}
        result = mask_sensitive_keys(None, "", event)
        assert result["tavily_api_key"] == "***REDACTED***"

    def test_masks_password(self) -> None:
        event = {"event": "test", "password": "hunter2"}
        result = mask_sensitive_keys(None, "", event)
        assert result["password"] == "***REDACTED***"

    def test_masks_token(self) -> None:
        event = {"event": "test", "token": "jwt-xyz"}
        result = mask_sensitive_keys(None, "", event)
        assert result["token"] == "***REDACTED***"

    def test_preserves_non_sensitive(self) -> None:
        event = {"event": "test", "url": "http://example.com", "status": 200}
        result = mask_sensitive_keys(None, "", event)
        assert result["url"] == "http://example.com"
        assert result["status"] == 200

    def test_case_insensitive_matching(self) -> None:
        event = {"event": "test", "API_KEY": "secret"}
        result = mask_sensitive_keys(None, "", event)
        assert result["API_KEY"] == "***REDACTED***"

    def test_pattern_match_api_key_variants(self) -> None:
        for key in ["api-key", "apikey", "Api_Key"]:
            event = {"event": "test", key: "value"}
            result = mask_sensitive_keys(None, "", event)
            assert result[key] == "***REDACTED***", f"Failed for key: {key}"

    def test_preserves_event_field(self) -> None:
        event = {"event": "startup", "api_key": "sk-123"}
        result = mask_sensitive_keys(None, "", event)
        assert result["event"] == "startup"
