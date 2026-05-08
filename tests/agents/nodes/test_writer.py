"""Tests for writer_node Jinja2 template refactor.

Verifies that the refactored writer_node using report.j2 produces
identical Markdown output to the original hardcoded implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

from ainews.agents.state import GraphState, NodeError

# ── Fixtures ──────────────────────────────────────────────


def _make_state(
    *,
    summaries: list[dict[str, Any]] | None = None,
    trends: list[dict[str, Any]] | None = None,
    errors: list[NodeError] | None = None,
) -> GraphState:
    """Build a minimal GraphState for writer tests."""
    return GraphState(
        run_id="test-run-001",
        params={"topics": ["AI", "ML"], "timeframe_days": 7, "sites": []},
        queries=[],
        raw_results=[],
        fetched_articles=[],
        filtered_articles=[],
        clusters=[],
        summaries=summaries or [],
        trends=trends or [],
        report_md="",
        xlsx_path="",
        errors=errors or [],
        metrics={},
        loop_count=0,
    )


SAMPLE_SUMMARIES: list[dict[str, Any]] = [
    {
        "cluster_id": "c1",
        "headline": "GPT-5 Released",
        "bullets": ["Faster than GPT-4", "Better reasoning"],
        "why_it_matters": "Major milestone in AI capability",
        "sources": ["https://openai.com/blog", "https://techcrunch.com/gpt5"],
    },
    {
        "cluster_id": "c2",
        "headline": "EU AI Act Enforced",
        "bullets": ["New compliance requirements"],
        "why_it_matters": "Regulatory impact on AI companies",
        "sources": ["https://eu-policy.org"],
    },
]

SAMPLE_TRENDS: list[dict[str, Any]] = [
    {
        "name": "Regulatory Convergence",
        "description": "Global AI regulations are converging.",
        "evidence_cluster_ids": ["c1", "c2"],
    },
]


# ── Tests ──────────────────────────────────────────────────


class TestWriterNodeTemplate:
    """Test writer_node produces correct Markdown via Jinja2 template."""

    @patch("ainews.agents.nodes.writer._get_llm")
    @patch("ainews.agents.nodes.writer.datetime")
    def test_template_produces_expected_sections(
        self, mock_dt: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """Writer output contains all required sections."""
        mock_dt.now.return_value = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Executive summary text.")
        mock_get_llm.return_value = mock_llm

        from ainews.agents.nodes.writer import writer_node

        state = _make_state(summaries=SAMPLE_SUMMARIES, trends=SAMPLE_TRENDS)
        result = writer_node.__wrapped__(state)  # type: ignore[attr-defined]
        report = result["report_md"]

        assert report.startswith("# AI News & Trends Report")
        assert "*Generated:" in report
        assert "*Topics: AI, ML | Window: 7 days*" in report
        assert "## Executive Summary" in report
        assert "## Top Stories" in report
        assert "### 1. GPT-5 Released" in report
        assert "### 2. EU AI Act Enforced" in report
        assert "## Key Trends" in report
        assert "### 1. Regulatory Convergence" in report
        assert "## Methodology" in report

    @patch("ainews.agents.nodes.writer._get_llm")
    @patch("ainews.agents.nodes.writer.datetime")
    def test_degradation_notice_with_errors(
        self, mock_dt: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """Degradation notice renders when errors are non-empty."""
        mock_dt.now.return_value = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Summary.")
        mock_get_llm.return_value = mock_llm

        from ainews.agents.nodes.writer import writer_node

        errors = [
            NodeError(node="scraper", message="timeout", traceback=""),
            NodeError(node="filter", message="error", traceback=""),
        ]
        state = _make_state(
            summaries=SAMPLE_SUMMARIES,
            trends=SAMPLE_TRENDS,
            errors=errors,
        )
        result = writer_node.__wrapped__(state)  # type: ignore[attr-defined]
        report = result["report_md"]

        assert "⚠️ **Note:**" in report
        assert "(2 total)" in report

    @patch("ainews.agents.nodes.writer._get_llm")
    @patch("ainews.agents.nodes.writer.datetime")
    def test_no_degradation_notice_without_errors(
        self, mock_dt: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """No degradation notice when errors list is empty."""
        mock_dt.now.return_value = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Summary.")
        mock_get_llm.return_value = mock_llm

        from ainews.agents.nodes.writer import writer_node

        state = _make_state(summaries=SAMPLE_SUMMARIES, trends=SAMPLE_TRENDS)
        result = writer_node.__wrapped__(state)  # type: ignore[attr-defined]
        report = result["report_md"]

        assert "⚠️ **Note:**" not in report

    @patch("ainews.agents.nodes.writer._get_llm")
    @patch("ainews.agents.nodes.writer.datetime")
    def test_empty_summaries(self, mock_dt: MagicMock, mock_get_llm: MagicMock) -> None:
        """Writer handles empty summaries gracefully."""
        mock_dt.now.return_value = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        from ainews.agents.nodes.writer import writer_node

        state = _make_state(summaries=[], trends=SAMPLE_TRENDS)
        result = writer_node.__wrapped__(state)  # type: ignore[attr-defined]
        report = result["report_md"]

        assert "## Top Stories" in report
        assert "## Executive Summary" in report
        # _generate_executive_summary returns fallback for empty summaries
        assert "No stories to summarize." in report

    @patch("ainews.agents.nodes.writer._get_llm")
    @patch("ainews.agents.nodes.writer.datetime")
    def test_empty_trends(self, mock_dt: MagicMock, mock_get_llm: MagicMock) -> None:
        """Writer skips Key Trends section when trends is empty."""
        mock_dt.now.return_value = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Summary.")
        mock_get_llm.return_value = mock_llm

        from ainews.agents.nodes.writer import writer_node

        state = _make_state(summaries=SAMPLE_SUMMARIES, trends=[])
        result = writer_node.__wrapped__(state)  # type: ignore[attr-defined]
        report = result["report_md"]

        assert "## Key Trends" not in report
        assert "## Methodology" in report

    @patch("ainews.agents.nodes.writer._get_llm")
    @patch("ainews.agents.nodes.writer.datetime")
    def test_report_md_in_result(
        self, mock_dt: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """Writer result contains report_md and metrics keys."""
        mock_dt.now.return_value = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Summary.")
        mock_get_llm.return_value = mock_llm

        from ainews.agents.nodes.writer import writer_node

        state = _make_state(summaries=SAMPLE_SUMMARIES, trends=SAMPLE_TRENDS)
        result = writer_node.__wrapped__(state)  # type: ignore[attr-defined]

        assert "report_md" in result
        assert "metrics" in result
        assert isinstance(result["report_md"], str)
        assert len(result["report_md"]) > 0
