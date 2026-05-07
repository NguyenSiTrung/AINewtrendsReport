"""ORM model for the RunLog table."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ainews.models.base import Base


class RunLog(Base):
    """Structured log entry emitted by a pipeline node during a run."""

    __tablename__ = "run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id"), nullable=False
    )
    node: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False, default="info")
    message: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    ts: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_run_logs_run_id", "run_id"),
        Index("ix_run_logs_level", "level"),
    )
