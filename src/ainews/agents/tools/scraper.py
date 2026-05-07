"""Async web scraper with robots.txt compliance.

Features:
- Async httpx client with configurable User-Agent.
- robots.txt fetch + cache per domain; respects ``Disallow`` rules.
- Content extraction via ``trafilatura.extract()`` (Markdown output).
- Per-domain rate limiting via ``asyncio.Semaphore``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

_DEFAULT_USER_AGENT = "ainews-scraper/0.1"
_DEFAULT_TIMEOUT = 30
_MAX_CONCURRENT_PER_DOMAIN = 2


# ── Models ────────────────────────────────────────────────


class ScrapedArticle(BaseModel):
    """Result of a successful page scrape."""

    url: str
    title: str
    content_md: str
    fetched_at: datetime
    word_count: int


# ── robots.txt Checker ────────────────────────────────────


class RobotsTxtChecker:
    """Async robots.txt fetcher with per-domain caching.

    Parameters
    ----------
    user_agent
        User-Agent string for robots.txt rule matching.
    """

    def __init__(self, user_agent: str = _DEFAULT_USER_AGENT) -> None:
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    async def is_allowed(self, url: str) -> bool:
        """Check if ``url`` is allowed by the domain's robots.txt.

        Missing or errored robots.txt defaults to allow-all.
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._cache:
            await self._fetch_robots(domain)

        parser = self._cache.get(domain)
        if parser is None:
            return True  # no robots.txt → allow

        return parser.can_fetch(self._user_agent, url)

    async def _fetch_robots(self, domain: str) -> None:
        """Fetch and parse robots.txt for a domain."""
        robots_url = f"{domain}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(robots_url)

            if resp.status_code != 200:
                # No robots.txt → allow all
                self._cache[domain] = self._allow_all_parser()
                return

            parser = RobotFileParser()
            parser.parse(resp.text.splitlines())
            self._cache[domain] = parser

        except Exception:
            logger.warning("robots_txt_fetch_error", domain=domain)
            self._cache[domain] = self._allow_all_parser()

    @staticmethod
    def _allow_all_parser() -> RobotFileParser:
        """Create a parser that allows all URLs."""
        parser = RobotFileParser()
        parser.parse(["User-agent: *", "Allow: /"])
        return parser


# ── Scraper ───────────────────────────────────────────────


class Scraper:
    """Async web scraper with robots.txt compliance and content extraction.

    Parameters
    ----------
    user_agent
        User-Agent header for HTTP requests.
    timeout
        Request timeout in seconds.
    robots_checker
        Optional pre-configured robots.txt checker.
    """

    def __init__(
        self,
        user_agent: str = _DEFAULT_USER_AGENT,
        timeout: int = _DEFAULT_TIMEOUT,
        robots_checker: RobotsTxtChecker | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._robots = robots_checker or RobotsTxtChecker(user_agent=user_agent)
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        """Get or create a per-domain rate-limiting semaphore."""
        if domain not in self._domain_semaphores:
            self._domain_semaphores[domain] = asyncio.Semaphore(
                _MAX_CONCURRENT_PER_DOMAIN
            )
        return self._domain_semaphores[domain]

    async def scrape(
        self,
        url: str,
        *,
        js_render: bool = False,
    ) -> ScrapedArticle | None:
        """Scrape a URL and extract content as Markdown.

        Parameters
        ----------
        url
            URL to scrape.
        js_render
            If ``True``, use Playwright for JS rendering (not yet implemented).

        Returns
        -------
        ScrapedArticle | None
            Structured article or ``None`` on failure.
        """
        # Check robots.txt
        if not await self._robots.is_allowed(url):
            logger.info("scrape_blocked_by_robots", url=url)
            return None

        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        semaphore = self._get_semaphore(domain)

        async with semaphore:
            return await self._fetch_and_extract(url)

    async def _fetch_and_extract(self, url: str) -> ScrapedArticle | None:
        """Fetch page content and extract with trafilatura."""
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": self._user_agent},
            ) as client:
                resp = await client.get(url)

            if resp.status_code >= 400:
                logger.warning(
                    "scrape_http_error",
                    url=url,
                    status=resp.status_code,
                )
                return None

            html = resp.text
            return self._extract(url, html)

        except Exception as exc:
            logger.error("scrape_error", url=url, error=str(exc))
            return None

    @staticmethod
    def _extract(url: str, html: str) -> ScrapedArticle | None:
        """Extract content from HTML using trafilatura."""
        import trafilatura

        result = trafilatura.extract(
            html,
            output_format="markdown",
            include_comments=False,
            include_tables=True,
        )

        if result is None:
            logger.info("scrape_no_content", url=url)
            return None

        # Try to extract title from trafilatura metadata
        metadata = trafilatura.extract_metadata(html)
        title = ""
        if metadata and metadata.title:
            title = metadata.title

        word_count = len(result.split())

        return ScrapedArticle(
            url=url,
            title=title,
            content_md=result,
            fetched_at=datetime.now(tz=UTC),
            word_count=word_count,
        )
