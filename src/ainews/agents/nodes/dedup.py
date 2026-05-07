"""Dedup node — wraps the Phase 2 deduplication engine.

Transforms ``filtered_articles`` (GraphState Article TypedDicts) into
the dedup engine's Article model, clusters them, and converts back
to GraphState Cluster TypedDicts.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import Article, Cluster, GraphState

logger = structlog.get_logger(__name__)


@node_resilient("dedup")
def dedup_node(state: GraphState) -> dict[str, Any]:
    """Deduplicate filtered articles into clusters.

    Parameters
    ----------
    state
        Current graph state with ``filtered_articles``.

    Returns
    -------
    dict
        Partial state with ``clusters``.
    """
    start = time.time()
    filtered = state.get("filtered_articles", [])

    if not filtered:
        return {
            "clusters": [],
            "metrics": track_metrics("dedup", state, start_time=start),
        }

    # Convert GraphState Articles to dedup engine Articles
    from ainews.agents.tools.dedup import Article as DedupArticle
    from ainews.agents.tools.dedup import deduplicate

    dedup_articles = []
    for article in filtered:
        published_str = article.get("published_at", "")
        try:
            published = (
                datetime.fromisoformat(published_str)
                if published_str
                else datetime.now(tz=UTC)
            )
        except ValueError:
            published = datetime.now(tz=UTC)

        dedup_articles.append(
            DedupArticle(
                url=article["url"],
                title=article["title"],
                content=article["content_md"],
                priority=article.get("relevance_score", 1.0),
                published_at=published,
            )
        )

    # Run dedup
    raw_clusters = deduplicate(dedup_articles)

    # Convert back to GraphState Cluster TypedDicts
    clusters: list[Cluster] = []
    for raw_cluster in raw_clusters:
        cluster_id = f"cluster-{uuid.uuid4().hex[:8]}"
        primary = _dedup_article_to_state(raw_cluster.primary)
        variants = [_dedup_article_to_state(v) for v in raw_cluster.variants]
        clusters.append(
            Cluster(
                primary=primary,
                variants=variants,
                cluster_id=cluster_id,
            )
        )

    logger.info(
        "dedup_complete",
        input_count=len(filtered),
        cluster_count=len(clusters),
    )

    return {
        "clusters": clusters,
        "metrics": track_metrics("dedup", state, start_time=start),
    }


def _dedup_article_to_state(
    dedup_article: Any,
) -> Article:
    """Convert a dedup engine Article to a GraphState Article."""
    return Article(
        url=dedup_article.url,
        title=dedup_article.title,
        content_md=dedup_article.content,
        source=_extract_domain(dedup_article.url),
        published_at=dedup_article.published_at.isoformat(),
        relevance_score=dedup_article.priority,
    )


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse

    return urlparse(url).netloc or ""
