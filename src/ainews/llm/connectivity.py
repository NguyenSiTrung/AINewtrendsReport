"""LLM connectivity test.

Provides a lightweight probe that issues a 1-token completion request to
verify the LLM server is reachable and responding.
"""

from __future__ import annotations

import time

import httpx
import structlog
from pydantic import BaseModel

from ainews.llm.config import LLMConfig

logger = structlog.get_logger(__name__)


class ConnectionTestResult(BaseModel):
    """Structured result of an LLM connectivity test."""

    success: bool
    latency_ms: float
    model_name: str | None = None
    error: str | None = None


def check_llm_connection(config: LLMConfig) -> ConnectionTestResult:
    """Issue a 1-token completion to verify LLM connectivity.

    Parameters
    ----------
    config
        Resolved LLM configuration.

    Returns
    -------
    ConnectionTestResult
        Structured result with success status, latency, and error if any.
        Never raises — all errors are caught and returned in the result.
    """
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 1,
        "temperature": 0.0,
    }
    headers: dict[str, str] = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    if config.extra_headers:
        headers.update(config.extra_headers)

    url = f"{config.base_url}/chat/completions"
    start = time.perf_counter()

    try:
        with httpx.Client(timeout=config.timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if response.status_code >= 400:
                body = response.text
                logger.warning(
                    "llm_connection_test_failed",
                    status_code=response.status_code,
                    body=body[:200],
                )
                return ConnectionTestResult(
                    success=False,
                    latency_ms=elapsed_ms,
                    error=f"HTTP {response.status_code}: {body[:200]}",
                )

            data = response.json()
            model_name = data.get("model", config.model)

            logger.info(
                "llm_connection_test_ok",
                model=model_name,
                latency_ms=round(elapsed_ms, 1),
            )
            return ConnectionTestResult(
                success=True,
                latency_ms=round(elapsed_ms, 1),
                model_name=model_name,
            )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("llm_connection_test_error", error=str(exc))
        return ConnectionTestResult(
            success=False,
            latency_ms=round(elapsed_ms, 1),
            error=str(exc),
        )
