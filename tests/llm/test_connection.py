"""Tests for LLM connection testing."""

from __future__ import annotations

import httpx
import respx

from ainews.llm.config import LLMConfig
from ainews.llm.connectivity import ConnectionTestResult, check_llm_connection


def _make_config(
    base_url: str = "http://localhost:8080/v1",
    api_key: str = "test-key",
    model: str = "test-model",
) -> LLMConfig:
    return LLMConfig(base_url=base_url, api_key=api_key, model=model)


class TestTestResult:
    """TestResult model tests."""

    def test_success_result(self) -> None:
        r = ConnectionTestResult(
            success=True, latency_ms=42.5, model_name="gpt-4o", error=None
        )
        assert r.success is True
        assert r.latency_ms == 42.5
        assert r.model_name == "gpt-4o"
        assert r.error is None

    def test_failure_result(self) -> None:
        r = ConnectionTestResult(
            success=False,
            latency_ms=0.0,
            model_name=None,
            error="Connection refused",
        )
        assert r.success is False
        assert r.error == "Connection refused"


class TestLLMConnection:
    """Test check_llm_connection with mocked HTTP."""

    @respx.mock
    def test_success(self) -> None:
        """Successful 1-token completion should return success=True."""
        config = _make_config()
        respx.post("http://localhost:8080/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "model": "test-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "Hi"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 5,
                        "completion_tokens": 1,
                        "total_tokens": 6,
                    },
                },
            )
        )
        result = check_llm_connection(config)
        assert result.success is True
        assert result.latency_ms > 0
        assert result.model_name == "test-model"
        assert result.error is None

    @respx.mock
    def test_connection_error(self) -> None:
        """Connection error should return success=False with error message."""
        config = _make_config()
        respx.post("http://localhost:8080/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        result = check_llm_connection(config)
        assert result.success is False
        assert result.error is not None
        assert "Connection refused" in result.error or "connect" in result.error.lower()

    @respx.mock
    def test_timeout(self) -> None:
        """Timeout should return success=False."""
        config = _make_config()
        respx.post("http://localhost:8080/v1/chat/completions").mock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )
        result = check_llm_connection(config)
        assert result.success is False
        assert result.error is not None

    @respx.mock
    def test_server_error(self) -> None:
        """HTTP 500 should return success=False."""
        config = _make_config()
        respx.post("http://localhost:8080/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )
        result = check_llm_connection(config)
        assert result.success is False
        assert result.error is not None
