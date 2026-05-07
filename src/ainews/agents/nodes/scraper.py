"""Scraper node — enriches raw results with full article content.

Iterates ``raw_results`` with missing or short content and calls the
async scraper (Phase 2 tool) to fill in ``content_md``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import Article, GraphState

logger = structlog.get_logger(__name__)

_MIN_CONTENT_LENGTH = 200  # Characters below which we attempt to scrape


@node_resilient("scraper")
def scraper_node(state: GraphState) -> dict[str, Any]:
    """Scrape full content for articles with short/missing content.

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

    for hit in raw_results:
        content = hit.get("raw_content") or hit.get("content", "")

        # If content is short, try to scrape
        if len(content) < _MIN_CONTENT_LENGTH:
            scraped_content = _scrape_url(hit["url"])
            if scraped_content:
                content = scraped_content

        articles.append(
            Article(
                url=hit["url"],
                title=hit["title"],
                content_md=content,
                source=_extract_domain(hit["url"]),
                published_at="",  # Will be enriched later if available
                relevance_score=hit.get("score", 0.0),
            )
        )

    logger.info(
        "scraper_complete",
        input_count=len(raw_results),
        output_count=len(articles),
    )

    return {
        "fetched_articles": articles,
        "metrics": track_metrics("scraper", state, start_time=start),
    }


def _scrape_url(url: str) -> str | None:
    """Scrape a single URL using the async scraper."""
    try:
        from ainews.agents.tools.scraper import Scraper

        scraper = Scraper()
        result = asyncio.run(scraper.scrape(url))
        if result:
            return result.content_md
    except Exception as exc:
        logger.warning("scraper_individual_error", url=url, error=str(exc))
    return None


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.netloc or ""
