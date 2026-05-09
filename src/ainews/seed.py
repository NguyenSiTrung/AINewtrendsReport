"""Seed data and idempotent upsert logic for starter sites and schedules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ainews.models.schedule import Schedule
from ainews.models.site import Site

STARTER_SITES: list[dict[str, Any]] = [
    {
        "url": "https://techcrunch.com/category/artificial-intelligence/",
        "category": "tech",
        "priority": 8,
    },
    {
        "url": "https://www.theverge.com/ai-artificial-intelligence",
        "category": "tech",
        "priority": 7,
    },
    {
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/",
        "category": "research",
        "priority": 9,
    },
    {
        "url": "https://huggingface.co/blog",
        "category": "research",
        "priority": 9,
    },
    {
        "url": "https://openai.com/blog",
        "category": "industry",
        "priority": 10,
    },
    {
        "url": "https://www.anthropic.com/news",
        "category": "industry",
        "priority": 10,
    },
    {
        "url": "https://ai.googleblog.com/",
        "category": "research",
        "priority": 9,
    },
    {
        "url": "https://arxiv-sanity-lite.com/",
        "category": "research",
        "priority": 8,
    },
    {
        "url": "https://stratechery.com/",
        "category": "analysis",
        "priority": 7,
    },
    {
        "url": "https://www.bensbites.co/",
        "category": "newsletter",
        "priority": 7,
    },
]

STARTER_SCHEDULES: list[dict[str, Any]] = [
    {
        "name": "weekly-ai-news",
        "cron_expr": "0 7 * * 1",
        "timeframe_days": 7,
        "topics": ["AI Trends", "AI News"],
    },
]


@dataclass
class SeedResult:
    """Counts of created and skipped records from a seed run."""

    sites_created: int
    sites_skipped: int
    schedules_created: int
    schedules_skipped: int


@dataclass
class ResetResult:
    """Counts from a reset-to-defaults operation."""

    sites_deleted: int
    schedules_deleted: int
    sites_created: int
    schedules_created: int


def reset_all(session: Session) -> ResetResult:
    """Delete all sites and schedules, then re-seed with defaults.

    This is a destructive operation — all user-created and modified
    records are removed and replaced with the starter data.
    """
    from sqlalchemy import delete

    sites_deleted = session.execute(delete(Site)).rowcount  # type: ignore[union-attr]
    schedules_deleted = session.execute(delete(Schedule)).rowcount  # type: ignore[union-attr]

    for data in STARTER_SITES:
        session.add(Site(**data))
    for data in STARTER_SCHEDULES:
        session.add(Schedule(**data))

    session.commit()

    return ResetResult(
        sites_deleted=sites_deleted,
        schedules_deleted=schedules_deleted,
        sites_created=len(STARTER_SITES),
        schedules_created=len(STARTER_SCHEDULES),
    )


def seed_all(session: Session) -> SeedResult:
    """Upsert all starter sites and schedules into the database.

    Matches sites by URL and schedules by name.  Safe to call multiple times
    (idempotent): existing records are counted as skipped, not duplicated.
    """
    sites_created, sites_skipped = _upsert_sites(session)
    schedules_created, schedules_skipped = _upsert_schedules(session)
    return SeedResult(
        sites_created=sites_created,
        sites_skipped=sites_skipped,
        schedules_created=schedules_created,
        schedules_skipped=schedules_skipped,
    )


def _upsert_sites(session: Session) -> tuple[int, int]:
    created = 0
    skipped = 0
    for data in STARTER_SITES:
        exists = session.execute(
            select(Site).filter_by(url=data["url"])
        ).scalar_one_or_none()
        if exists is not None:
            skipped += 1
        else:
            session.add(Site(**data))
            created += 1
    session.commit()
    return created, skipped


def _upsert_schedules(session: Session) -> tuple[int, int]:
    created = 0
    skipped = 0
    for data in STARTER_SCHEDULES:
        exists = session.execute(
            select(Schedule).filter_by(name=data["name"])
        ).scalar_one_or_none()
        if exists is not None:
            skipped += 1
        else:
            session.add(Schedule(**data))
            created += 1
    session.commit()
    return created, skipped
