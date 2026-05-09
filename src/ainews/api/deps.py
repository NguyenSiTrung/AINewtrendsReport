"""FastAPI dependency injection utilities."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request
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


def require_api_auth(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Validate JWT authentication for API routes.

    Checks JWT from:
    1. ``Authorization: Bearer <token>`` header (API clients)
    2. ``access_token`` cookie (browser/HTMX requests)

    Raises
    ------
    HTTPException(401)
        If no valid token is found.
    """
    from ainews.api.auth import JWT_COOKIE_NAME, decode_access_token, get_user_by_id

    token: str | None = None

    # Check Authorization header first
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    # Fall back to cookie
    if not token:
        token = request.cookies.get(JWT_COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(session, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    # Store user on request for downstream use
    request.state.api_user = user
