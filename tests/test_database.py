"""Tests for database engine factory and SQLite pragma configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from ainews.core.database import create_engine, get_db_session, make_session_factory


@pytest.fixture()
def file_engine(tmp_path: Path):  # type: ignore[misc]
    """Engine backed by a temp file (WAL mode requires a file-based database)."""
    db = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db}")
    yield engine
    engine.dispose()


def test_in_memory_engine_uses_static_pool() -> None:
    """In-memory SQLite engine uses StaticPool to share one connection."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite:///:memory:")
    assert isinstance(engine.pool, StaticPool)
    engine.dispose()


def test_pragma_journal_mode_wal(file_engine) -> None:  # type: ignore[no-untyped-def]
    """journal_mode=WAL is applied on every new connection."""
    with file_engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert result == "wal"


def test_pragma_synchronous_normal(file_engine) -> None:  # type: ignore[no-untyped-def]
    """synchronous=NORMAL (1) is applied on every new connection."""
    with file_engine.connect() as conn:
        result = conn.execute(text("PRAGMA synchronous")).scalar()
    assert result == 1


def test_pragma_foreign_keys_on(file_engine) -> None:  # type: ignore[no-untyped-def]
    """foreign_keys=ON (1) is applied on every new connection."""
    with file_engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1


def test_pragma_busy_timeout(file_engine) -> None:  # type: ignore[no-untyped-def]
    """busy_timeout=5000ms is applied on every new connection."""
    with file_engine.connect() as conn:
        result = conn.execute(text("PRAGMA busy_timeout")).scalar()
    assert result == 5000


def test_pragma_temp_store_memory(file_engine) -> None:  # type: ignore[no-untyped-def]
    """temp_store=MEMORY (2) is applied on every new connection."""
    with file_engine.connect() as conn:
        result = conn.execute(text("PRAGMA temp_store")).scalar()
    assert result == 2


def test_pragma_mmap_size(file_engine) -> None:  # type: ignore[no-untyped-def]
    """mmap_size=268435456 (256 MiB) is applied on every new connection."""
    with file_engine.connect() as conn:
        result = conn.execute(text("PRAGMA mmap_size")).scalar()
    assert result == 268435456


# ── Session management ────────────────────────────────────────────────────────


def test_session_factory_returns_sessions() -> None:
    """make_session_factory() returns a factory that creates Session instances."""
    engine = create_engine("sqlite:///:memory:")
    factory = make_session_factory(engine)
    session = factory()
    assert isinstance(session, Session)
    session.close()
    engine.dispose()


def test_get_db_session_yields_session() -> None:
    """get_db_session() context manager yields a live Session."""
    engine = create_engine("sqlite:///:memory:")
    with get_db_session(engine) as session:
        assert isinstance(session, Session)
        assert session.is_active
    engine.dispose()


def test_get_db_session_commits_on_success() -> None:
    """get_db_session() commits when no exception is raised."""
    engine = create_engine("sqlite:///:memory:")
    with get_db_session(engine) as session:
        session.execute(text("SELECT 1"))
    engine.dispose()


def test_get_db_session_rolls_back_on_exception() -> None:
    """get_db_session() rolls back and re-raises on exception."""
    engine = create_engine("sqlite:///:memory:")
    raises_ctx = pytest.raises(RuntimeError, match="test rollback")
    with raises_ctx, get_db_session(engine) as session:
        session.execute(text("SELECT 1"))
        raise RuntimeError("test rollback")
    engine.dispose()


def test_session_factory_independent_sessions() -> None:
    """Each call to the factory produces an independent Session."""
    engine = create_engine("sqlite:///:memory:")
    factory = make_session_factory(engine)
    s1 = factory()
    s2 = factory()
    assert s1 is not s2
    s1.close()
    s2.close()
    engine.dispose()
