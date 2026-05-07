"""SQLAlchemy ORM model for report generation schedules."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from ainews.models.base import Base


class Schedule(Base):
    """A scheduled report run configuration.

    Columns
    -------
    id              Integer primary key, autoincrement.
    name            Unique schedule name, NOT NULL.
    cron_expr       Cron expression (e.g. ``"0 7 * * 1"``), NOT NULL.
    timeframe_days  Number of days back to pull articles; defaults to 7.
    site_filter     JSON list of site categories/urls to include; nullable.
    topics          JSON list of topic strings; nullable.
    model_override  Optional LLM model name override; nullable.
    enabled         1 = active, 0 = disabled; defaults to 1.
    created_at      ISO 8601 creation timestamp (TEXT); nullable.
    """

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    cron_expr: Mapped[str] = mapped_column(String, nullable=False)
    timeframe_days: Mapped[int] = mapped_column(Integer, default=7)
    site_filter: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    topics: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    model_override: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (Index("ix_schedules_enabled", "enabled"),)
