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
