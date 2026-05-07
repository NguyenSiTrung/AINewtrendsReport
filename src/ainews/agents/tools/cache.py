"""In-memory TTL cache implementing the CacheBackend protocol.

Uses ``cachetools.TTLCache`` under the hood.  Swappable to Valkey in Phase 5.
"""

from __future__ import annotations

from cachetools import TTLCache


class InMemoryCache:
    """In-memory cache with TTL expiry and LRU eviction.

    Implements the :class:`~ainews.agents.tools.tavily_search.CacheBackend`
    protocol.

    Parameters
    ----------
    maxsize
        Maximum number of items in the cache (default 256).
    default_ttl
        Default TTL in seconds when not specified per-item (default 6 hours).
    """

    def __init__(
        self,
        maxsize: int = 256,
        default_ttl: int = 21600,
    ) -> None:
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._cache: TTLCache[str, str] = TTLCache(
            maxsize=maxsize,
            ttl=default_ttl,
        )

    def get(self, key: str) -> str | None:
        """Retrieve a cached value, or ``None`` if missing/expired."""
        return self._cache.get(key)

    def set(self, key: str, value: str, ttl: int) -> None:
        """Store a value with a TTL.

        Note: ``cachetools.TTLCache`` applies a global TTL set at construction.
        The per-item ``ttl`` parameter is accepted for protocol compatibility
        but the cache-level TTL governs expiry.
        """
        self._cache[key] = value
