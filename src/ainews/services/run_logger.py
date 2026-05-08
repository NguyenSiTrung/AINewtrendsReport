"""Run logger service — log_to_db() helper.

Provides ``log_to_db()`` which creates a ``RunLog`` row in its own
short-lived session, independent of any ongoing graph state transaction.
Errors are suppressed so logging never crashes pipeline nodes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import Engine

from ainews.core.database import make_session_factory
from ainews.models.run_log import RunLog

logger = structlog.get_logger(__name__)


def log_to_db(
    engine: Engine,
    run_id: str,
    node: str,
    level: str,
    message: str,
    *,
    payload: dict[str, Any] | None = None,
) -> None:
    """Create a RunLog row in its own short-lived session.

    Uses a fresh session from the engine so that DB writes are independent
    of the caller's transaction. All exceptions are caught and logged —
    the helper must never crash a pipeline node.

    Parameters
    ----------
    engine:
        SQLAlchemy engine to use for the session.
    run_id:
        The UUID of the run this log belongs to.
    node:
        Name of the pipeline node (e.g., ``"planner"``, ``"retriever"``).
    level:
        Log level string (``"INFO"``, ``"ERROR"``, ``"WARNING"``, ``"DEBUG"``).
    message:
        Human-readable log message.
    payload:
        Optional JSON-serializable dict with extra data (e.g., metrics).
    """
    try:
        factory = make_session_factory(engine)
        session = factory()
        try:
            log_entry = RunLog(
                run_id=run_id,
                node=node,
                level=level,
                message=message,
                payload=payload,
                ts=datetime.now(tz=UTC).isoformat(),
            )
            session.add(log_entry)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
    except Exception:
        # Suppress all errors — logging must never crash nodes
        logger.warning(
            "log_to_db_failed",
            run_id=run_id,
            node=node,
            level=level,
            exc_info=True,
        )
