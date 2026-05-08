"""Tests for agents.nodes.planner — Planner node."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from ainews.agents.nodes.planner import planner_node
from ainews.agents.state import GraphState, RunParams


def _make_state(**overrides: Any) -> GraphState:
    """Create a minimal GraphState for testing."""
    defaults: GraphState = {
        "run_id": "test-run",
        "params": RunParams(
            timeframe_days=7, topics=["AI", "LLM"], sites=["techcrunch.com"]
        ),
        "queries": [],
        "raw_results": [],
        "fetched_articles": [],
        "filtered_articles": [],
        "clusters": [],
        "summaries": [],
        "trends": [],
        "report_md": "",
        "xlsx_path": "",
        "errors": [],
        "metrics": {},
        "loop_count": 0,
    }
    defaults.update(overrides)  # type: ignore[typeddict-item]
    return defaults


class TestPlannerNode:
    """Verify Planner node generates search queries via LLM."""

    def test_planner_returns_queries(self) -> None:
        """Planner calls LLM and returns parsed query list."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps(
                [
                    "latest AI breakthroughs 2026",
                    "LLM open source models news",
                    "AI regulation updates",
                ]
            )
        )

        state = _make_state()
        with patch("ainews.agents.nodes.planner._get_llm", return_value=mock_llm):
            result = planner_node(state)

        assert "queries" in result
        assert len(result["queries"]) == 3
        assert "latest AI breakthroughs 2026" in result["queries"]

    def test_planner_handles_json_in_markdown_block(self) -> None:
        """Planner handles LLM wrapping JSON in ```json blocks."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='```json\n["query 1", "query 2"]\n```'
        )

        state = _make_state()
        with patch("ainews.agents.nodes.planner._get_llm", return_value=mock_llm):
            result = planner_node(state)

        assert len(result["queries"]) == 2

    def test_planner_handles_malformed_json(self) -> None:
        """Planner handles malformed LLM output gracefully."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="This is not valid JSON at all"
        )

        state = _make_state()
        with patch("ainews.agents.nodes.planner._get_llm", return_value=mock_llm):
            result = planner_node(state)

        # Should return errors and/or fallback queries
        assert "errors" in result or "queries" in result

    def test_planner_handles_llm_exception(self) -> None:
        """Planner catches LLM errors via @node_resilient."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = ConnectionError("LLM unreachable")

        state = _make_state()
        with patch("ainews.agents.nodes.planner._get_llm", return_value=mock_llm):
            result = planner_node(state)

        # @node_resilient catches and returns errors
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_planner_tracks_metrics(self) -> None:
        """Planner records metrics for the node."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='["query 1"]')

        state = _make_state()
        with patch("ainews.agents.nodes.planner._get_llm", return_value=mock_llm):
            result = planner_node(state)

        assert "metrics" in result
        assert "planner" in result["metrics"]
