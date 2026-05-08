"""FastAPI dependency injection utilities."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from ainews.core.database import make_session_factory


def get_engine(request: Request) -> Engine:
    """Extract the SQLAlchemy engine from app state."""
    return request.app.state.engine  # type: ignore[no-any-return]


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session per request, with auto-commit/rollback."""
    engine: Engine = get_engine(request)
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
