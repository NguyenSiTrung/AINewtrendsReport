"""Tests for agents.prompts.loader — Jinja2 prompt template loading."""

from __future__ import annotations

import pytest

from ainews.agents.prompts.loader import load_prompt


class TestLoadPrompt:
    """Verify prompt template loading and variable rendering."""

    def test_load_planner_template(self) -> None:
        """Planner template renders with topics, sites, timeframe."""
        result = load_prompt(
            "planner",
            topics=["AI", "LLM"],
            sites=["techcrunch.com", "arstechnica.com"],
            timeframe_days=7,
        )
        assert "AI" in result
        assert "LLM" in result
        assert "techcrunch.com" in result
        assert "7" in result

    def test_load_filter_template(self) -> None:
        """Filter template renders with article content and topics."""
        result = load_prompt(
            "filter",
            title="Test Article Title",
            content="This is article content about AI models.",
            topics=["AI", "models"],
        )
        assert "Test Article Title" in result
        assert "AI" in result

    def test_load_synthesizer_template(self) -> None:
        """Synthesizer template renders with cluster articles."""
        articles = [
            {"title": "Article 1", "content_md": "Content 1", "url": "https://a.com"},
            {"title": "Article 2", "content_md": "Content 2", "url": "https://b.com"},
        ]
        result = load_prompt("synthesizer", articles=articles)
        assert "Article 1" in result
        assert "Article 2" in result

    def test_load_trender_template(self) -> None:
        """Trender template renders with summaries."""
        summaries = [
            {"headline": "AI Breakthrough", "bullets": ["point1"]},
            {"headline": "New Model", "bullets": ["point2"]},
        ]
        result = load_prompt("trender", summaries=summaries)
        assert "AI Breakthrough" in result
        assert "New Model" in result

    def test_load_writer_executive_template(self) -> None:
        """Writer executive template renders with report content."""
        result = load_prompt(
            "writer_executive",
            summaries_text="Major AI breakthroughs this week...",
            trends_text="Open source models trending...",
        )
        assert "AI breakthroughs" in result

    def test_template_not_found_raises(self) -> None:
        """Loading a non-existent template raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            load_prompt("nonexistent")

    def test_all_templates_exist(self) -> None:
        """All required templates can be loaded (smoke test)."""
        templates = ["planner", "filter", "synthesizer", "trender", "writer_executive"]
        for name in templates:
            # Just verify they load without error (with minimal vars)
            result = load_prompt(
                name,
                topics=[],
                sites=[],
                timeframe_days=1,
                title="",
                content="",
                articles=[],
                summaries=[],
                summaries_text="",
                trends_text="",
            )
            assert isinstance(result, str)
            assert len(result) > 0
