"""Retriever node — fan-out search via Send() parallelism.

Uses ``Send()`` to dispatch one ``retrieve_one`` invocation per query.
Each sub-invocation calls the Tavily search wrapper and returns
``raw_results`` which are aggregated by LangGraph's reducer.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import GraphState, SearchHit

logger = structlog.get_logger(__name__)


def _get_tavily_tool() -> Any:
    """Lazy-load Tavily search tool."""
    from ainews.agents.tools.tavily_search import TavilySearchTool
    from ainews.core.config import Settings

    settings = Settings()
    return TavilySearchTool(api_key=settings.tavily_api_key)


def retrieve_dispatch(state: GraphState) -> list[Any]:
    """Dispatch Send() for each query in state.

    Returns a list of ``Send("retrieve_one", {...})`` objects for
    LangGraph's conditional edge mechanism.
    """
    from langgraph.types import Send

    queries = state.get("queries", [])
    logger.info("retriever_dispatch", query_count=len(queries))

    sends = []
    for query in queries:
        sends.append(
            Send(
                "retrieve_one",
                {
                    "query": query,
                    "sites": state["params"].get("sites", []),
                    "timeframe_days": state["params"]["timeframe_days"],
                },
            )
        )
    return sends


@node_resilient("retrieve_one")
def retrieve_one(state: dict[str, Any]) -> dict[str, Any]:
    """Execute a single Tavily search for one query.

    This is a sub-node invoked via Send() — receives a minimal
    state dict (not the full GraphState).
    """
    start = time.time()
    query: str = state["query"]
    sites: list[str] = state.get("sites", [])
    timeframe_days: int = state.get("timeframe_days", 7)

    # Map timeframe to Tavily time_range
    time_range = "week" if timeframe_days <= 7 else "month"

    tool = _get_tavily_tool()
    results = tool.search(
        query,
        include_domains=sites if sites else None,
        time_range=time_range,
    )

    # Convert SearchResult to SearchHit TypedDict
    hits: list[SearchHit] = []
    for r in results:
        hits.append(
            SearchHit(
                url=r.url,
                title=r.title,
                content=r.content,
                raw_content=r.raw_content,
                score=r.score,
            )
        )

    logger.info("retrieve_one_complete", query=query, hit_count=len(hits))

    return {
        "raw_results": hits,
        "metrics": track_metrics(
            "retrieve_one",
            state,
            start_time=start,
        ),
    }
