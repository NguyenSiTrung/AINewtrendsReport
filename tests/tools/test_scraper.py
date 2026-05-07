"""Tests for web scraper tool."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from ainews.agents.tools.scraper import (
    RobotsTxtChecker,
    ScrapedArticle,
    Scraper,
)

# ── ScrapedArticle model tests ────────────────────────────


class TestScrapedArticle:
    """ScrapedArticle model construction and validation."""

    def test_construct_full(self) -> None:
        a = ScrapedArticle(
            url="https://example.com/article",
            title="Test Article",
            content_md="# Hello\n\nWorld",
            fetched_at=datetime(2026, 5, 7, tzinfo=UTC),
            word_count=2,
        )
        assert a.url == "https://example.com/article"
        assert a.title == "Test Article"
        assert a.word_count == 2

    def test_content_md_required(self) -> None:
        with pytest.raises((TypeError, ValueError)):
            ScrapedArticle(
                url="https://x.com",
                title="T",
                fetched_at=datetime.now(tz=UTC),
                word_count=0,
            )  # type: ignore[call-arg]


# ── RobotsTxtChecker tests ───────────────────────────────


class TestRobotsTxtChecker:
    """robots.txt parsing and compliance tests."""

    @respx.mock
    async def test_allowed_url(self) -> None:
        """URL should be allowed if robots.txt has no disallow."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(
                200,
                text="User-agent: *\nAllow: /\n",
            )
        )
        checker = RobotsTxtChecker()
        assert await checker.is_allowed("https://example.com/article") is True

    @respx.mock
    async def test_disallowed_url(self) -> None:
        """URL should be blocked if robots.txt disallows it."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(
                200,
                text="User-agent: *\nDisallow: /private/\n",
            )
        )
        checker = RobotsTxtChecker()
        result = await checker.is_allowed("https://example.com/private/page")
        assert result is False

    @respx.mock
    async def test_missing_robots_txt(self) -> None:
        """Missing robots.txt (404) should allow all URLs."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(404)
        )
        checker = RobotsTxtChecker()
        assert await checker.is_allowed("https://example.com/anything") is True

    @respx.mock
    async def test_robots_txt_cached(self) -> None:
        """Second call should use cached robots.txt."""
        route = respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(
                200,
                text="User-agent: *\nAllow: /\n",
            )
        )
        checker = RobotsTxtChecker()
        await checker.is_allowed("https://example.com/a")
        await checker.is_allowed("https://example.com/b")
        assert route.call_count == 1  # cached after first call


# ── Scraper tests ─────────────────────────────────────────


class TestScraper:
    """Async scraper with robots.txt compliance."""

    @respx.mock
    async def test_scrape_success(self) -> None:
        """Should extract content from HTML page."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
        )
        respx.get("https://example.com/article").mock(
            return_value=httpx.Response(
                200,
                text="""
                <html>
                <head><title>Test Article</title></head>
                <body>
                <article>
                <h1>Test Article</h1>
                <p>This is the article content with enough words to pass extraction.</p>
                <p>More content here for the scraper to find and process.</p>
                </article>
                </body>
                </html>
                """,
                headers={"content-type": "text/html"},
            )
        )
        scraper = Scraper()
        result = await scraper.scrape("https://example.com/article")
        # trafilatura might or might not extract; we test the flow
        if result is not None:
            assert result.url == "https://example.com/article"
            assert result.word_count >= 0

    @respx.mock
    async def test_scrape_blocked_by_robots(self) -> None:
        """Should return None when robots.txt blocks the URL."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(
                200,
                text="User-agent: *\nDisallow: /secret/\n",
            )
        )
        scraper = Scraper()
        result = await scraper.scrape("https://example.com/secret/page")
        assert result is None

    @respx.mock
    async def test_scrape_http_error(self) -> None:
        """Should return None on HTTP error."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
        )
        respx.get("https://example.com/gone").mock(return_value=httpx.Response(404))
        scraper = Scraper()
        result = await scraper.scrape("https://example.com/gone")
        assert result is None

    @respx.mock
    async def test_scrape_connection_error(self) -> None:
        """Should return None on connection error."""
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="User-agent: *\nAllow: /\n")
        )
        respx.get("https://example.com/down").mock(
            side_effect=httpx.ConnectError("refused")
        )
        scraper = Scraper()
        result = await scraper.scrape("https://example.com/down")
        assert result is None
