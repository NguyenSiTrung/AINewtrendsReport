"""Tests for the Run ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

import ainews.models.schedule  # noqa: F401 - registers Schedule with Base.metadata
from ainews.core.database import create_engine, make_session_factory
from ainews.models.base import Base
from ainews.models.run import Run


@pytest.fixture()
def engine():  # type: ignore[misc]
    """In-memory SQLite engine with all model tables created."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):  # type: ignore[misc]
    """Session bound to the in-memory engine."""
    factory = make_session_factory(engine)
    sess = factory()
    yield sess
    sess.close()


# ── Table creation ────────────────────────────────────────────────────────────


def test_run_table_created(engine) -> None:  # type: ignore[no-untyped-def]
    """runs table is created by Base.metadata.create_all."""
    inspector = inspect(engine)
    assert "runs" in inspector.get_table_names()


# ── Primary key / UUID ────────────────────────────────────────────────────────


def test_run_uuid_pk_auto_generated(session) -> None:  # type: ignore[no-untyped-def]
    """Run.id is auto-generated as a UUID string when not provided."""
    run = Run()
    session.add(run)
    session.commit()
    assert run.id is not None
    assert len(run.id) == 36  # UUID format: 8-4-4-4-12


def test_run_uuid_pk_unique_per_instance(session) -> None:  # type: ignore[no-untyped-def]
    """Each Run() gets a distinct UUID string after DB flush."""
    r1 = Run()
    r2 = Run()
    session.add_all([r1, r2])
    session.commit()
    assert r1.id != r2.id


def test_run_uuid_pk_is_string(session) -> None:  # type: ignore[no-untyped-def]
    """Run.id is a str after DB flush."""
    run = Run()
    session.add(run)
    session.commit()
    assert isinstance(run.id, str)


# ── Status default ────────────────────────────────────────────────────────────


def test_run_default_status(session) -> None:  # type: ignore[no-untyped-def]
    """Run.status defaults to 'pending' after DB round-trip."""
    run = Run()
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.status == "pending"


# ── Nullable schedule_id ──────────────────────────────────────────────────────


def test_run_schedule_id_nullable(session) -> None:  # type: ignore[no-untyped-def]
    """Run.schedule_id is nullable (supports ad-hoc runs)."""
    run = Run(schedule_id=None)
    session.add(run)
    session.commit()
    assert run.schedule_id is None


# ── JSON columns ──────────────────────────────────────────────────────────────


def test_run_json_columns_accept_dicts(session) -> None:  # type: ignore[no-untyped-def]
    """Run.input_params and Run.stats accept dict values."""
    run = Run(
        input_params={"key": "value", "count": 42},
        stats={"articles_fetched": 10, "articles_kept": 5},
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.input_params == {"key": "value", "count": 42}
    assert run.stats == {"articles_fetched": 10, "articles_kept": 5}


def test_run_json_columns_default_none(session) -> None:  # type: ignore[no-untyped-def]
    """Run.input_params and Run.stats default to None."""
    run = Run()
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.input_params is None
    assert run.stats is None


# ── Timestamp columns ─────────────────────────────────────────────────────────


def test_run_timestamps_nullable_by_default(session) -> None:  # type: ignore[no-untyped-def]
    """Run timestamp fields are nullable and default to None."""
    run = Run()
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.started_at is None
    assert run.finished_at is None
    assert run.created_at is None


def test_run_timestamps_stored_as_iso8601_text(session) -> None:  # type: ignore[no-untyped-def]
    """Timestamps are stored and retrieved as ISO 8601 TEXT strings."""
    ts = "2026-05-07T10:00:00Z"
    run = Run(started_at=ts, finished_at=ts, created_at=ts)
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.started_at == ts
    assert run.finished_at == ts
    assert run.created_at == ts


# ── Indexes ───────────────────────────────────────────────────────────────────


def test_run_index_on_status(engine) -> None:  # type: ignore[no-untyped-def]
    """Index ix_runs_status exists on the runs table."""
    inspector = inspect(engine)
    indexes = {ix["name"] for ix in inspector.get_indexes("runs")}
    assert "ix_runs_status" in indexes


def test_run_index_on_schedule_id(engine) -> None:  # type: ignore[no-untyped-def]
    """Index ix_runs_schedule_id exists on the runs table."""
    inspector = inspect(engine)
    indexes = {ix["name"] for ix in inspector.get_indexes("runs")}
    assert "ix_runs_schedule_id" in indexes
