"""Pydantic schemas for the /api/trigger endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TriggerRequest(BaseModel):
    """Request body for POST /api/trigger.

    Callers provide either ``schedule_name`` to run a named schedule,
    or explicit one-off parameters (``topics``, ``sites``, ``timeframe_days``).
    """

    schedule_name: str | None = Field(
        default=None,
        description="Named schedule to execute (resolves config from DB).",
    )
    topics: list[str] | None = Field(
        default=None,
        description="Ad-hoc topic list for a one-off run.",
    )
    sites: list[str] | None = Field(
        default=None,
        description="Restrict search to these site URLs.",
    )
    timeframe_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Look-back window in days.",
    )


class TriggerResponse(BaseModel):
    """Response body returned by POST /api/trigger."""

    run_id: str = Field(description="UUID of the newly created run.")
    status: str = Field(
        default="pending",
        description="Initial run status (always 'pending').",
    )
