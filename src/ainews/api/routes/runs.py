"""Runs router — paginated list and detail views for pipeline runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ainews.api.deps import get_db, require_api_auth
from ainews.models.run import Run
from ainews.schemas.run import (
    RunDetail,
    RunDetailResponse,
    RunListResponse,
    RunSummary,
)

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=RunListResponse, dependencies=[Depends(require_api_auth)])
def list_runs(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    session: Session = Depends(get_db),  # noqa: B008
) -> RunListResponse:
    """Return a paginated list of runs, optionally filtered by status."""
    query = select(Run).order_by(Run.created_at.desc())  # type: ignore[union-attr]
    count_query = select(func.count()).select_from(Run)

    if status:
        query = query.where(Run.status == status)
        count_query = count_query.where(Run.status == status)

    total: int = session.execute(count_query).scalar_one()
    rows = session.execute(query.offset(offset).limit(limit)).scalars().all()

    runs = [
        RunSummary(
            id=r.id,
            status=r.status,
            triggered_by=r.triggered_by,
            schedule_id=r.schedule_id,
            created_at=r.created_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
        )
        for r in rows
    ]

    return RunListResponse(runs=runs, total=total, offset=offset, limit=limit)


@router.get("/runs/{run_id}", response_model=RunDetailResponse, dependencies=[Depends(require_api_auth)])
def get_run(
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> RunDetailResponse:
    """Return detailed info for a single run."""
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    detail = RunDetail(
        id=run.id,
        status=run.status,
        triggered_by=run.triggered_by,
        schedule_id=run.schedule_id,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        input_params=run.input_params,
        stats=run.stats,
        error=run.error,
    )

    return RunDetailResponse(run=detail)
