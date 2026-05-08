"""Pipeline service — shared run creation and enqueue logic.

Both the API (``POST /api/trigger``) and CLI (``ainews trigger-run``)
use ``create_and_enqueue_run()`` so run creation is never duplicated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.orm import Session

from ainews.models.run import Run
from ainews.models.schedule import Schedule
from ainews.tasks.pipeline import run_pipeline

logger = structlog.get_logger(__name__)


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
            session.query(Schedule)
            .filter(Schedule.name == schedule_name)
            .first()
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

    now = datetime.now(tz=timezone.utc).isoformat()

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
    log = logger.bind(run_id=run_id, triggered_by=triggered_by)
    log.info("pipeline.run_created")

    # Enqueue Celery task (non-blocking)
    run_pipeline.delay(run_id)
    log.info("pipeline.task_enqueued")

    return run_id
