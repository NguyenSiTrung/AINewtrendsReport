"""LangGraph pipeline assembly.

Wires all 8 node functions + 2 Send() sub-nodes into a ``StateGraph``,
adds conditional edges for retry and degradation routing, and
optionally integrates a ``SqliteSaver`` checkpointer.
"""

from __future__ import annotations

from typing import Any

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from ainews.agents.nodes.dedup import dedup_node
from ainews.agents.nodes.filter import filter_node, filter_router
from ainews.agents.nodes.planner import planner_node
from ainews.agents.nodes.retriever import retrieve_dispatch, retrieve_one
from ainews.agents.nodes.scraper import scraper_node
from ainews.agents.nodes.synthesizer import synthesize_one
from ainews.agents.nodes.trender import trender_node
from ainews.agents.nodes.writer import writer_node
from ainews.agents.resilience import should_degrade
from ainews.agents.state import GraphState

logger = structlog.get_logger(__name__)


def _post_dedup_router(
    state: GraphState,
) -> list[Send] | str:
    """Route after Dedup: fan-out to Synthesizer or skip to Writer.

    If no clusters are produced (empty results), route directly
    to Writer to produce a degraded report.
    If errors exceed threshold, also route to Writer.
    """
    clusters = state.get("clusters", [])

    if not clusters or should_degrade(state, error_threshold=3):
        logger.warning(
            "dedup_skip_to_writer",
            cluster_count=len(clusters),
            error_count=len(state.get("errors", [])),
        )
        return "writer"

    # Fan-out: one Send per cluster
    sends = []
    for cluster in clusters:
        sends.append(Send("synthesize_one", {"cluster": cluster}))
    return sends


def _post_synthesizer_router(state: GraphState) -> str:
    """Route after Synthesizer: degrade to Writer or continue to Trender.

    If the error threshold is exceeded, skip Trender and go directly
    to Writer with whatever data is available.
    """
    if should_degrade(state, error_threshold=3):
        logger.warning(
            "degrade_path",
            error_count=len(state.get("errors", [])),
        )
        return "writer"
    return "trender"


def build_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Build and compile the LangGraph pipeline.

    Parameters
    ----------
    checkpointer
        Optional checkpointer for state persistence (e.g. ``SqliteSaver``).
        Pass ``None`` for in-memory execution without checkpointing.

    Returns
    -------
    CompiledStateGraph
        A compiled graph ready for ``graph.invoke(state)``.
    """
    builder = StateGraph(GraphState)

    # ── Register nodes ───────────────────────────────
    builder.add_node("planner", planner_node)  # type: ignore[call-overload]
    builder.add_node("retrieve_one", retrieve_one)  # type: ignore[call-overload]
    builder.add_node("scraper", scraper_node)  # type: ignore[call-overload]
    builder.add_node("filter", filter_node)  # type: ignore[call-overload]
    builder.add_node("dedup", dedup_node)  # type: ignore[call-overload]
    builder.add_node("synthesize_one", synthesize_one)  # type: ignore[call-overload]
    builder.add_node("trender", trender_node)  # type: ignore[call-overload]
    builder.add_node("writer", writer_node)  # type: ignore[call-overload]

    # ── Linear edges ─────────────────────────────────
    builder.add_edge(START, "planner")

    # Planner → fan-out to Retriever sub-nodes
    builder.add_conditional_edges(
        "planner",
        retrieve_dispatch,
        ["retrieve_one"],
    )

    # Retriever fan-in → Scraper
    builder.add_edge("retrieve_one", "scraper")

    # Scraper → Filter
    builder.add_edge("scraper", "filter")

    # Filter → conditional: retry (→ planner) or proceed (→ dedup)
    builder.add_conditional_edges(
        "filter",
        filter_router,
        {"planner": "planner", "dedup": "dedup"},
    )

    # Dedup → conditional: fan-out to Synthesizer or skip to Writer
    builder.add_conditional_edges(
        "dedup",
        _post_dedup_router,
        ["synthesize_one", "writer"],
    )

    # Synthesizer fan-in → conditional: degrade or trender
    builder.add_conditional_edges(
        "synthesize_one",
        _post_synthesizer_router,
        {"trender": "trender", "writer": "writer"},
    )

    # Trender → Writer
    builder.add_edge("trender", "writer")

    # Writer → END
    builder.add_edge("writer", END)

    # ── Compile ──────────────────────────────────────
    compiled = builder.compile(checkpointer=checkpointer)

    logger.info(
        "graph_compiled",
        node_count=len(compiled.nodes),
        has_checkpointer=checkpointer is not None,
    )

    return compiled
