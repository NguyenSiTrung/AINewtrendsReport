"""Error resilience utilities for graph nodes.

Provides 5 layers of error resilience:
1. **Tenacity retries** — exponential backoff on transient errors.
2. **Node-level try/except** — ``@node_resilient`` decorator.
3. **Graceful skip** — partial results on Send() failures.
4. **Degrade path** — ``should_degrade()`` to route to Writer early.
5. **Per-node metrics** — ``track_metrics()`` for observability.
"""

from __future__ import annotations

import contextvars
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ainews.agents.state import GraphState, NodeError

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# ── Layer 1: Tenacity retries ────────────────────────────


def with_retries(
    max_attempts: int = 3,
    wait_seconds: float = 2.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Wrap a function with exponential-backoff retries.

    Retries on ``ConnectionError``, ``TimeoutError``, and ``OSError``.

    Parameters
    ----------
    max_attempts
        Maximum number of attempts (default 3).
    wait_seconds
        Base wait time in seconds (doubles each attempt).
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_seconds, min=wait_seconds),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
            reraise=True,
        )
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ── Layer 2: Node-level try/except ───────────────────────


def node_resilient(
    node_name: str,
) -> Callable[
    [Callable[[Any], dict[str, Any]]],
    Callable[[Any], dict[str, Any]],
]:
    """Decorator that wraps a node function with error handling.

    On exception, appends a ``NodeError`` to ``state["errors"]`` and
    returns a partial state update instead of crashing the graph.

    Accepts both ``GraphState`` and ``dict[str, Any]`` state arguments
    to support both full nodes and ``Send()`` sub-nodes.

    Also logs node start/end/error events to the ``run_logs`` table
    via ``log_to_db()`` for real-time progress tracking.

    Parameters
    ----------
    node_name
        Human-readable name of the node (for error reporting).
    """

    def decorator(
        func: Callable[[Any], dict[str, Any]],
    ) -> Callable[[Any], dict[str, Any]]:
        @wraps(func)
        def wrapper(state: Any) -> dict[str, Any]:
            start = time.time()
            run_id = _extract_run_id(state)
            engine = _get_logging_engine()

            # Log node start
            if engine is not None and run_id:
                start_detail = _summarize_node_input(node_name, state)
                _safe_log(
                    engine,
                    run_id,
                    node_name,
                    "INFO",
                    start_detail,
                )

            try:
                result = func(state)
                # Auto-track metrics if not already present
                if "metrics" not in result:
                    result["metrics"] = track_metrics(
                        node_name, state, start_time=start
                    )

                # Log node completion with rich summary
                if engine is not None and run_id:
                    elapsed = round(time.time() - start, 2)
                    summary, stats = _summarize_node_result(
                        node_name,
                        result,
                        state,
                    )
                    payload: dict[str, Any] = {"wall_seconds": elapsed}
                    if stats:
                        payload.update(stats)
                    _safe_log(
                        engine,
                        run_id,
                        node_name,
                        "INFO",
                        f"Completed in {elapsed}s — {summary}",
                        payload=payload,
                    )

                return result
            except Exception as exc:
                tb = traceback.format_exc()
                error = NodeError(
                    node=node_name,
                    message=str(exc),
                    traceback=tb,
                    timestamp=datetime.now(tz=UTC),
                )
                logger.error(
                    "node_error",
                    node=node_name,
                    error=str(exc),
                )

                # Log node failure
                if engine is not None and run_id:
                    _safe_log(
                        engine,
                        run_id,
                        node_name,
                        "ERROR",
                        f"Node failed: {exc}",
                    )

                return {
                    "errors": [error],
                    "metrics": track_metrics(node_name, state, start_time=start),
                }

        return wrapper

    return decorator


# ── Logging helpers for node_resilient ───────────────────

_UNSET = object()  # sentinel to distinguish "not yet tried" from "tried and failed"
_logging_engine_var: contextvars.ContextVar[Any] = contextvars.ContextVar(
    "_logging_engine", default=_UNSET
)


