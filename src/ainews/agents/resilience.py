"""Error resilience utilities for graph nodes.

Provides 5 layers of error resilience:
1. **Tenacity retries** — exponential backoff on transient errors.
2. **Node-level try/except** — ``@node_resilient`` decorator.
3. **Graceful skip** — partial results on Send() failures.
4. **Degrade path** — ``should_degrade()`` to route to Writer early.
5. **Per-node metrics** — ``track_metrics()`` for observability.
"""

from __future__ import annotations

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
                _safe_log(
                    engine,
                    run_id,
                    node_name,
                    "INFO",
                    "Node started",
                )

            try:
                result = func(state)
                # Auto-track metrics if not already present
                if "metrics" not in result:
                    result["metrics"] = track_metrics(
                        node_name, state, start_time=start
                    )

                # Log node completion
                if engine is not None and run_id:
                    elapsed = round(time.time() - start, 2)
                    _safe_log(
                        engine,
                        run_id,
                        node_name,
                        "INFO",
                        "Node completed",
                        payload={"wall_seconds": elapsed},
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
_logging_engine_cache: Any = _UNSET


def _get_logging_engine() -> Any:
    """Lazily resolve the DB engine for run logging.

    Returns ``None`` if engine cannot be created (e.g., during tests
    without a configured database).  Uses a sentinel so we only
    attempt engine creation once per process.
    """
    global _logging_engine_cache
    if _logging_engine_cache is not _UNSET:
        return _logging_engine_cache
    try:
        from ainews.core.config import Settings
        from ainews.core.database import create_engine as _create

        settings = Settings()
        _logging_engine_cache = _create(settings.database_url)
        logger.debug("logging_engine_created", url=settings.database_url)
        return _logging_engine_cache
    except Exception:
        logger.warning("logging_engine_unavailable", exc_info=True)
        _logging_engine_cache = None
        return None


def set_logging_engine(engine: Any) -> None:
    """Inject a pre-built engine for run logging.

    Called by the Celery task before invoking the graph, so that
    ``@node_resilient`` nodes share the task's DB engine instead of
    trying to create one from scratch (which may fail if env vars
    are not forwarded to the worker).
    """
    global _logging_engine_cache
    _logging_engine_cache = engine


def _extract_run_id(state: Any) -> str | None:
    """Extract run_id from a GraphState or dict."""
    if isinstance(state, dict):
        return state.get("run_id")
    return None


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
