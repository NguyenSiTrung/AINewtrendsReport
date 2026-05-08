"""Schedules CRUD router — manage report generation schedules."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ainews.api.deps import get_db
from ainews.models.schedule import Schedule
from ainews.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate

router = APIRouter(tags=["schedules"])


def _schedule_to_response(sched: Schedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=sched.id,
        name=sched.name,
        cron_expr=sched.cron_expr,
        timeframe_days=sched.timeframe_days,
        site_filter=sched.site_filter,
        topics=sched.topics,
        model_override=sched.model_override,
        enabled=bool(sched.enabled),
        created_at=sched.created_at,
    )


@router.get("/schedules", response_model=list[ScheduleResponse])
def list_schedules(
    session: Session = Depends(get_db),  # noqa: B008
) -> list[ScheduleResponse]:
    """Return all schedules.

    # TODO: add auth dependency
    """
    rows = session.execute(select(Schedule)).scalars().all()
    return [_schedule_to_response(s) for s in rows]


@router.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    body: ScheduleCreate,
    session: Session = Depends(get_db),  # noqa: B008
) -> ScheduleResponse:
    """Create a new schedule.

    # TODO: add auth dependency
    """
    sched = Schedule(
        name=body.name,
        cron_expr=body.cron_expr,
        timeframe_days=body.timeframe_days,
        site_filter=body.site_filter,
        topics=body.topics,
        model_override=body.model_override,
        enabled=int(body.enabled),
        created_at=datetime.now(tz=UTC).isoformat(),
    )
    try:
        session.add(sched)
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Schedule with name '{body.name}' already exists",
        ) from exc

    return _schedule_to_response(sched)


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: int,
    session: Session = Depends(get_db),  # noqa: B008
) -> ScheduleResponse:
    """Return a single schedule by ID.

    # TODO: add auth dependency
    """
    sched = session.get(Schedule, schedule_id)
    if sched is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _schedule_to_response(sched)


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    session: Session = Depends(get_db),  # noqa: B008
) -> ScheduleResponse:
    """Update an existing schedule (partial update).

    # TODO: add auth dependency
    """
    sched = session.get(Schedule, schedule_id)
    if sched is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = body.model_dump(exclude_unset=True)
    if "enabled" in update_data:
        update_data["enabled"] = int(update_data["enabled"])

    for key, value in update_data.items():
        setattr(sched, key, value)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Schedule with name '{body.name}' already exists",
        ) from exc

    return _schedule_to_response(sched)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: int,
    session: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a schedule by ID.

    # TODO: add auth dependency
    """
    sched = session.get(Schedule, schedule_id)
    if sched is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    session.delete(sched)
