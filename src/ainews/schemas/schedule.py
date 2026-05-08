"""Pydantic schemas for the /api/schedules endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _validate_cron(expr: str) -> str:
    """Validate a cron expression using croniter."""
    from croniter import CroniterBadCronError, croniter

    try:
        croniter(expr)
    except (CroniterBadCronError, ValueError, KeyError) as exc:
        msg = f"Invalid cron expression: {exc}"
        raise ValueError(msg) from exc
    return expr


class ScheduleCreate(BaseModel):
    """Request body for POST /api/schedules."""

    name: str = Field(min_length=1, max_length=100)
    cron_expr: str = Field(description="Standard 5-field cron expression.")
    timeframe_days: int = Field(default=7, ge=1, le=365)
    site_filter: list[Any] | None = None
    topics: list[Any] | None = None
    model_override: str | None = None
    enabled: bool = Field(default=True)

    @field_validator("cron_expr")
    @classmethod
    def _validate_cron(cls, v: str) -> str:
        return _validate_cron(v)


class ScheduleUpdate(BaseModel):
    """Request body for PUT /api/schedules/{id} — all fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    cron_expr: str | None = None
    timeframe_days: int | None = Field(default=None, ge=1, le=365)
    site_filter: list[Any] | None = None
    topics: list[Any] | None = None
    model_override: str | None = None
    enabled: bool | None = None

    @field_validator("cron_expr")
    @classmethod
    def _validate_cron(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_cron(v)
        return v


class ScheduleResponse(BaseModel):
    """Response body for schedule endpoints."""

    id: int
    name: str
    cron_expr: str
    timeframe_days: int
    site_filter: list[Any] | None = None
    topics: list[Any] | None = None
    model_override: str | None = None
    enabled: bool
    created_at: str | None = None
