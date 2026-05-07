"""Tests for agents.resilience — error resilience utilities."""

from __future__ import annotations

import time
from typing import Any

import pytest

from ainews.agents.resilience import (
    should_degrade,
    track_metrics,
    with_retries,
)
from ainews.agents.state import GraphState, NodeError, RunParams


def _make_state(**overrides: Any) -> GraphState:
    """Create a minimal GraphState for testing."""
    defaults: GraphState = {
        "run_id": "test-run",
        "params": RunParams(timeframe_days=7, topics=["AI"], sites=[]),
        "queries": [],
        "raw_results": [],
        "fetched_articles": [],
        "filtered_articles": [],
        "clusters": [],
        "summaries": [],
        "trends": [],
        "report_md": "",
        "errors": [],
        "metrics": {},
        "loop_count": 0,
    }
    defaults.update(overrides)  # type: ignore[typeddict-item]
    return defaults


class TestWithRetries:
    """Verify tenacity retry wrapper."""

    def test_success_on_first_attempt(self) -> None:
        """Function succeeds on first call — no retries."""
        call_count = 0

        @with_retries(max_attempts=3)
        def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_retries_on_connection_error(self) -> None:
        """Retries on ConnectionError up to max_attempts."""
        call_count = 0

        @with_retries(max_attempts=3, wait_seconds=0.01)
        def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("connection refused")
            return "ok"

        assert fail_twice() == "ok"
        assert call_count == 3

    def test_gives_up_after_max_attempts(self) -> None:
        """Raises after exhausting retries."""

        @with_retries(max_attempts=2, wait_seconds=0.01)
        def always_fail() -> str:
            raise ConnectionError("still broken")

        with pytest.raises(ConnectionError):
            always_fail()

    def test_retries_on_timeout(self) -> None:
        """Retries on TimeoutError."""
        call_count = 0

        @with_retries(max_attempts=2, wait_seconds=0.01)
        def timeout_once() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timed out")
            return "ok"

        assert timeout_once() == "ok"
        assert call_count == 2


class TestTrackMetrics:
    """Verify per-node metrics tracking."""

    def test_adds_metrics_to_state(self) -> None:
        """track_metrics records wall time and token usage."""
        state = _make_state()
        start = time.time() - 1.5  # Simulate 1.5s elapsed

        result = track_metrics(
            "planner",
            state,
            start_time=start,
            input_tokens=100,
            output_tokens=50,
        )
        assert "planner" in result
        assert result["planner"]["input_tokens"] == 100
        assert result["planner"]["output_tokens"] == 50
        assert result["planner"]["wall_seconds"] >= 1.0

    def test_metrics_without_tokens(self) -> None:
        """track_metrics works with zero tokens (non-LLM nodes)."""
        state = _make_state()
        start = time.time() - 0.5

        result = track_metrics("scraper", state, start_time=start)
        assert result["scraper"]["input_tokens"] == 0
        assert result["scraper"]["output_tokens"] == 0
        assert result["scraper"]["wall_seconds"] >= 0.4


class TestShouldDegrade:
    """Verify degradation checker."""

    def test_no_errors_no_degrade(self) -> None:
        """No errors → no degradation."""
        state = _make_state()
        assert should_degrade(state, error_threshold=3) is False

    def test_below_threshold_no_degrade(self) -> None:
        """Errors below threshold → no degradation."""
        errors = [
            NodeError(node="planner", message="err1", traceback=""),
            NodeError(node="filter", message="err2", traceback=""),
        ]
        state = _make_state(errors=errors)
        assert should_degrade(state, error_threshold=3) is False

    def test_at_threshold_degrades(self) -> None:
        """Errors at threshold → degrade."""
        errors = [
            NodeError(node="planner", message="err1", traceback=""),
            NodeError(node="filter", message="err2", traceback=""),
            NodeError(node="scraper", message="err3", traceback=""),
        ]
        state = _make_state(errors=errors)
        assert should_degrade(state, error_threshold=3) is True

    def test_above_threshold_degrades(self) -> None:
        """Errors above threshold → degrade."""
        errors = [
            NodeError(node=f"node{i}", message=f"err{i}", traceback="")
            for i in range(5)
        ]
        state = _make_state(errors=errors)
        assert should_degrade(state, error_threshold=3) is True