def _get_logging_engine() -> Any:
    """Lazily resolve the DB engine for run logging.

    Returns ``None`` if engine cannot be created (e.g., during tests
    without a configured database).  Uses a sentinel so we only
    attempt engine creation once per context (task / thread).

    Uses ``contextvars.ContextVar`` so concurrent Celery tasks in the
    same process each get an isolated engine reference.
    """
    cached = _logging_engine_var.get()
    if cached is not _UNSET:
        return cached
    try:
        from ainews.core.config import get_settings
        from ainews.core.database import create_engine as _create

        settings = get_settings()
        engine = _create(settings.database_url)
        _logging_engine_var.set(engine)
        logger.debug("logging_engine_created", url=settings.database_url)
        return engine
    except Exception:
        logger.warning("logging_engine_unavailable", exc_info=True)
        _logging_engine_var.set(None)
        return None


def set_logging_engine(engine: Any) -> None:
    """Inject a pre-built engine for run logging.

    Called by the Celery task before invoking the graph, so that
    ``@node_resilient`` nodes share the task's DB engine instead of
    trying to create one from scratch (which may fail if env vars
    are not forwarded to the worker).

    Uses ``contextvars.ContextVar`` so concurrent tasks each get
    their own isolated reference.
    """
    _logging_engine_var.set(engine)


def _extract_run_id(state: Any) -> str | None:
    """Extract run_id from a GraphState or dict."""
    if isinstance(state, dict):
        return state.get("run_id")
    return None


def _summarize_node_input(node_name: str, state: Any) -> str:
    """Build a human-readable start message from node input state.

    Extracts context from the *incoming* state to show what data
    the node will process (e.g. article count, query count).
    """
    if not isinstance(state, dict):
        return "Started"

    try:
        if node_name == "planner":
            topics = state.get("topics") or []
            if topics:
                return f"Planning queries for {len(topics)} topic(s)"
            return "Planning search queries"

        if node_name in ("retriever", "retrieve_one"):
            queries = state.get("queries") or []
            query = state.get("query", "")
            if query:
                return f"Searching: {query}"
            return f"Dispatching {len(queries)} search(es)"

        if node_name == "scraper":
            articles = state.get("raw_results") or []
            return f"Scraping {len(articles)} raw result(s)"

        if node_name == "filter":
            articles = state.get("fetched_articles") or []
            return f"Filtering {len(articles)} article(s) by relevance"

        if node_name == "dedup":
            articles = state.get("filtered_articles") or []
            return f"Deduplicating {len(articles)} article(s)"

        if node_name in ("synthesizer", "synthesize_one"):
            cluster = state.get("cluster")
            if cluster and hasattr(cluster, "primary"):
                title = getattr(cluster.primary, "title", "")
                if title:
                    short = title[:60] + ("…" if len(title) > 60 else "")
                    return f"Summarizing: {short}"
            clusters = state.get("clusters") or []
            return f"Dispatching {len(clusters)} cluster(s) for synthesis"

        if node_name == "trender":
            summaries = state.get("summaries") or []
            return f"Identifying trends across {len(summaries)} summaries"

        if node_name == "writer":
            summaries = state.get("summaries") or []
            trends = state.get("trends") or []
            return f"Writing report — {len(summaries)} stories, {len(trends)} trend(s)"

        if node_name == "exporter":
            return "Exporting report to Markdown & Excel"

    except Exception:
        pass  # Fall through to default

    return "Started"


