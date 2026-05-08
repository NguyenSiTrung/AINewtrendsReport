"""Structured logging configuration using structlog.

Produces JSON-formatted log lines with standard context fields:
timestamp, level, logger name, and event.

Includes a processor to mask sensitive values (API keys, secrets)
so they never appear in log output.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

# Keys whose values should be masked in log output
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "password",
        "token",
        "authorization",
        "ainews_llm_api_key",
        "ainews_tavily_api_key",
        "tavily_api_key",
        "llm_api_key",
    }
)

# Regex pattern for sensitive keys (case-insensitive)
_SENSITIVE_PATTERN = re.compile(
    r"(api[_-]?key|secret|password|token|authorization)", re.IGNORECASE
)

_MASK = "***REDACTED***"


def mask_sensitive_keys(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that masks sensitive values in log events.

    Checks both exact key matches and regex patterns against all
    key-value pairs in the event dict.
    """
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if key_lower in _SENSITIVE_KEYS or _SENSITIVE_PATTERN.search(key_lower):
            event_dict[key] = _MASK
    return event_dict


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON rendering.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure stdlib logging as structlog's output backend
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=numeric_level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            mask_sensitive_keys,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
