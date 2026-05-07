"""SQLAlchemy ORM model for the `articles` table."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ainews.models.base import Base


class Article(Base):
    """Represents a single news article fetched during a Run."""

    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("run_id", "url", name="uq_articles_run_id_url"),
        Index("ix_articles_run_id", "run_id"),
        Index("ix_articles_hash", "hash"),
        Index("ix_articles_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("runs.id"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    content_md: Mapped[str | None] = mapped_column(String, nullable=True)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    hash: Mapped[str | None] = mapped_column(String, nullable=True)
    shingles: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="fetched")
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Article id={self.id!r} url={self.url!r} status={self.status!r}>"