def _summarize_node_result(
    node_name: str,
    result: dict[str, Any],
    state: Any,
) -> tuple[str, dict[str, Any]]:
    """Build a human-readable completion summary from node output.

    Returns
    -------
    (message, stats_dict)
        message: string like "15 clusters, 5 removed"
        stats_dict: JSON-serializable dict for the payload column
    """
    stats: dict[str, Any] = {}

    try:
        if node_name == "planner":
            queries = result.get("queries") or []
            stats["query_count"] = len(queries)
            return f"{len(queries)} search queries generated", stats

        if node_name in ("retriever", "retrieve_one"):
            raw = result.get("raw_results") or []
            query = (state or {}).get("query", "") if isinstance(state, dict) else ""
            stats["hit_count"] = len(raw)
            if query:
                stats["query"] = query
                return f"{len(raw)} results for '{query}'", stats
            return f"{len(raw)} raw result(s) collected", stats

        if node_name == "scraper":
            raw = result.get("fetched_articles") or []
            stats["output_count"] = len(raw)
            return f"{len(raw)} article(s) scraped", stats

        if node_name == "filter":
            kept = result.get("filtered_articles") or []
            input_c = (
                len((state or {}).get("fetched_articles", []))
                if isinstance(state, dict)
                else 0
            )
            removed = max(0, input_c - len(kept))
            stats["kept"] = len(kept)
            stats["removed"] = removed
            return f"{len(kept)} kept, {removed} removed", stats

        if node_name == "dedup":
            clusters = result.get("clusters") or []
            input_c = (
                len((state or {}).get("filtered_articles", []))
                if isinstance(state, dict)
                else 0
            )
            removed = max(0, input_c - len(clusters))
            stats["cluster_count"] = len(clusters)
            stats["deduped"] = removed
            return f"{len(clusters)} clusters, {removed} duplicate(s) removed", stats

        if node_name in ("synthesizer", "synthesize_one"):
            summaries = result.get("summaries") or []
            if summaries and len(summaries) == 1:
                title = (
                    summaries[0].get("title", "")
                    if isinstance(summaries[0], dict)
                    else ""
                )
                if title:
                    short = title[:50] + ("…" if len(title) > 50 else "")
                    stats["title"] = short
                    return f"Summary ready: {short}", stats
            stats["summary_count"] = len(summaries)
            return f"{len(summaries)} summary(ies) generated", stats

        if node_name == "trender":
            trends = result.get("trends") or []
            stats["trend_count"] = len(trends)
            return f"{len(trends)} trend(s) identified", stats

        if node_name == "writer":
            report = result.get("report_md") or ""
            stats["report_length"] = len(report)
            word_count = len(report.split()) if report else 0
            stats["word_count"] = word_count
            return f"Report drafted ({word_count:,} words)", stats

        if node_name == "exporter":
            return "Reports exported successfully", stats

    except Exception:
        pass  # Fall through to default

    return "done", stats


def _safe_log(
    engine: Any,
    run_id: str,
    node: str,
    level: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Call log_to_db without ever raising."""
    try:
        from ainews.services.run_logger import log_to_db

        log_to_db(
            engine,
            run_id,
            node,
            level,
            message,
            payload=payload,
        )
    except Exception:
        pass  # Never crash a node for logging


# ── Layer 4: Degrade path ────────────────────────────────


def should_degrade(state: GraphState, error_threshold: int = 3) -> bool:
    """Check if the pipeline should degrade to partial output.

    Parameters
    ----------
    state
        Current graph state.
    error_threshold
        Number of errors that triggers degradation.

    Returns
    -------
    bool
        ``True`` if error count >= threshold.
    """
    return len(state["errors"]) >= error_threshold


# ── Layer 5: Per-node metrics ────────────────────────────


def track_metrics(
    node_name: str,
    state: dict[str, Any] | GraphState,
    start_time: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> dict[str, dict[str, Any]]:
    """Record per-node execution metrics.

    Parameters
    ----------
    node_name
        Name of the node.
    state
        Current graph state (for existing metrics context).
    start_time
        ``time.time()`` value from when the node started.
    input_tokens
        Number of input tokens consumed (0 for non-LLM nodes).
    output_tokens
        Number of output tokens generated (0 for non-LLM nodes).

    Returns
    -------
    dict
        Metrics dict keyed by node name, suitable for merging into state.
    """
    wall_seconds = time.time() - start_time
    return {
        node_name: {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "wall_seconds": round(wall_seconds, 3),
        }
    }
