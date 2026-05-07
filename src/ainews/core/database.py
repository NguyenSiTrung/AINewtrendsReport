"""Database engine factory with SQLite-specific pragma configuration."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as _sa_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Architectural invariants — not configurable at runtime
_PRAGMAS: dict[str, Any] = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "foreign_keys": "ON",
    "busy_timeout": 5000,
    "temp_store": "MEMORY",
    "mmap_size": 268435456,
}


def _apply_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Apply performance and safety pragmas to each new SQLite connection."""
    cursor = dbapi_connection.cursor()
    for pragma, value in _PRAGMAS.items():
        cursor.execute(f"PRAGMA {pragma}={value}")
    cursor.close()


def create_engine(url: str) -> Engine:
    """Return a SQLAlchemy Engine with SQLite pragmas applied on every new connection.

    For in-memory URLs (containing ``:memory:``), uses ``StaticPool`` so all
    operations share a single connection — required for test isolation.
    """
    kwargs: dict[str, Any] = {}
    if ":memory:" in url:
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool

    engine = _sa_create_engine(url, **kwargs)
    event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to *engine*.

    Configured with ``autocommit=False`` and ``autoflush=False`` — callers
    manage transactions explicitly via :func:`get_db_session`.
    """
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_db_session(engine: Engine) -> Generator[Session, None, None]:
    """Yield a :class:`~sqlalchemy.orm.Session` with automatic commit/rollback.

    Commits on clean exit; rolls back and re-raises on any exception.
    Suitable as a FastAPI dependency in future phases.
    """
    factory = make_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
