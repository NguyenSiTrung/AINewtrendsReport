"""Tests for hard run caps (RunCapChecker)."""

from __future__ import annotations

import time

from ainews.core.run_caps import RunCapChecker, RunCapConfig


class TestRunCapConfig:
    def test_defaults(self) -> None:
        config = RunCapConfig()
        assert config.max_total_tokens == 500_000
        assert config.max_wall_seconds == 1800
        assert config.max_articles == 200


class TestRunCapChecker:
    def test_no_violation_empty_state(self) -> None:
        checker = RunCapChecker()
        result = checker.check({})
        assert result is None

    def test_no_violation_under_limits(self) -> None:
        checker = RunCapChecker(
            config=RunCapConfig(
                max_total_tokens=1000,
                max_articles=10,
            )
        )
        state = {
            "metrics": {"node1": {"input_tokens": 50, "output_tokens": 50}},
            "fetched_articles": [{"title": "a"}] * 5,
        }
        assert checker.check(state) is None

    def test_token_cap_exceeded(self) -> None:
        checker = RunCapChecker(config=RunCapConfig(max_total_tokens=100))
        state = {
            "metrics": {
                "node1": {"input_tokens": 30, "output_tokens": 30},
                "node2": {"input_tokens": 25, "output_tokens": 25},
            },
        }
        violation = checker.check(state)
        assert violation is not None
        assert violation.cap_type == "tokens"
        assert violation.current_value == 110
        assert violation.limit == 100

    def test_article_cap_exceeded(self) -> None:
        checker = RunCapChecker(config=RunCapConfig(max_articles=3))
        state = {
            "fetched_articles": [{"url": f"http://a.com/{i}"} for i in range(5)],
        }
        violation = checker.check(state)
        assert violation is not None
        assert violation.cap_type == "articles"
        assert violation.current_value == 5

    def test_wall_time_cap_exceeded(self) -> None:
        # Start time 10 seconds in the past
        checker = RunCapChecker(
            config=RunCapConfig(max_wall_seconds=5),
            start_time=time.time() - 10,
        )
        violation = checker.check({})
        assert violation is not None
        assert violation.cap_type == "wall_time"

    def test_wall_time_not_exceeded(self) -> None:
        checker = RunCapChecker(
            config=RunCapConfig(max_wall_seconds=60),
        )
        violation = checker.check({})
        assert violation is None

    def test_is_exceeded_convenience(self) -> None:
        checker = RunCapChecker(config=RunCapConfig(max_articles=1))
        assert not checker.is_exceeded({})
        assert checker.is_exceeded({"fetched_articles": [1, 2, 3]})

    def test_uses_raw_results_for_article_count(self) -> None:
        checker = RunCapChecker(config=RunCapConfig(max_articles=2))
        state = {
            "raw_results": [1, 2, 3],
            "fetched_articles": [],
        }
        violation = checker.check(state)
        assert violation is not None
        assert violation.cap_type == "articles"

    def test_priority_wall_time_first(self) -> None:
        """Wall time is checked first."""
        checker = RunCapChecker(
            config=RunCapConfig(max_wall_seconds=1, max_total_tokens=10),
            start_time=time.time() - 100,
        )
        state = {"metrics": {"a": {"input_tokens": 500, "output_tokens": 499}}}
        violation = checker.check(state)
        assert violation is not None
        assert violation.cap_type == "wall_time"
