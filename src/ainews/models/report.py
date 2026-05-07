"""ORM model for the Report table."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ainews.models.base import Base


class Report(Base):
    """Represents a generated AI-news report for a pipeline run."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    summary_md: Mapped[str | None] = mapped_column(String, nullable=True)
    html_path: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    trends: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    token_usage: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (Index("ix_reports_run_id", "run_id"),)
