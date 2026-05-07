"""Tests for the seed data module — upsert logic, idempotency, and counts."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from ainews.core.database import create_engine, get_db_session
from ainews.models.base import Base
from ainews.models.schedule import Schedule
from ainews.models.site import Site
from ainews.seed import STARTER_SCHEDULES, STARTER_SITES, SeedResult, seed_all


@pytest.fixture()
def session():  # type: ignore[misc]
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with get_db_session(engine) as s:
        yield s
    engine.dispose()


# ── Starter data constants ────────────────────────────────────────────────────


def test_starter_sites_count() -> None:
    """STARTER_SITES defines exactly 10 sites."""
    assert len(STARTER_SITES) == 10


def test_starter_sites_all_have_urls() -> None:
    """Every starter site has a non-empty URL."""
    for site in STARTER_SITES:
        assert site["url"], f"Missing url in site: {site}"


def test_starter_sites_urls_are_unique() -> None:
    """All starter site URLs are distinct."""
    urls = [s["url"] for s in STARTER_SITES]
    assert len(urls) == len(set(urls))


def test_starter_schedules_count() -> None:
    """STARTER_SCHEDULES defines exactly 1 schedule."""
    assert len(STARTER_SCHEDULES) == 1


def test_starter_weekly_schedule_fields() -> None:
    """The weekly-ai-news schedule has the expected cron and timeframe."""
    sched = STARTER_SCHEDULES[0]
    assert sched["name"] == "weekly-ai-news"
    assert sched["cron_expr"] == "0 7 * * 1"
    assert sched["timeframe_days"] == 7


# ── seed_all: first run creates everything ────────────────────────────────────


def test_seed_all_first_run_creates_sites(session: Session) -> None:
    """First call to seed_all inserts all 10 starter sites."""
    result = seed_all(session)
    assert result.sites_created == 10
    assert result.sites_skipped == 0
    assert session.query(Site).count() == 10


def test_seed_all_first_run_creates_schedule(session: Session) -> None:
    """First call to seed_all inserts the weekly-ai-news schedule."""
    result = seed_all(session)
    assert result.schedules_created == 1
    assert result.schedules_skipped == 0
    assert session.query(Schedule).count() == 1


def test_seed_all_returns_seed_result(session: Session) -> None:
    """seed_all returns a SeedResult dataclass."""
    result = seed_all(session)
    assert isinstance(result, SeedResult)


# ── seed_all: idempotency (second run skips all) ──────────────────────────────


def test_seed_all_idempotent_sites(session: Session) -> None:
    """Second call to seed_all skips all existing sites."""
    seed_all(session)
    result = seed_all(session)

    assert result.sites_created == 0
    assert result.sites_skipped == 10
    assert session.query(Site).count() == 10  # unchanged


def test_seed_all_idempotent_schedules(session: Session) -> None:
    """Second call to seed_all skips the existing schedule."""
    seed_all(session)
    result = seed_all(session)

    assert result.schedules_created == 0
    assert result.schedules_skipped == 1
    assert session.query(Schedule).count() == 1  # unchanged


# ── seed_all: partial — one pre-existing, rest new ───────────────────────────


def test_seed_all_partial_sites(session: Session) -> None:
    """Partial pre-seed: only already-existing sites are skipped."""
    first_url = STARTER_SITES[0]["url"]
    session.add(Site(url=first_url, enabled=1))
    session.commit()

    result = seed_all(session)
    assert result.sites_created == 9
    assert result.sites_skipped == 1
    assert session.query(Site).count() == 10


def test_seed_all_partial_schedule(session: Session) -> None:
    """Partial pre-seed: only the existing schedule is skipped."""
    session.add(
        Schedule(name="weekly-ai-news", cron_expr="0 0 * * 0", timeframe_days=7)
    )
    session.commit()

    result = seed_all(session)
    assert result.schedules_created == 0
    assert result.schedules_skipped == 1
