"""Celery Beat periodic tasks."""

from __future__ import annotations

import zoneinfo
from datetime import UTC, datetime

import structlog
from celery import shared_task
from croniter import croniter

from ainews.core.config import get_settings
from ainews.core.database import create_engine, get_db_session
from ainews.models.schedule import Schedule
from ainews.services.pipeline import create_and_enqueue_run

logger = structlog.get_logger(__name__)

# Module-level engine for the beat worker
_settings = get_settings()
_engine = create_engine(_settings.database_url)


@shared_task(name="ainews.tasks.beat.check_schedules")
def check_schedules() -> None:
    """Check all enabled schedules and enqueue runs if their cron expression matches."""
    now_utc = datetime.now(tz=UTC)
    matched = []

    with get_db_session(_engine) as session:
        schedules = session.query(Schedule).filter(Schedule.enabled == 1).all()

        for schedule in schedules:
            try:
                tz_name = schedule.timezone or _settings.timezone
                try:
                    tz = zoneinfo.ZoneInfo(tz_name)
                except zoneinfo.ZoneInfoNotFoundError:
                    logger.warning("beat.invalid_timezone", tz=tz_name, fallback="UTC")
                    tz = UTC

                now_local = now_utc.astimezone(tz)
                now_local_minute = now_local.replace(second=0, microsecond=0)

                if croniter.match(schedule.cron_expr, now_local_minute):
                    matched.append(schedule.name)
            except Exception as exc:
                logger.error(
                    "beat.schedule_eval_failed", schedule=schedule.name, error=str(exc)
                )

    # Process matched schedules in isolated transactions
    for schedule_name in matched:
        try:
            with get_db_session(_engine) as session:
                logger.info("beat.schedule_matched", schedule=schedule_name)
                create_and_enqueue_run(
                    session=session,
                    schedule_name=schedule_name,
                    triggered_by="cron",
                )
        except Exception as exc:
            logger.error("beat.enqueue_failed", schedule=schedule_name, error=str(exc))
