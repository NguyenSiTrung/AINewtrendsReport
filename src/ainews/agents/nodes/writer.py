"""Writer node — assembles final Markdown report.

Uses Jinja2 template for structure and LLM polish for Executive Summary.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from ainews.agents.prompts.loader import load_prompt, render_template
from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import GraphState

logger = structlog.get_logger(__name__)


def _get_llm() -> Any:
    """Lazy-load LLM client from factory."""
    from ainews.core.config import get_settings
    from ainews.llm.factory import get_llm, get_llm_config

    settings = get_settings()
    config = get_llm_config(settings)
    return get_llm(config)


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

    # ── Enforce max-sources cap ────────────────────────────
    max_sources = params.get("report_max_sources", 50)
    if max_sources and len(summaries) > max_sources:
        logger.info(
            "writer_truncating_summaries",
            original=len(summaries),
            max_sources=max_sources,
        )
        summaries = summaries[:max_sources]

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
        response = llm.invoke(prompt)
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
