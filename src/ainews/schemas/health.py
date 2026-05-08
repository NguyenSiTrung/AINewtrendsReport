"""Pydantic schemas for the /api/health endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Health status of a single infrastructure component."""

    status: str = Field(description="'ok' or 'down'.")
    detail: str | None = Field(
        default=None, description="Optional error detail."
    )


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""

    status: str = Field(
        description="Overall status: 'ok', 'degraded', or 'down'."
    )
    components: dict[str, ComponentStatus] = Field(
        description="Per-component health info."
    )
