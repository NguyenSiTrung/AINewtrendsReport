"""Per-domain token-bucket rate limiter backed by Valkey (Redis).

Uses INCR + TTL for a sliding-window counter per domain.
Falls back to a simple in-memory dict when Valkey is unavailable.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_RATE = 2  # requests per second per domain
_DEFAULT_WINDOW = 1  # window size in seconds


class RateLimiter:
    """Token-bucket rate limiter using Valkey (Redis-compatible) backend.

    Parameters
    ----------
    redis_client
        A Redis/Valkey client instance. If ``None``, uses in-memory fallback.
    rate
        Maximum requests per window per domain.
    window
        Window size in seconds.
    """

    def __init__(
        self,
        redis_client: Any = None,
        rate: int = _DEFAULT_RATE,
        window: int = _DEFAULT_WINDOW,
    ) -> None:
        self._redis = redis_client
        self._rate = rate
        self._window = window
        # In-memory fallback when Valkey is unavailable
        self._memory: dict[str, list[float]] = {}

    def _key(self, domain: str) -> str:
        return f"ainews:ratelimit:{domain}"

    def is_allowed(self, domain: str) -> bool:
        """Check if a request to ``domain`` is allowed under the rate limit.

        Returns ``True`` if allowed, ``False`` if throttled.
        """
        if self._redis is not None:
            return self._check_valkey(domain)
        return self._check_memory(domain)

    def wait_if_needed(self, domain: str) -> float:
        """Block until a request to ``domain`` is allowed.

        Returns the number of seconds waited (0.0 if immediately allowed).
        """
        waited = 0.0
        while not self.is_allowed(domain):
            sleep_time = self._window / self._rate
            time.sleep(sleep_time)
            waited += sleep_time
        return waited

    def _check_valkey(self, domain: str) -> bool:
        """Use Valkey INCR + EXPIRE for atomic rate check."""
        key = self._key(domain)
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self._window)
            result = pipe.execute()
            count = result[0]
            return count <= self._rate
        except Exception as exc:
            logger.warning("rate_limiter_valkey_error", domain=domain, error=str(exc))
            return self._check_memory(domain)

    def _check_memory(self, domain: str) -> bool:
        """In-memory sliding window fallback."""
        now = time.time()
        if domain not in self._memory:
            self._memory[domain] = []

        # Remove expired entries
        window_start = now - self._window
        self._memory[domain] = [t for t in self._memory[domain] if t > window_start]

        if len(self._memory[domain]) >= self._rate:
            return False

        self._memory[domain].append(now)
        return True
