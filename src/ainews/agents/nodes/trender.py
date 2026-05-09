"""Trender node — identifies cross-cutting trends across summaries.

Single LLM call via ``trender.j2`` across all summaries to extract
3-7 macro trends.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog

from ainews.agents.prompts.loader import load_prompt
from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import GraphState, Trend

logger = structlog.get_logger(__name__)


def _get_llm() -> Any:
    """Lazy-load LLM client from factory."""
    from ainews.core.config import Settings
    from ainews.llm.factory import get_llm, get_llm_config

    settings = Settings()
    config = get_llm_config(settings)
    return get_llm(config)


def _parse_trends_response(text: str) -> list[dict[str, Any]] | None:
    """Parse LLM trends response JSON array."""
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


@node_resilient("trender")
def trender_node(state: GraphState) -> dict[str, Any]:
    """Identify cross-cutting trends from summaries.

    Parameters
    ----------
    state
        Current graph state with ``summaries``.

    Returns
    -------
    dict
        Partial state with ``trends``.
    """
    start = time.time()
    summaries = state.get("summaries", [])

    if not summaries:
        return {
            "trends": [],
            "metrics": track_metrics("trender", state, start_time=start),
        }

    prompt = load_prompt("trender", summaries=summaries)

    llm = _get_llm()
    response = llm.invoke(prompt)
    parsed = _parse_trends_response(response.content)

    trends: list[Trend] = []
    if parsed:
        for item in parsed:
            trends.append(
                Trend(
                    name=item.get("name", "Unnamed Trend"),
                    description=item.get("description", ""),
                    evidence_cluster_ids=[
                        str(cid) for cid in item.get("evidence_cluster_ids", [])
                    ],
                )
            )

    logger.info("trender_complete", trend_count=len(trends))

    return {
        "trends": trends,
        "metrics": track_metrics("trender", state, start_time=start),
    }
