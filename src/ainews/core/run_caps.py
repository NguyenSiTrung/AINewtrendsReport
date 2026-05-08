"""Hard run caps — abort pipeline runs that exceed resource limits.

Checked at each node transition to enforce:
- ``max_total_tokens``: cumulative token usage
- ``max_wall_seconds``: wall-clock time
- ``max_articles``: article count fetched
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_MAX_TOKENS = 500_000
_DEFAULT_MAX_WALL_SECONDS = 1800  # 30 minutes
_DEFAULT_MAX_ARTICLES = 200


@dataclass
class RunCapConfig:
    """Configuration for run resource caps."""

    max_total_tokens: int = _DEFAULT_MAX_TOKENS
    max_wall_seconds: int = _DEFAULT_MAX_WALL_SECONDS
    max_articles: int = _DEFAULT_MAX_ARTICLES


@dataclass
class CapViolation:
    """Details of a cap violation."""

    cap_type: str  # "tokens", "wall_time", or "articles"
    current_value: int | float
    limit: int | float
    message: str


class RunCapChecker:
    """Check resource caps at each node transition.

    Parameters
    ----------
    config
        Cap configuration. Uses defaults if not provided.
    start_time
        Wall-clock start time (``time.time()``). Defaults to now.
    """

    def __init__(
        self,
        config: RunCapConfig | None = None,
        start_time: float | None = None,
    ) -> None:
        self.config = config or RunCapConfig()
        self.start_time = start_time or time.time()

    def check(self, state: dict[str, Any]) -> CapViolation | None:
        """Check all caps against current state.

        Parameters
        ----------
        state
            The graph state dict. Expects ``metrics`` (with token counts),
            ``fetched_articles``, and ``raw_results``.

        Returns
        -------
        CapViolation | None
            Details of the first violated cap, or ``None`` if all OK.
        """
        # Check wall time
        elapsed = time.time() - self.start_time
        if elapsed > self.config.max_wall_seconds:
            violation = CapViolation(
                cap_type="wall_time",
                current_value=elapsed,
                limit=self.config.max_wall_seconds,
                message=(
                    f"Wall time exceeded: {elapsed:.0f}s > "
                    f"{self.config.max_wall_seconds}s limit"
                ),
            )
            logger.warning("run_cap_exceeded", **vars(violation))
            return violation

        # Check total tokens
        metrics = state.get("metrics", {})
        total_tokens = sum(
            m.get("tokens", 0)
            for m in metrics.values()
            if isinstance(m, dict)
        )
        if total_tokens > self.config.max_total_tokens:
            violation = CapViolation(
                cap_type="tokens",
                current_value=total_tokens,
                limit=self.config.max_total_tokens,
                message=(
                    f"Token usage exceeded: {total_tokens:,} > "
                    f"{self.config.max_total_tokens:,} limit"
                ),
            )
            logger.warning("run_cap_exceeded", **vars(violation))
            return violation

        # Check article count
        articles = state.get("fetched_articles", [])
        raw_results = state.get("raw_results", [])
        article_count = max(len(articles), len(raw_results))
        if article_count > self.config.max_articles:
            violation = CapViolation(
                cap_type="articles",
                current_value=article_count,
                limit=self.config.max_articles,
                message=(
                    f"Article count exceeded: {article_count} > "
                    f"{self.config.max_articles} limit"
                ),
            )
            logger.warning("run_cap_exceeded", **vars(violation))
            return violation

        return None

    def is_exceeded(self, state: dict[str, Any]) -> bool:
        """Convenience check — returns True if any cap is exceeded."""
        return self.check(state) is not None
