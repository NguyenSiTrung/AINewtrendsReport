"""GraphState TypedDict and supporting types for the LangGraph workflow.

All state flows through ``GraphState`` — nodes are stateless pure functions
that accept ``GraphState`` and return a partial state update ``dict``.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any

from typing_extensions import TypedDict

# ── Supporting TypedDicts ────────────────────────────────


class RunParams(TypedDict):
    """Input parameters for a pipeline run."""

    timeframe_days: int
    topics: list[str]
    sites: list[str]


class SearchHit(TypedDict):
    """A single raw search result from Tavily."""

    url: str
    title: str
    content: str
    raw_content: str | None
    score: float


class Article(TypedDict):
    """An article after scraping / enrichment."""

    url: str
    title: str
    content_md: str
    source: str
    published_at: str
    relevance_score: float


class Cluster(TypedDict):
    """A group of deduplicated articles."""

    primary: Article
    variants: list[Article]
    cluster_id: str


class Summary(TypedDict):
    """LLM-generated summary for one cluster."""

    cluster_id: str
    headline: str
    bullets: list[str]
    why_it_matters: str
    sources: list[str]


class Trend(TypedDict):
    """A cross-cutting trend identified across summaries."""

    name: str
    description: str
    evidence_cluster_ids: list[str]


# ── NodeError ────────────────────────────────────────────


@dataclass
class NodeError:
    """Structured error from a graph node.

    Parameters
    ----------
    node
        Name of the node that raised the error.
    message
        Human-readable error description.
    traceback
        Full traceback string (may be empty).
    timestamp
        When the error occurred (defaults to ``now(UTC)``).
    """

    node: str
    message: str
    traceback: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __repr__(self) -> str:
        return f"NodeError(node={self.node!r}, message={self.message!r})"


def _merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge two metric dicts (b wins on key conflicts)."""
    merged = dict(a)
    merged.update(b)
    return merged


class GraphState(TypedDict):
    """Top-level state flowing through the LangGraph pipeline.

    List fields use ``Annotated[..., operator.add]`` so that partial
    state updates returned by nodes are *appended* rather than replaced.
    ``metrics`` is merged via a custom dict-merge reducer.
    """

    run_id: str
    params: RunParams
    queries: Annotated[list[str], operator.add]
    raw_results: Annotated[list[SearchHit], operator.add]
    fetched_articles: Annotated[list[Article], operator.add]
    filtered_articles: Annotated[list[Article], operator.add]
    clusters: Annotated[list[Cluster], operator.add]
    summaries: Annotated[list[Summary], operator.add]
    trends: Annotated[list[Trend], operator.add]
    report_md: str
    xlsx_path: str
    errors: Annotated[list[NodeError], operator.add]
    metrics: Annotated[dict[str, Any], _merge_dicts]
    loop_count: int
