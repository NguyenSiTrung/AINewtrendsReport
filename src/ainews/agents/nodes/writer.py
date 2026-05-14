"""Writer node — assembles final Markdown report.

Uses Jinja2 template for structure and LLM polish for Executive Summary.
"""

from __future__ import annotations

import math
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import structlog

from ainews.llm.concurrency import limited_invoke_sync
from ainews.agents.prompts.loader import load_prompt, render_template
from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import GraphState

logger = structlog.get_logger(__name__)


def _get_llm() -> Any:
    """Lazy-load LLM client from factory."""
    from ainews.llm.factory import get_default_llm

    return get_default_llm()


@node_resilient("writer")
def writer_node(state: GraphState) -> dict[str, Any]:
    """Assemble final Markdown report from summaries and trends.

    Parameters
    ----------
    state
        Current graph state with ``summaries``, ``trends``, and ``errors``.

    Returns
    -------
    dict
        Partial state with ``report_md``.
    """
    start = time.time()
    summaries = state.get("summaries", [])
    trends = state.get("trends", [])
    errors = state.get("errors", [])
    params = state["params"]

    # ── Smart source cap with priority ranking ─────────────
    max_sources = params.get("report_max_sources", 50)
    if max_sources and len(summaries) > max_sources:
        clusters = state.get("clusters", [])
        site_priorities = params.get("site_priorities", {})
        summaries = _rank_and_truncate(
            summaries, clusters, site_priorities, max_sources,
        )

    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Generate executive summary via LLM
    executive_summary = _generate_executive_summary(summaries, trends)

    # Render report via Jinja2 template
    report_md = render_template(
        "report",
        generated_at=now,
        params=params,
        errors=errors,
        executive_summary=executive_summary,
        summaries=summaries,
        trends=trends,
    )

    logger.info(
        "writer_complete",
        report_length=len(report_md),
        summary_count=len(summaries),
        trend_count=len(trends),
    )

    return {
        "report_md": report_md,
        "metrics": track_metrics("writer", state, start_time=start),
    }


def _generate_executive_summary(
    summaries: list[Any],
    trends: list[Any],
) -> str:
    """Generate polished executive summary via LLM.

    Falls back to a simple concatenation if LLM fails.
    """
    if not summaries:
        return "No stories to summarize."

    summaries_text = "\n".join(
        f"- {s.get('headline', 'Untitled')}: " + "; ".join(s.get("bullets", [])[:2])
        for s in summaries
    )
    trends_text = (
        "\n".join(
            f"- {t.get('name', 'Unnamed')}: {t.get('description', '')}" for t in trends
        )
        if trends
        else "No specific trends identified."
    )

    try:
        prompt = load_prompt(
            "writer_executive",
            summaries_text=summaries_text,
            trends_text=trends_text,
        )
        llm = _get_llm()
        response = limited_invoke_sync(llm, prompt)
        executive: str = response.content
        return executive.strip()
    except Exception as exc:
        logger.warning("writer_executive_llm_error", error=str(exc))
        # Fallback
        return (
            "This week's key developments include: "
            + "; ".join(s.get("headline", "") for s in summaries[:5])
            + "."
        )


# ── Smart Ranking ────────────────────────────────────────

# Weight constants for the composite score
_W_RELEVANCE = 0.40
_W_CLUSTER_SIZE = 0.25
_W_RECENCY = 0.20
_W_SITE_PRIORITY = 0.15


def _rank_and_truncate(
    summaries: list[Any],
    clusters: list[Any],
    site_priorities: dict[str, int],
    max_sources: int,
) -> list[Any]:
    """Rank summaries by composite score and keep the top *max_sources*.

    Scoring factors (weights):
      - Relevance (0.40): LLM filter score from the cluster's primary article.
      - Cluster size (0.25): More duplicates = hotter topic (log-scaled).
      - Recency (0.20): Exponential decay — newer articles rank higher.
      - Site priority (0.15): Admin-configured source credibility (1-10).
    """
    # Build cluster lookup by cluster_id
    cluster_map: dict[str, dict[str, Any]] = {
        c["cluster_id"]: c for c in clusters
    }

    scored: list[tuple[float, dict[str, Any]]] = []
    for summary in summaries:
        cluster = cluster_map.get(summary.get("cluster_id", ""))

        # Factor 1: Relevance (0.0–1.0)
        relevance = 0.5
        if cluster:
            relevance = cluster["primary"].get("relevance_score", 0.5)

        # Factor 2: Cluster size bonus (log-scaled, capped at 1.0)
        cluster_size = 1
        if cluster:
            cluster_size = 1 + len(cluster.get("variants", []))
        size_bonus = min(math.log2(1 + cluster_size) / math.log2(11), 1.0)

        # Factor 3: Recency bonus (exponential decay)
        recency = 0.5
        if cluster:
            published_at = cluster["primary"].get("published_at", "")
            if published_at:
                try:
                    pub_dt = datetime.fromisoformat(published_at)
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=UTC)
                    age_hours = max(
                        (datetime.now(tz=UTC) - pub_dt).total_seconds() / 3600, 1,
                    )
                    recency = math.exp(-0.03 * age_hours)
                except (ValueError, TypeError):
                    pass

        # Factor 4: Site priority (best among sources, normalized 0.0–1.0)
        site_prio_normalized = 0.5
        sources = summary.get("sources", [])
        if sources:
            prios = [
                site_priorities.get(_extract_domain(url), 5) for url in sources
            ]
            site_prio_normalized = max(prios) / 10.0

        score = (
            relevance * _W_RELEVANCE
            + size_bonus * _W_CLUSTER_SIZE
            + recency * _W_RECENCY
            + site_prio_normalized * _W_SITE_PRIORITY
        )
        scored.append((score, summary))

    scored.sort(key=lambda x: x[0], reverse=True)

    kept = [s for _, s in scored[:max_sources]]

    logger.info(
        "writer_smart_truncation",
        total=len(summaries),
        kept=max_sources,
        dropped=len(summaries) - max_sources,
        top_score=round(scored[0][0], 3) if scored else 0,
        cutoff_score=(
            round(scored[max_sources - 1][0], 3) if len(scored) >= max_sources else 0
        ),
    )
    return kept


def _extract_domain(url: str) -> str:
    """Extract bare domain from a URL, stripping ``www.`` prefix."""
    return urlparse(url).netloc.removeprefix("www.")
