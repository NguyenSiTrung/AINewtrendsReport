"""Tests for agents.state — GraphState TypedDict and supporting types."""

from __future__ import annotations

from datetime import UTC, datetime

from ainews.agents.state import (
    Article,
    Cluster,
    GraphState,
    NodeError,
    RunParams,
    SearchHit,
    Summary,
    Trend,
)


class TestGraphStateDefaults:
    """Verify GraphState field defaults and type annotations."""

    def test_minimal_state_creation(self) -> None:
        """GraphState can be created with only run_id and params."""
        state: GraphState = {
            "run_id": "test-run-001",
            "params": RunParams(
                timeframe_days=7,
                topics=["LLM"],
                sites=[],
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
        assert state["run_id"] == "test-run-001"
        assert state["loop_count"] == 0
        assert state["errors"] == []
        assert state["metrics"] == {}
        assert state["report_md"] == ""

    def test_state_with_populated_lists(self) -> None:
        """GraphState supports populated list fields."""
        hit = SearchHit(
            url="https://example.com/article",
            title="Test Article",
            content="Article content",
            raw_content="Full raw content",
            score=0.95,
        )
        state: GraphState = {
            "run_id": "run-002",
            "params": RunParams(
                timeframe_days=3,
                topics=["GPT"],
                sites=["example.com"],
            ),
            "queries": ["latest GPT news"],
            "raw_results": [hit],
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
        assert len(state["raw_results"]) == 1
        assert state["raw_results"][0]["url"] == "https://example.com/article"


class TestRunParams:
    """Verify RunParams TypedDict."""

    def test_params_with_required_fields(self) -> None:
        params = RunParams(
            timeframe_days=7,
            topics=["AI", "LLM"],
            sites=["techcrunch.com"],
        )
        assert params["timeframe_days"] == 7
        assert params["topics"] == ["AI", "LLM"]
        assert params["sites"] == ["techcrunch.com"]


class TestSearchHit:
    """Verify SearchHit TypedDict."""

    def test_all_fields(self) -> None:
        hit = SearchHit(
            url="https://example.com",
            title="Title",
            content="Short content",
            raw_content="Full content here",
            score=0.88,
        )
        assert hit["url"] == "https://example.com"
        assert hit["score"] == 0.88
        assert hit["raw_content"] == "Full content here"

    def test_optional_raw_content(self) -> None:
        hit = SearchHit(
            url="https://example.com",
            title="Title",
            content="Content",
            raw_content=None,
            score=0.5,
        )
        assert hit["raw_content"] is None


class TestArticle:
    """Verify Article TypedDict."""

    def test_article_fields(self) -> None:
        article = Article(
            url="https://example.com/post",
            title="An Article",
            content_md="# Article\n\nContent here.",
            source="techcrunch.com",
            published_at="2026-05-07T12:00:00Z",
            relevance_score=0.85,
        )
        assert article["url"] == "https://example.com/post"
        assert article["relevance_score"] == 0.85


class TestCluster:
    """Verify Cluster TypedDict."""

    def test_cluster_with_primary_and_variants(self) -> None:
        primary = Article(
            url="https://example.com/a",
            title="Primary",
            content_md="Primary content",
            source="example.com",
            published_at="2026-05-07T12:00:00Z",
            relevance_score=0.9,
        )
        variant = Article(
            url="https://other.com/a",
            title="Variant",
            content_md="Similar content",
            source="other.com",
            published_at="2026-05-07T11:00:00Z",
            relevance_score=0.7,
        )
        cluster = Cluster(
            primary=primary,
            variants=[variant],
            cluster_id="cluster-001",
        )
        assert cluster["primary"]["title"] == "Primary"
        assert len(cluster["variants"]) == 1

    def test_cluster_without_variants(self) -> None:
        primary = Article(
            url="https://example.com/b",
            title="Unique",
            content_md="Unique content",
            source="example.com",
            published_at="2026-05-07T12:00:00Z",
            relevance_score=0.95,
        )
        cluster = Cluster(
            primary=primary,
            variants=[],
            cluster_id="cluster-002",
        )
        assert cluster["variants"] == []


class TestSummary:
    """Verify Summary TypedDict."""

    def test_summary_all_fields(self) -> None:
        summary = Summary(
            cluster_id="cluster-001",
            headline="Major AI Breakthrough",
            bullets=["Point 1", "Point 2", "Point 3"],
            why_it_matters="This changes everything",
            sources=["https://example.com/a", "https://other.com/b"],
        )
        assert summary["headline"] == "Major AI Breakthrough"
        assert len(summary["bullets"]) == 3
        assert len(summary["sources"]) == 2


class TestTrend:
    """Verify Trend TypedDict."""

    def test_trend_all_fields(self) -> None:
        trend = Trend(
            name="Open-source LLMs",
            description="Growing trend toward open models",
            evidence_cluster_ids=["cluster-001", "cluster-003"],
        )
        assert trend["name"] == "Open-source LLMs"
        assert len(trend["evidence_cluster_ids"]) == 2


class TestNodeError:
    """Verify NodeError dataclass."""

    def test_node_error_creation(self) -> None:
        err = NodeError(
            node="planner",
            message="LLM connection timeout",
            traceback="Traceback ...",
            timestamp=datetime(2026, 5, 8, 0, 0, 0, tzinfo=UTC),
        )
        assert err.node == "planner"
        assert err.message == "LLM connection timeout"
        assert err.traceback == "Traceback ..."
        assert err.timestamp.tzinfo == UTC

    def test_node_error_auto_timestamp(self) -> None:
        err = NodeError(
            node="filter",
            message="Parse error",
            traceback="",
        )
        assert err.node == "filter"
        # timestamp should be auto-set
        assert err.timestamp is not None
        assert err.timestamp.tzinfo == UTC

    def test_node_error_repr(self) -> None:
        err = NodeError(
            node="scraper",
            message="HTTP 503",
            traceback="",
        )
        assert "scraper" in repr(err)
        assert "HTTP 503" in repr(err)
