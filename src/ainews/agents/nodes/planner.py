"""Planner node — generates search queries from run parameters.

Calls the LLM via ``llm_factory()`` with the ``planner.j2`` prompt
to convert ``params`` (timeframe, topics, sites) into a list of
Tavily search queries.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog

from ainews.agents.prompts.loader import load_prompt
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


def _extract_json_array(text: str) -> list[str] | None:
    """Extract a JSON array from LLM output.

    Handles both raw JSON and ```json fenced blocks.
    """
    # Try to extract from markdown code fence
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(q) for q in parsed if isinstance(q, str)]
    except json.JSONDecodeError:
        pass

    return None


@node_resilient("planner")
def planner_node(state: GraphState) -> dict[str, Any]:
    """Generate search queries from run parameters.

    Parameters
    ----------
    state
        Current graph state with ``params`` containing topics, sites,
        and timeframe.

    Returns
    -------
    dict
        Partial state update with ``queries`` list and ``metrics``.
    """
    start = time.time()
    params = state["params"]

    use_smart_planner = params.get("use_smart_planner", True)
    if not use_smart_planner:
        queries = list(params["topics"])
        logger.info("planner_bypassed_using_exact_topics", query_count=len(queries))
        return {
            "queries": queries,
            "metrics": track_metrics("planner", state, start_time=start),
        }

    prompt = load_prompt(
        "planner",
        topics=params["topics"],
        sites=params["sites"],
        timeframe_days=params["timeframe_days"],
    )

    llm = _get_llm()
    response = llm.invoke(prompt)
    raw_content: str = response.content

    queries = _extract_json_array(raw_content)

    if queries is None:
        # Fallback: generate basic queries from topics
        logger.warning("planner_json_parse_failed", raw=raw_content[:200])
        queries = [f"latest {topic} news" for topic in params["topics"]]

    logger.info("planner_complete", query_count=len(queries))

    return {
        "queries": queries,
        "metrics": track_metrics("planner", state, start_time=start),
    }
