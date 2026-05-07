"""Tavily search wrapper with project defaults and caching.

Wraps ``langchain-tavily.TavilySearch`` with:
- Project defaults (``topic="news"``, Markdown raw content).
- Pluggable cache via the :class:`CacheBackend` protocol (default: in-memory TTL).
- Structured :class:`SearchResult` output.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

# ── Models ────────────────────────────────────────────────


class SearchResult(BaseModel):
    """A single search result from Tavily."""

    url: str
    title: str
    content: str
    raw_content: str | None = None
    score: float


# ── Cache Protocol ────────────────────────────────────────


@runtime_checkable
class CacheBackend(Protocol):
    """Pluggable cache interface.

    Phase 2 uses an in-memory ``TTLCache``; Phase 5 swaps to Valkey.
    """

    def get(self, key: str) -> str | None:
        """Retrieve a cached value by key, or ``None`` if missing/expired."""
        ...

    def set(self, key: str, value: str, ttl: int) -> None:
        """Store a value with a TTL (seconds)."""
        ...
