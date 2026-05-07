"""Tests for Tavily search wrapper models and cache."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ainews.agents.tools.tavily_search import CacheBackend, SearchResult


class TestSearchResult:
    """SearchResult model construction and validation."""

    def test_construct_full(self) -> None:
        r = SearchResult(
            url="https://example.com/article",
            title="Test Article",
            content="Summary of the article.",
            raw_content="# Full Markdown\n\nContent here.",
            score=0.95,
        )
        assert r.url == "https://example.com/article"
        assert r.title == "Test Article"
        assert r.score == 0.95

    def test_raw_content_optional(self) -> None:
        r = SearchResult(
            url="https://example.com",
            title="Title",
            content="Content",
            score=0.5,
        )
        assert r.raw_content is None

    def test_score_bounds(self) -> None:
        """Score should be between 0 and 1."""
        r = SearchResult(
            url="https://x.com",
            title="T",
            content="C",
            score=0.0,
        )
        assert r.score == 0.0

        r2 = SearchResult(
            url="https://x.com",
            title="T",
            content="C",
            score=1.0,
        )
        assert r2.score == 1.0

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            SearchResult(url="https://x.com")  # type: ignore[call-arg]


class TestCacheBackendProtocol:
    """CacheBackend protocol should be implementable."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """CacheBackend should be runtime-checkable."""

        class FakeCache:
            def get(self, key: str) -> str | None:
                return None

            def set(self, key: str, value: str, ttl: int) -> None:
                pass

        cache = FakeCache()
        assert isinstance(cache, CacheBackend)

    def test_non_conformant_rejected(self) -> None:
        """Objects without get/set should not be CacheBackend."""

        class NotACache:
            pass

        assert not isinstance(NotACache(), CacheBackend)


class TestTavilySearchTool:
    """TavilySearchTool wrapper with cache integration."""

    def _make_tool(
        self,
        cache: CacheBackend | None = None,
    ) -> TavilySearchTool:  # noqa: F821
        from ainews.agents.tools.tavily_search import TavilySearchTool

        tool = TavilySearchTool.__new__(TavilySearchTool)
        tool._api_key = "test-key"
        tool._cache = cache
        tool._cache_ttl = 21600
        tool._tool = None  # will be replaced by mock
        return tool

    def test_cache_miss_then_hit(self) -> None:
        """First call should miss, second should hit cache."""
        from unittest.mock import MagicMock

        from ainews.agents.tools.cache import InMemoryCache

        cache = InMemoryCache(maxsize=10, default_ttl=3600)
        tool = self._make_tool(cache=cache)

        mock_invoke = MagicMock(
            return_value=[
                {
                    "url": "https://example.com",
                    "title": "Test",
                    "content": "Content",
                    "raw_content": "# Raw",
                    "score": 0.9,
                }
            ]
        )
        tool._tool = MagicMock()
        tool._tool.invoke = mock_invoke

        # First call — cache miss
        results1 = tool.search("AI news")
        assert len(results1) == 1
        assert results1[0].url == "https://example.com"
        assert mock_invoke.call_count == 1

        # Second call — cache hit (invoke not called again)
        results2 = tool.search("AI news")
        assert len(results2) == 1
        assert results2[0].url == "https://example.com"
        assert mock_invoke.call_count == 1  # still 1

    def test_search_without_cache(self) -> None:
        """Search should work without cache."""
        from unittest.mock import MagicMock

        tool = self._make_tool(cache=None)
        mock_invoke = MagicMock(
            return_value=[
                {
                    "url": "https://a.com",
                    "title": "A",
                    "content": "C",
                    "score": 0.5,
                }
            ]
        )
        tool._tool = MagicMock()
        tool._tool.invoke = mock_invoke

        results = tool.search("test query")
        assert len(results) == 1
        assert mock_invoke.call_count == 1

    def test_search_error_returns_empty(self) -> None:
        """Errors from Tavily should return empty list, not raise."""
        from unittest.mock import MagicMock

        tool = self._make_tool()
        tool._tool = MagicMock()
        tool._tool.invoke = MagicMock(side_effect=RuntimeError("API down"))

        results = tool.search("failing query")
        assert results == []

    def test_cache_key_determinism(self) -> None:
        """Same params should produce same cache key."""
        from ainews.agents.tools.tavily_search import TavilySearchTool

        key1 = TavilySearchTool._cache_key("AI", ["a.com"], "day", 10)
        key2 = TavilySearchTool._cache_key("AI", ["a.com"], "day", 10)
        assert key1 == key2

    def test_cache_key_differs_for_different_params(self) -> None:
        """Different params should produce different cache keys."""
        from ainews.agents.tools.tavily_search import TavilySearchTool

        key1 = TavilySearchTool._cache_key("AI", None, None, 10)
        key2 = TavilySearchTool._cache_key("ML", None, None, 10)
        assert key1 != key2

    def test_parse_results_from_list(self) -> None:
        """_parse_results should handle list of dicts."""
        from ainews.agents.tools.tavily_search import TavilySearchTool

        raw = [
            {
                "url": "https://a.com",
                "title": "A",
                "content": "C",
                "score": 0.8,
            }
        ]
        results = TavilySearchTool._parse_results(raw)
        assert len(results) == 1
        assert results[0].title == "A"

    def test_parse_results_from_json_string(self) -> None:
        """_parse_results should handle JSON string."""
        import json

        from ainews.agents.tools.tavily_search import TavilySearchTool

        raw = json.dumps(
            [
                {
                    "url": "https://b.com",
                    "title": "B",
                    "content": "CB",
                    "score": 0.7,
                }
            ]
        )
        results = TavilySearchTool._parse_results(raw)
        assert len(results) == 1
        assert results[0].url == "https://b.com"
