"""Authentication module — JWT cookie-based auth for the admin UI.

Uses bcrypt for password hashing and PyJWT for token management.
JWT is stored in an HttpOnly cookie for browser-based access.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import bcrypt
import jwt
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from ainews.models.user import User

# ── Configuration ────────────────────────────────────────
# In production, override via AINEWS_JWT_SECRET env var.
JWT_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_COOKIE_NAME = "access_token"
JWT_EXPIRE_HOURS = 24


def _get_jwt_secret() -> str:
    """Return JWT secret, preferring env var over process-level default."""
    import os

    return os.environ.get("AINEWS_JWT_SECRET", JWT_SECRET)


# ── Password utilities ───────────────────────────────────


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT utilities ────────────────────────────────────────


def create_access_token(user_id: int, email: str) -> str:
    """Create a signed JWT access token."""
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(tz=UTC) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(tz=UTC),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token. Returns None on failure."""
    try:
        return jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ── User lookup ──────────────────────────────────────────


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    """Validate credentials. Returns the User if valid, else None."""
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.hashed_pw):
        return None
    return user


def get_user_by_id(session: Session, user_id: int) -> User | None:
    """Look up a user by primary key."""
    return session.get(User, user_id)


def create_admin_user(session: Session, email: str, password: str) -> User:
    """Create an admin user. Raises ValueError if email exists."""
    existing = session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"User with email '{email}' already exists")

    user = User(
        email=email,
        hashed_pw=hash_password(password),
        role="admin",
        created_at=datetime.now(tz=UTC).isoformat(),
    )
    session.add(user)
    session.flush()
    return user
