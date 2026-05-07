"""Tests for InMemoryCache."""

from __future__ import annotations

import time

from ainews.agents.tools.cache import InMemoryCache
from ainews.agents.tools.tavily_search import CacheBackend


class TestInMemoryCache:
    """InMemoryCache implements CacheBackend protocol."""

    def test_implements_cache_backend(self) -> None:
        cache = InMemoryCache()
        assert isinstance(cache, CacheBackend)

    def test_cache_miss(self) -> None:
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_cache_hit(self) -> None:
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl=3600)
        assert cache.get("key1") == "value1"

    def test_cache_overwrite(self) -> None:
        cache = InMemoryCache()
        cache.set("key1", "v1", ttl=3600)
        cache.set("key1", "v2", ttl=3600)
        assert cache.get("key1") == "v2"

    def test_ttl_expiry(self) -> None:
        """Values should expire after TTL."""
        cache = InMemoryCache(maxsize=10, default_ttl=1)
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_maxsize_eviction(self) -> None:
        """Cache should evict LRU items when maxsize is exceeded."""
        cache = InMemoryCache(maxsize=2, default_ttl=3600)
        cache.set("a", "1", ttl=3600)
        cache.set("b", "2", ttl=3600)
        cache.set("c", "3", ttl=3600)  # should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"

    def test_key_hashing_determinism(self) -> None:
        """Same key should always produce same result."""
        cache = InMemoryCache()
        cache.set("deterministic-key", "val", ttl=3600)
        assert cache.get("deterministic-key") == "val"
        assert cache.get("deterministic-key") == "val"

    def test_default_configuration(self) -> None:
        """Default maxsize=256, default_ttl=21600."""
        cache = InMemoryCache()
        assert cache._maxsize == 256
        assert cache._default_ttl == 21600
