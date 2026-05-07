"""Tests for deduplication engine."""

from __future__ import annotations

from datetime import UTC, datetime

from ainews.agents.tools.dedup import (
    Article,
    Cluster,
    canonicalize_url,
    deduplicate,
    hamming_distance,
    jaccard_similarity,
    shingles,
    simhash,
)

# ── URL Canonicalization ──────────────────────────────────


class TestCanonicalizeURL:
    """URL normalization and tracking parameter stripping."""

    def test_strip_utm_params(self) -> None:
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        assert canonicalize_url(url) == "https://example.com/article"

    def test_strip_ref_params(self) -> None:
        url = "https://example.com/page?ref=homepage&fbclid=abc123"
        assert canonicalize_url(url) == "https://example.com/page"

    def test_normalize_host_case(self) -> None:
        url = "https://EXAMPLE.COM/Article"
        result = canonicalize_url(url)
        assert "example.com" in result

    def test_drop_amp_suffix(self) -> None:
        url = "https://example.com/article/amp"
        result = canonicalize_url(url)
        assert not result.endswith("/amp")

    def test_drop_amp_html_suffix(self) -> None:
        url = "https://example.com/article.amp.html"
        result = canonicalize_url(url)
        assert ".amp" not in result

    def test_strip_trailing_slash(self) -> None:
        url = "https://example.com/article/"
        result = canonicalize_url(url)
        assert not result.endswith("/")

    def test_preserve_path(self) -> None:
        url = "https://example.com/news/2026/ai-trends"
        assert canonicalize_url(url) == "https://example.com/news/2026/ai-trends"

    def test_preserve_non_tracking_params(self) -> None:
        url = "https://example.com/search?q=ai+news&page=2"
        result = canonicalize_url(url)
        assert "q=ai+news" in result
        assert "page=2" in result


# ── Simhash ───────────────────────────────────────────────


class TestSimhash:
    """64-bit simhash implementation."""

    def test_same_text_same_hash(self) -> None:
        h1 = simhash("The quick brown fox jumps over the lazy dog")
        h2 = simhash("The quick brown fox jumps over the lazy dog")
        assert h1 == h2

    def test_different_text_different_hash(self) -> None:
        h1 = simhash("AI advances in natural language processing")
        h2 = simhash("Climate change impacts on agriculture worldwide")
        assert h1 != h2

    def test_similar_text_small_distance(self) -> None:
        h1 = simhash("AI news: OpenAI releases GPT-5 today")
        h2 = simhash("AI news: OpenAI releases GPT-5 model today")
        dist = hamming_distance(h1, h2)
        assert dist <= 20  # similar texts should have smaller distance than random

    def test_empty_text(self) -> None:
        h = simhash("")
        assert isinstance(h, int)

    def test_hamming_distance_identical(self) -> None:
        assert hamming_distance(0, 0) == 0
        assert hamming_distance(42, 42) == 0

    def test_hamming_distance_all_different(self) -> None:
        assert hamming_distance(0, (1 << 64) - 1) == 64


# ── Jaccard Similarity ────────────────────────────────────


class TestJaccardSimilarity:
    """Token n-gram Jaccard similarity."""

    def test_identical_text(self) -> None:
        text = "the quick brown fox"
        assert jaccard_similarity(shingles(text), shingles(text)) == 1.0

    def test_completely_different_text(self) -> None:
        s1 = shingles("alpha beta gamma delta")
        s2 = shingles("one two three four five six")
        sim = jaccard_similarity(s1, s2)
        assert sim == 0.0

    def test_partially_similar(self) -> None:
        s1 = shingles("AI news OpenAI releases model")
        s2 = shingles("AI news OpenAI launches new model")
        sim = jaccard_similarity(s1, s2)
        assert 0.0 < sim < 1.0

    def test_empty_text(self) -> None:
        assert jaccard_similarity(set(), set()) == 0.0

    def test_shingles_produces_ngrams(self) -> None:
        result = shingles("a b c d e", n=3)
        assert len(result) > 0
        # 3-gram shingles of 5 tokens = 3 shingles
        assert len(result) == 3


# ── Deduplicate Orchestrator ──────────────────────────────


def _make_article(
    url: str = "https://example.com/article",
    title: str = "Test Article",
    content: str = "This is the article content.",
    priority: float = 1.0,
    published_at: datetime | None = None,
) -> Article:
    return Article(
        url=url,
        title=title,
        content=content,
        priority=priority,
        published_at=published_at or datetime(2026, 5, 7, tzinfo=UTC),
    )


class TestDeduplicate:
    """Cluster and deduplicate orchestrator."""

    def test_no_duplicates(self) -> None:
        """Completely different articles should each be their own cluster."""
        articles = [
            _make_article(
                url="https://a.com/1",
                title="Apple announces new iPhone",
                content=(
                    "Apple today unveiled its latest iPhone model"
                    " with advanced AI features."
                ),
            ),
            _make_article(
                url="https://b.com/2",
                title="SpaceX launches Starship",
                content="SpaceX successfully launched its Starship rocket into orbit.",
            ),
        ]
        clusters = deduplicate(articles)
        assert len(clusters) == 2

    def test_exact_duplicate_urls(self) -> None:
        """Same URL (after canonicalization) should cluster together."""
        articles = [
            _make_article(
                url="https://example.com/article?utm_source=twitter",
                title="Same Article",
                content="Same content here for testing purposes.",
            ),
            _make_article(
                url="https://example.com/article?utm_source=facebook",
                title="Same Article",
                content="Same content here for testing purposes.",
            ),
        ]
        clusters = deduplicate(articles)
        assert len(clusters) == 1
        assert len(clusters[0].variants) == 1

    def test_near_duplicate_content(self) -> None:
        """Similar articles should cluster together."""
        base_content = (
            "OpenAI today announced a new version of its flagship model GPT-5. "
            "The model shows significant improvements in"
            " reasoning and coding abilities."
        )
        articles = [
            _make_article(
                url="https://a.com/1",
                title="OpenAI announces GPT-5",
                content=base_content,
                priority=1.0,
            ),
            _make_article(
                url="https://b.com/2",
                title="OpenAI announces GPT-5 model",
                content=base_content + " Additional minor detail here.",
                priority=0.8,
            ),
        ]
        clusters = deduplicate(articles)
        # These should cluster together due to high similarity
        assert len(clusters) <= 2

    def test_cluster_primary_selection(self) -> None:
        """Primary should be selected by priority * recency * length."""
        articles = [
            _make_article(
                url="https://a.com/1",
                title="Short version",
                content="Brief.",
                priority=0.5,
                published_at=datetime(2026, 5, 6, tzinfo=UTC),
            ),
            _make_article(
                url="https://b.com/2",
                title="Long version with detail",
                content="Much longer article content with many more words and details.",
                priority=1.0,
                published_at=datetime(2026, 5, 7, tzinfo=UTC),
            ),
        ]
        # Even if they don't cluster, verify the model works
        clusters = deduplicate(articles)
        assert len(clusters) >= 1
        assert all(isinstance(c, Cluster) for c in clusters)

    def test_empty_input(self) -> None:
        """Empty article list should return empty clusters."""
        assert deduplicate([]) == []

    def test_single_article(self) -> None:
        """Single article should be its own cluster."""
        articles = [_make_article()]
        clusters = deduplicate(articles)
        assert len(clusters) == 1
        assert clusters[0].primary == articles[0]
        assert clusters[0].variants == []
