"""Pipeline service — shared run creation and enqueue logic.

Both the API (``POST /api/trigger``) and CLI (``ainews trigger-run``)
use ``create_and_enqueue_run()`` so run creation is never duplicated.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import structlog
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from ainews.core.database import get_db_session
from ainews.models.run import Run
from ainews.models.run_log import RunLog
from ainews.models.schedule import Schedule
from ainews.services.run_logger import log_to_db
from ainews.tasks.pipeline import run_pipeline

logger = structlog.get_logger(__name__)

_PENDING_ENQUEUES_KEY = "ainews_pending_run_enqueues"
_ENQUEUE_LISTENERS_KEY = "ainews_enqueue_listeners_registered"
_PendingEnqueue = tuple[str, str, Engine]


def create_and_enqueue_run(
    session: Session,
    *,
    schedule_name: str | None = None,
    params: dict[str, Any] | None = None,
    triggered_by: str = "api",
) -> str:
    """Create a Run row and enqueue the Celery pipeline task.

    Parameters
    ----------
    session:
        Active SQLAlchemy session (caller manages transaction).
    schedule_name:
        If provided, resolve schedule config from DB.
    params:
        Ad-hoc run parameters (topics, sites, timeframe_days).
    triggered_by:
        Origin of the trigger: ``"api"``, ``"cli"``, or ``"cron"``.

    Returns
    -------
    The UUID of the newly created run.

    Raises
    ------
    ValueError
        If ``schedule_name`` is provided but not found in the database.
    """
    schedule_id: int | None = None
    input_params: dict[str, Any] = params or {}

    # Resolve schedule if named
    if schedule_name is not None:
        schedule = (
            session.query(Schedule).filter(Schedule.name == schedule_name).first()
        )
        if schedule is None:
            msg = f"Schedule '{schedule_name}' not found"
            raise ValueError(msg)
        schedule_id = schedule.id
        # Merge schedule defaults into params (explicit params take precedence)
        if not input_params.get("topics") and schedule.topics:
            input_params["topics"] = schedule.topics
        if not input_params.get("timeframe_days"):
            input_params["timeframe_days"] = schedule.timeframe_days
        if not input_params.get("sites") and schedule.site_filter:
            input_params["sites"] = schedule.site_filter
        if "use_smart_planner" not in input_params:
            input_params["use_smart_planner"] = bool(schedule.use_smart_planner)

    now = datetime.now(tz=UTC).isoformat()

    run = Run(
        status="pending",
        triggered_by=triggered_by,
        schedule_id=schedule_id,
        input_params=input_params if input_params else None,
        created_at=now,
    )
    session.add(run)
    session.flush()  # Populate run.id

    run_id: str = run.id
    logger.bind(run_id=run_id, triggered_by=triggered_by).info("pipeline.run_created")
    session.add(
        RunLog(
            run_id=run_id,
            node="pipeline",
            level="INFO",
            message="Run created",
            ts=now,
        )
    )

    engine = cast(Engine, session.get_bind())
    _queue_after_commit(session, run_id, triggered_by, engine)

    return run_id


def _queue_after_commit(
    session: Session,
    run_id: str,
    triggered_by: str,
    engine: Engine,
) -> None:
    pending = cast(
        list[_PendingEnqueue],
        session.info.setdefault(_PENDING_ENQUEUES_KEY, []),
    )
    pending.append((run_id, triggered_by, engine))
    if session.info.get(_ENQUEUE_LISTENERS_KEY):
        return

    event.listen(session, "after_commit", _enqueue_pending_after_commit)
    event.listen(session, "after_rollback", _clear_pending_after_rollback)
    session.info[_ENQUEUE_LISTENERS_KEY] = True


def _enqueue_pending_after_commit(session: Session) -> None:
    pending = cast(
        list[_PendingEnqueue],
        session.info.pop(_PENDING_ENQUEUES_KEY, []),
    )
    for run_id, triggered_by, engine in pending:
        _enqueue_committed_run(run_id, triggered_by, engine)


def _clear_pending_after_rollback(session: Session) -> None:
    session.info.pop(_PENDING_ENQUEUES_KEY, None)


def _enqueue_committed_run(run_id: str, triggered_by: str, engine: Engine) -> None:
    log = logger.bind(run_id=run_id, triggered_by=triggered_by)
    try:
        run_pipeline.delay(run_id)
    except Exception as exc:
        error = f"Failed to enqueue pipeline task: {exc}"
        log.error("pipeline.task_enqueue_failed", error=str(exc))
        _record_enqueue_failure(engine, run_id, error, str(exc), log)
        return

    log.info("pipeline.task_enqueued")
    log_to_db(
        engine,
        run_id,
        "pipeline",
        "INFO",
        "Pipeline task enqueued",
    )


def _record_enqueue_failure(
    engine: Engine,
    run_id: str,
    error: str,
    reason: str,
    log: Any,
) -> None:
    try:
        with get_db_session(engine) as failure_session:
            failed_run = failure_session.get(Run, run_id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.finished_at = datetime.now(tz=UTC).isoformat()
                failed_run.error = error
            failure_session.add(
                RunLog(
                    run_id=run_id,
                    node="pipeline",
                    level="ERROR",
                    message=f"Pipeline task enqueue failed: {reason}",
                    ts=datetime.now(tz=UTC).isoformat(),
                )
            )
    except Exception:
        log.warning(
            "pipeline.task_enqueue_failure_persist_failed",
            exc_info=True,
        )
