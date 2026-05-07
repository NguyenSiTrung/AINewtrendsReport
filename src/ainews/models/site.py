"""SQLAlchemy ORM model for crawlable web sites."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from ainews.models.base import Base


class Site(Base):
    """A web site targeted for crawling and article extraction.

    Columns
    -------
    id          Integer primary key, autoincrement.
    url         Unique URL of the site, NOT NULL.
    category    Optional site category (e.g. "tech", "ai").
    priority    Crawl priority 1-10; defaults to 5.
    crawl_depth Maximum link-follow depth; defaults to 2.
    selectors   JSON blob of CSS/XPath selector config; nullable.
    js_render   1 = JavaScript rendering required, 0 = static; defaults to 0.
    enabled     1 = active, 0 = disabled; defaults to 1.
    created_at  ISO 8601 creation timestamp (TEXT); nullable.
    """

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    crawl_depth: Mapped[int] = mapped_column(Integer, default=2)
    selectors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    js_render: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_sites_enabled", "enabled"),
        Index("ix_sites_category", "category"),
    )
