"""Tests for per-domain rate limiter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from ainews.tools.rate_limiter import RateLimiter


class TestRateLimiterMemory:
    """Test in-memory fallback rate limiter."""

    def test_allows_within_rate(self) -> None:
        limiter = RateLimiter(rate=3, window=1)
        assert limiter.is_allowed("example.com")
        assert limiter.is_allowed("example.com")
        assert limiter.is_allowed("example.com")

    def test_blocks_over_rate(self) -> None:
        limiter = RateLimiter(rate=2, window=1)
        assert limiter.is_allowed("example.com")
        assert limiter.is_allowed("example.com")
        assert not limiter.is_allowed("example.com")

    def test_different_domains_independent(self) -> None:
        limiter = RateLimiter(rate=1, window=1)
        assert limiter.is_allowed("a.com")
        assert limiter.is_allowed("b.com")
        assert not limiter.is_allowed("a.com")

    def test_window_expires(self) -> None:
        limiter = RateLimiter(rate=1, window=0.1)
        assert limiter.is_allowed("example.com")
        assert not limiter.is_allowed("example.com")
        time.sleep(0.15)
        assert limiter.is_allowed("example.com")

    def test_wait_if_needed(self) -> None:
        limiter = RateLimiter(rate=1, window=0.1)
        assert limiter.is_allowed("example.com")
        waited = limiter.wait_if_needed("example.com")
        assert waited > 0


class TestRateLimiterValkey:
    """Test Valkey-backed rate limiter."""

    def test_valkey_allows(self) -> None:
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [1, True]
        mock_redis.pipeline.return_value = mock_pipe

        limiter = RateLimiter(redis_client=mock_redis, rate=2)
        assert limiter.is_allowed("example.com")

    def test_valkey_blocks_over_rate(self) -> None:
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [3, True]
        mock_redis.pipeline.return_value = mock_pipe

        limiter = RateLimiter(redis_client=mock_redis, rate=2)
        assert not limiter.is_allowed("example.com")

    def test_valkey_fallback_on_error(self) -> None:
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = ConnectionError("Valkey down")
        mock_redis.pipeline.return_value = mock_pipe

        limiter = RateLimiter(redis_client=mock_redis, rate=5)
        # Should fall back to memory and allow
        assert limiter.is_allowed("example.com")
