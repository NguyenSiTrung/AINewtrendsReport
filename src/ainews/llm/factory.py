"""LLM client factory — config resolution and client construction.

The factory follows a two-layer design:

1. **``get_llm_config``** — resolves an :class:`LLMConfig` from three
   sources with explicit priority:
   ``model_override > db_overrides > Settings (env)``.

2. **``get_llm``** — pure construction of a ``ChatOpenAI`` client from
   a resolved :class:`LLMConfig`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ainews.core.config import Settings
from ainews.llm.config import LLMConfig

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

# Fields that can be overridden via ``db_overrides`` dict.
_OVERRIDABLE_FIELDS: frozenset[str] = frozenset(
    {
        "base_url",
        "api_key",
        "model",
        "temperature",
        "max_tokens",
        "timeout",
        "extra_headers",
    }
)


def get_llm_config(
    settings: Settings,
    db_overrides: dict[str, object] | None = None,
    model_override: str | None = None,
) -> LLMConfig:
    """Resolve a fully-merged :class:`LLMConfig`.

    Priority (highest → lowest):

    1. ``model_override`` — per-run CLI / programmatic override (model only).
    2. ``db_overrides``   — runtime overrides stored in ``settings_kv`` table.
    3. ``settings``       — values from env / ``.env`` file.

    Returns
    -------
    LLMConfig
        An immutable, validated configuration instance.
    """
    # Layer 1: base values from Settings
    merged: dict[str, object] = {
        "base_url": settings.llm_base_url,
        "api_key": settings.llm_api_key,
        "model": settings.llm_model,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "timeout": settings.llm_timeout,
        "extra_headers": settings.llm_extra_headers,
    }

    # Layer 2: db overrides (only known keys)
    if db_overrides:
        for key, value in db_overrides.items():
            if key in _OVERRIDABLE_FIELDS:
                merged[key] = value

    # Layer 3: per-run model override (highest priority)
    if model_override is not None:
        merged["model"] = model_override

    return LLMConfig.model_validate(merged)


def get_llm(config: LLMConfig) -> ChatOpenAI:
    """Construct a :class:`ChatOpenAI` from a resolved config.

    This is a pure construction function — no network calls, no side effects.

    Parameters
    ----------
    config
        An immutable :class:`LLMConfig` (typically from :func:`get_llm_config`).

    Returns
    -------
    ChatOpenAI
        Ready-to-use LangChain chat model.
    """
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, object] = {
        "base_url": config.base_url,
        "api_key": config.api_key,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout": config.timeout,
    }
    if config.extra_headers is not None:
        kwargs["default_headers"] = config.extra_headers

    return ChatOpenAI(**kwargs)  # type: ignore[arg-type]
