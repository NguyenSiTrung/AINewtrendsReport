"""LLM concurrency cap — asyncio.Semaphore wrapper around LLM calls.

Limits the number of concurrent LLM invocations to prevent GPU
saturation on local LLM servers.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_MAX_CONCURRENCY = 2

# Module-level semaphore (thread-safe initialisation)
_lock = threading.Lock()
_semaphore: asyncio.Semaphore | None = None
_threading_semaphore: threading.Semaphore | None = None
_max_concurrency: int = _DEFAULT_MAX_CONCURRENCY


def configure(max_concurrency: int | None = None) -> None:
    """Configure the concurrency limit.

    Must be called before any LLM calls. Safe to call multiple times
    (resets the semaphore).

    Parameters
    ----------
    max_concurrency
        Maximum concurrent LLM calls. Defaults to 2.
    """
    global _semaphore, _threading_semaphore, _max_concurrency  # noqa: PLW0603
    with _lock:
        _max_concurrency = max_concurrency or _DEFAULT_MAX_CONCURRENCY
        _semaphore = asyncio.Semaphore(_max_concurrency)
        _threading_semaphore = threading.Semaphore(_max_concurrency)
        logger.info("llm_concurrency_configured", max_concurrency=_max_concurrency)


def get_semaphore() -> asyncio.Semaphore:
    """Get the async semaphore, creating it lazily if needed."""
    global _semaphore  # noqa: PLW0603
    if _semaphore is None:
        with _lock:
            if _semaphore is None:
                _semaphore = asyncio.Semaphore(_max_concurrency)
    return _semaphore


def get_threading_semaphore() -> threading.Semaphore:
    """Get the threading semaphore for sync contexts."""
    global _threading_semaphore  # noqa: PLW0603
    if _threading_semaphore is None:
        with _lock:
            if _threading_semaphore is None:
                _threading_semaphore = threading.Semaphore(_max_concurrency)
    return _threading_semaphore


async def limited_invoke(llm: Any, *args: Any, **kwargs: Any) -> Any:
    """Invoke an LLM with concurrency limiting (async).

    Parameters
    ----------
    llm
        A LangChain chat model (e.g., ChatOpenAI).
    *args, **kwargs
        Arguments forwarded to ``llm.ainvoke()``.

    Returns
    -------
    Any
        The LLM response.
    """
    sem = get_semaphore()
    async with sem:
        logger.debug("llm_concurrency_acquired", max=_max_concurrency)
        return await llm.ainvoke(*args, **kwargs)


def limited_invoke_sync(llm: Any, *args: Any, **kwargs: Any) -> Any:
    """Invoke an LLM with concurrency limiting (sync).

    Parameters
    ----------
    llm
        A LangChain chat model (e.g., ChatOpenAI).
    *args, **kwargs
        Arguments forwarded to ``llm.invoke()``.

    Returns
    -------
    Any
        The LLM response.
    """
    sem = get_threading_semaphore()
    sem.acquire()
    try:
        logger.debug("llm_concurrency_acquired_sync", max=_max_concurrency)
        return llm.invoke(*args, **kwargs)
    finally:
        sem.release()
