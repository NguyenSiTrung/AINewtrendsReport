"""Synthesizer node — per-cluster LLM summarization via Send() fan-out.

Uses ``Send()`` to dispatch one ``synthesize_one`` invocation per cluster.
Each sub-invocation calls the LLM with the ``synthesizer.j2`` prompt.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog

from ainews.llm.concurrency import limited_invoke_sync
from ainews.agents.prompts.loader import load_prompt
from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import GraphState, Summary

logger = structlog.get_logger(__name__)


def _get_llm() -> Any:
    """Lazy-load LLM client from factory."""
    from ainews.llm.factory import get_default_llm

    return get_default_llm()


def synthesize_dispatch(state: GraphState) -> list[Any]:
    """Dispatch Send() for each cluster.

    Returns a list of ``Send("synthesize_one", {...})`` objects.
    """
    from langgraph.types import Send

    clusters = state.get("clusters", [])
    logger.info("synthesizer_dispatch", cluster_count=len(clusters))

    sends = []
    for cluster in clusters:
        sends.append(
            Send(
                "synthesize_one",
                {
                    "cluster": cluster,
                },
            )
        )
    return sends


def _parse_summary_response(text: str) -> dict[str, Any] | None:
    """Parse LLM summary response JSON."""
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


@node_resilient("synthesize_one")
def synthesize_one(state: dict[str, Any]) -> dict[str, Any]:
    """Summarize a single cluster of articles.

    This is a sub-node invoked via Send().
    """
    start = time.time()
    cluster = state["cluster"]
    cluster_id: str = cluster["cluster_id"]

    # Build articles list for prompt
    all_articles = [cluster["primary"], *cluster.get("variants", [])]

    prompt = load_prompt("synthesizer", articles=all_articles)

    llm = _get_llm()
    response = limited_invoke_sync(llm, prompt)
    parsed = _parse_summary_response(response.content)

    if parsed:
        summary = Summary(
            cluster_id=cluster_id,
            headline=parsed.get("headline", "Untitled"),
            bullets=parsed.get("bullets", []),
            why_it_matters=parsed.get("why_it_matters", ""),
            sources=parsed.get("sources", [a["url"] for a in all_articles]),
        )
    else:
        # Fallback summary
        summary = Summary(
            cluster_id=cluster_id,
            headline=cluster["primary"]["title"],
            bullets=["See source articles for details."],
            why_it_matters="",
            sources=[a["url"] for a in all_articles],
        )

    return {
        "summaries": [summary],
        "metrics": track_metrics(
            "synthesize_one",
            state,
            start_time=start,
        ),
    }
