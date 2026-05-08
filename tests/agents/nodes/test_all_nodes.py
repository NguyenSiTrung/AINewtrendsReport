"""Tests for all Phase 2 nodes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

from ainews.agents.state import (
    Article,
    GraphState,
    NodeError,
    RunParams,
    SearchHit,
    Summary,
    Trend,
)


def _make_state(**overrides: Any) -> GraphState:
    """Create a minimal GraphState for testing."""
    defaults: GraphState = {
        "run_id": "test-run",
        "params": RunParams(
            timeframe_days=7, topics=["AI", "LLM"], sites=["example.com"]
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


# ── Scraper Node ─────────────────────────────────────────


class TestScraperNode:
    """Verify Scraper node enriches raw results."""

    def test_scraper_converts_raw_results_to_articles(self) -> None:
        """Scraper converts SearchHits to Articles."""
        from ainews.agents.nodes.scraper import scraper_node

        hits = [
            SearchHit(
                url="https://example.com/article1",
                title="Test Article",
                content="Short",
                raw_content="Full content here that is long enough " * 10,
                score=0.9,
            ),
        ]
        state = _make_state(raw_results=hits)
        result = scraper_node(state)

        assert "fetched_articles" in result
        assert len(result["fetched_articles"]) == 1
        assert result["fetched_articles"][0]["url"] == "https://example.com/article1"

    def test_scraper_handles_empty_results(self) -> None:
        """Scraper handles empty raw_results gracefully."""
        from ainews.agents.nodes.scraper import scraper_node

        state = _make_state(raw_results=[])
        result = scraper_node(state)

        assert result["fetched_articles"] == []


# ── Filter Node ──────────────────────────────────────────


class TestFilterNode:
    """Verify Filter node scores and filters articles."""

    def test_filter_keeps_relevant_articles(self) -> None:
        """Filter keeps articles scored above threshold."""
        from ainews.agents.nodes.filter import filter_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({"score": 0.9, "keep": True, "reason": "Relevant"})
        )

        articles = [
            Article(
                url="https://example.com/a",
                title="AI Article",
                content_md="Article about AI models.",
                source="example.com",
                published_at="2026-05-07T12:00:00Z",
                relevance_score=0.8,
            ),
        ]
        state = _make_state(fetched_articles=articles)

        with patch("ainews.agents.nodes.filter._get_llm", return_value=mock_llm):
            result = filter_node(state)

        assert len(result["filtered_articles"]) == 1
        assert result["loop_count"] == 1

    def test_filter_rejects_low_scoring_articles(self) -> None:
        """Filter drops articles scored below threshold."""
        from ainews.agents.nodes.filter import filter_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({"score": 0.2, "keep": False, "reason": "Not relevant"})
        )

        articles = [
            Article(
                url="https://example.com/b",
                title="Unrelated Article",
                content_md="Article about cooking.",
                source="example.com",
                published_at="2026-05-07T12:00:00Z",
                relevance_score=0.2,
            ),
        ]
        state = _make_state(fetched_articles=articles)

        with patch("ainews.agents.nodes.filter._get_llm", return_value=mock_llm):
            result = filter_node(state)

        assert len(result["filtered_articles"]) == 0


class TestFilterRouter:
    """Verify filter conditional edge routing."""

    def test_routes_to_planner_when_too_few_kept(self) -> None:
        """Routes to planner if fewer than min_kept and loop_count < 2."""
        from ainews.agents.nodes.filter import filter_router

        state = _make_state(filtered_articles=[], loop_count=0)
        assert filter_router(state) == "planner"

    def test_routes_to_dedup_when_enough_kept(self) -> None:
        """Routes to dedup if enough articles kept."""
        from ainews.agents.nodes.filter import filter_router

        articles = [
            Article(
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                content_md="Content",
                source="example.com",
                published_at="",
                relevance_score=0.9,
            )
            for i in range(5)
        ]
        state = _make_state(filtered_articles=articles, loop_count=1)
        assert filter_router(state) == "dedup"

    def test_routes_to_dedup_when_max_loops_reached(self) -> None:
        """Routes to dedup after max loops even if few results."""
        from ainews.agents.nodes.filter import filter_router

        state = _make_state(filtered_articles=[], loop_count=2)
        assert filter_router(state) == "dedup"


# ── Dedup Node ───────────────────────────────────────────


class TestDedupNode:
    """Verify Dedup node clusters articles."""

    def test_dedup_creates_clusters(self) -> None:
        """Dedup creates clusters from filtered articles."""
        from ainews.agents.nodes.dedup import dedup_node

        articles = [
            Article(
                url="https://example.com/a",
                title="AI Article 1",
                content_md="Content about AI models and breakthroughs.",
                source="example.com",
                published_at=datetime.now(tz=UTC).isoformat(),
                relevance_score=0.9,
            ),
            Article(
                url="https://other.com/b",
                title="Different Story",
                content_md="Completely different content about something else.",
                source="other.com",
                published_at=datetime.now(tz=UTC).isoformat(),
                relevance_score=0.8,
            ),
        ]
        state = _make_state(filtered_articles=articles)
        result = dedup_node(state)

        assert "clusters" in result
        assert len(result["clusters"]) >= 1

    def test_dedup_handles_empty_input(self) -> None:
        """Dedup handles empty filtered_articles."""
        from ainews.agents.nodes.dedup import dedup_node

        state = _make_state(filtered_articles=[])
        result = dedup_node(state)

        assert result["clusters"] == []


# ── Trender Node ─────────────────────────────────────────


class TestTrenderNode:
    """Verify Trender node identifies trends."""

    def test_trender_extracts_trends(self) -> None:
        """Trender calls LLM and returns parsed trends."""
        from ainews.agents.nodes.trender import trender_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps(
                [
                    {
                        "name": "Open Source AI",
                        "description": "Growing trend toward open models",
                        "evidence_cluster_ids": ["cluster-001"],
                    }
                ]
            )
        )

        summaries = [
            Summary(
                cluster_id="cluster-001",
                headline="Open AI Model Released",
                bullets=["New model is open source"],
                why_it_matters="Democratizes AI",
                sources=["https://example.com"],
            ),
        ]
        state = _make_state(summaries=summaries)

        with patch("ainews.agents.nodes.trender._get_llm", return_value=mock_llm):
            result = trender_node(state)

        assert len(result["trends"]) == 1
        assert result["trends"][0]["name"] == "Open Source AI"

    def test_trender_handles_empty_summaries(self) -> None:
        """Trender handles no summaries gracefully."""
        from ainews.agents.nodes.trender import trender_node

        state = _make_state(summaries=[])
        result = trender_node(state)

        assert result["trends"] == []


# ── Writer Node ──────────────────────────────────────────


class TestWriterNode:
    """Verify Writer node assembles Markdown report."""

    def test_writer_generates_report(self) -> None:
        """Writer creates a Markdown report from summaries and trends."""
        from ainews.agents.nodes.writer import writer_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="This week saw major developments in AI..."
        )

        summaries = [
            Summary(
                cluster_id="cluster-001",
                headline="AI Breakthrough",
                bullets=["Key point 1", "Key point 2"],
                why_it_matters="Significant impact",
                sources=["https://example.com/a"],
            ),
        ]
        trends = [
            Trend(
                name="Open Source AI",
                description="Growing trend",
                evidence_cluster_ids=["cluster-001"],
            ),
        ]
        state = _make_state(summaries=summaries, trends=trends)

        with patch("ainews.agents.nodes.writer._get_llm", return_value=mock_llm):
            result = writer_node(state)

        assert "report_md" in result
        assert "# AI News & Trends Report" in result["report_md"]
        assert "AI Breakthrough" in result["report_md"]
        assert "Open Source AI" in result["report_md"]
        assert "Methodology" in result["report_md"]

    def test_writer_includes_degradation_notice(self) -> None:
        """Writer adds degradation notice when errors present."""
        from ainews.agents.nodes.writer import writer_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Summary text")

        errors = [NodeError(node="planner", message="err", traceback="")]
        summaries = [
            Summary(
                cluster_id="c1",
                headline="Story",
                bullets=["Point"],
                why_it_matters="Impact",
                sources=["https://example.com"],
            ),
        ]
        state = _make_state(summaries=summaries, errors=errors)

        with patch("ainews.agents.nodes.writer._get_llm", return_value=mock_llm):
            result = writer_node(state)

        assert "⚠️" in result["report_md"]
        assert "partial data" in result["report_md"]

    def test_writer_handles_empty_summaries(self) -> None:
        """Writer handles no summaries."""
        from ainews.agents.nodes.writer import writer_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Nothing to report")

        state = _make_state(summaries=[], trends=[])

        with patch("ainews.agents.nodes.writer._get_llm", return_value=mock_llm):
            result = writer_node(state)

        assert "report_md" in result
        assert len(result["report_md"]) > 0
