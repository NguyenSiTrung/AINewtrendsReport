"""Pydantic schemas for the /api/runs endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    """Compact run representation for list responses."""

    id: str
    status: str
    triggered_by: str
    schedule_id: int | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class RunDetail(BaseModel):
    """Full run representation including metrics and error info."""

    id: str
    status: str
    triggered_by: str
    schedule_id: int | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    input_params: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None
    error: str | None = None


class RunListResponse(BaseModel):
    """Paginated response for GET /api/runs."""

    runs: list[RunSummary]
    total: int = Field(description="Total number of matching runs.")
    offset: int = Field(default=0)
    limit: int = Field(default=20)


class RunDetailResponse(BaseModel):
    """Response for GET /api/runs/{run_id}."""

    run: RunDetail
