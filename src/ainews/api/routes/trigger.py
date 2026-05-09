"""Trigger router — POST /api/trigger to create and enqueue a pipeline run."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ainews.api.deps import get_db, require_api_auth
from ainews.schemas.trigger import TriggerRequest, TriggerResponse
from ainews.services.pipeline import create_and_enqueue_run

router = APIRouter(tags=["trigger"])


@router.post("/trigger", response_model=TriggerResponse, status_code=201, dependencies=[Depends(require_api_auth)])
def trigger_run(
    body: TriggerRequest,
    session: Session = Depends(get_db),  # noqa: B008
) -> TriggerResponse:
    """Create a new pipeline run and enqueue it for background execution."""
    params = {}
    if body.topics:
        params["topics"] = body.topics
    if body.sites:
        params["sites"] = body.sites
    if body.timeframe_days:
        params["timeframe_days"] = body.timeframe_days

    run_id = create_and_enqueue_run(
        session,
        schedule_name=body.schedule_name,
        params=params or None,
        triggered_by="api",
    )

    return TriggerResponse(run_id=run_id, status="pending")
