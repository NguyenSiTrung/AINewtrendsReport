"""Scraper node — enriches raw results with full article content.

Content acquisition follows a 3-tier fallback strategy:

1. **Tavily raw_content** — already returned by ``include_raw_content=True``
   in the Search API call.  Zero extra cost.
2. **Tavily Extract API** — cloud-based extraction via ``TavilySearchTool.extract()``.
   Works behind firewalls that block direct outbound HTTP.
3. **Direct HTTP + trafilatura** — local async scraper as last resort.

Each article is tagged with a ``content_method`` label for debugging.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import Article, GraphState

logger = structlog.get_logger(__name__)

_MIN_CONTENT_LENGTH = 200  # Characters below which we attempt enrichment


# ── Content method labels ─────────────────────────────────

CONTENT_METHOD_TAVILY_RAW = "tavily_raw_content"
CONTENT_METHOD_TAVILY_EXTRACT = "tavily_extract_api"
CONTENT_METHOD_DIRECT_SCRAPE = "direct_scrape"
CONTENT_METHOD_TAVILY_SNIPPET = "tavily_snippet"
CONTENT_METHOD_FAILED = "none"


@node_resilient("scraper")
def scraper_node(state: GraphState) -> dict[str, Any]:
    """Scrape full content for articles with short/missing content.

    Uses a 3-tier fallback: Tavily raw_content → Tavily Extract API
    → direct HTTP scrape.  Logs which method succeeded for each URL.

    Parameters
    ----------
    state
        Current graph state with ``raw_results`` from Retriever.

    Returns
    -------
    dict
        Partial state with ``fetched_articles``.
    """
    start = time.time()
    raw_results = state.get("raw_results", [])
    articles: list[Article] = []

    # Counters for the summary log
    method_counts: dict[str, int] = {
        CONTENT_METHOD_TAVILY_RAW: 0,
        CONTENT_METHOD_TAVILY_EXTRACT: 0,
        CONTENT_METHOD_DIRECT_SCRAPE: 0,
        CONTENT_METHOD_TAVILY_SNIPPET: 0,
        CONTENT_METHOD_FAILED: 0,
    }

    for hit in raw_results:
        url = hit["url"]
        title = hit.get("title", "")
        content, method = _resolve_content(hit)

        method_counts[method] = method_counts.get(method, 0) + 1

        logger.info(
            "scraper_source_resolved",
            url=url,
            title=title[:80],
            content_method=method,
            content_length=len(content),
        )

        articles.append(
            Article(
                url=url,
                title=title,
                content_md=content,
                source=_extract_domain(url),
                published_at="",  # Will be enriched later if available
                relevance_score=hit.get("score", 0.0),
            )
        )

    logger.info(
        "scraper_complete",
        input_count=len(raw_results),
        output_count=len(articles),
        method_breakdown=method_counts,
    )

    return {
        "fetched_articles": articles,
        "metrics": track_metrics("scraper", state, start_time=start),
    }


# ── 3-Tier Content Resolution ────────────────────────────


def _resolve_content(hit: dict[str, Any]) -> tuple[str, str]:
    """Resolve full content for a search hit using 3-tier fallback.

    Returns
    -------
    tuple[str, str]
        ``(content_text, method_label)`` where ``method_label`` is one
        of the ``CONTENT_METHOD_*`` constants.
    """
    url = hit["url"]

    # ── Tier 1: Tavily raw_content (already in search response) ───
    raw_content = hit.get("raw_content") or ""
    if len(raw_content) >= _MIN_CONTENT_LENGTH:
        return raw_content, CONTENT_METHOD_TAVILY_RAW

    # ── Tier 2: Tavily Extract API (cloud-based, firewall-safe) ───
    extracted = _extract_via_tavily(url)
    if extracted and len(extracted) >= _MIN_CONTENT_LENGTH:
        return extracted, CONTENT_METHOD_TAVILY_EXTRACT

    # ── Tier 3: Direct HTTP + trafilatura (last resort) ───────────
    scraped = _scrape_url_direct(url)
    if scraped and len(scraped) >= _MIN_CONTENT_LENGTH:
        return scraped, CONTENT_METHOD_DIRECT_SCRAPE

    # ── Fallback: use whatever snippet Tavily gave us ─────────────
    snippet = hit.get("content", "")
    if snippet:
        return snippet, CONTENT_METHOD_TAVILY_SNIPPET

    return "", CONTENT_METHOD_FAILED


# ── Tier 2: Tavily Extract ───────────────────────────────


def _extract_via_tavily(url: str) -> str | None:
    """Extract content via Tavily Extract API."""
    try:
        from ainews.agents.tools.tavily_search import TavilySearchTool
        from ainews.core.config import get_settings

        settings = get_settings()
        if not settings.tavily_api_key:
            return None

        tool = TavilySearchTool(api_key=settings.tavily_api_key)
        result = tool.extract(url)

        if result:
            logger.debug(
                "tavily_extract_success",
                url=url,
                content_length=len(result),
            )
        return result

    except Exception as exc:
        logger.warning(
            "tavily_extract_fallback_error",
            url=url,
            error=str(exc),
        )
        return None


# ── Tier 3: Direct HTTP scrape ───────────────────────────


def _scrape_url_direct(url: str) -> str | None:
    """Scrape a single URL using the async httpx + trafilatura scraper."""
    try:
        from ainews.agents.tools.scraper import Scraper

        scraper = Scraper()
        result = _run_async(scraper.scrape(url))
        if result:
            logger.debug(
                "direct_scrape_success",
                url=url,
                content_length=result.word_count,
            )
            return result.content_md
    except Exception as exc:
        logger.warning(
            "direct_scrape_error",
            url=url,
            error=str(exc),
        )
    return None


# ── Async helper ─────────────────────────────────────────


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from sync code, handling existing event loops.

    - If no event loop is running, falls back to ``asyncio.run()``.
    - If an event loop *is* running (e.g. inside Celery with
      eventlet/gevent or Jupyter), creates a new thread to run the
      coroutine to avoid 'RuntimeError: cannot run loop while another
      loop is running'.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)

    # Loop is running — spin up a temporary thread
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result(timeout=30)


# ── Utilities ────────────────────────────────────────────


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.netloc or ""
