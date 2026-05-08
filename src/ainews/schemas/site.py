"""Pydantic schemas for the /api/sites endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class SiteCreate(BaseModel):
    """Request body for POST /api/sites."""

    url: str = Field(description="Unique URL of the site.")
    category: str | None = None
    priority: int = Field(default=5, ge=1, le=10)
    crawl_depth: int = Field(default=2, ge=1, le=10)
    selectors: dict[str, Any] | None = None
    js_render: bool = Field(default=False)
    enabled: bool = Field(default=True)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            msg = "URL must start with http:// or https://"
            raise ValueError(msg)
        return v


class SiteUpdate(BaseModel):
    """Request body for PUT /api/sites/{id} — all fields optional."""

    url: str | None = None
    category: str | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    crawl_depth: int | None = Field(default=None, ge=1, le=10)
    selectors: dict[str, Any] | None = None
    js_render: bool | None = None
    enabled: bool | None = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                msg = "URL must start with http:// or https://"
                raise ValueError(msg)
        return v


class SiteResponse(BaseModel):
    """Response body for site endpoints."""

    id: int
    url: str
    category: str | None = None
    priority: int
    crawl_depth: int
    selectors: dict[str, Any] | None = None
    js_render: bool
    enabled: bool
    created_at: str | None = None
