"""Tests for Phase 2: Authentication System.

Covers password hashing, JWT tokens, login/logout flow,
auth-gated pages, and the seed admin CLI command.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine
from ainews.models import Base


@pytest.fixture()
def engine() -> Any:
    """In-memory SQLite engine with all tables."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def client(engine: Any) -> TestClient:
    """FastAPI test client."""
    from ainews.api.main import create_app

    app = create_app()
    app.state.engine = engine
    return TestClient(app, raise_server_exceptions=False)


def _seed_admin(engine: Any) -> None:
    """Create a test admin user in the database."""
    from ainews.api.auth import create_admin_user
    from ainews.core.database import get_db_session

    with get_db_session(engine) as session:
        create_admin_user(session, "admin@test.com", "secret123")
        session.commit()


# ── Password Utilities ───────────────────────────────────


class TestPasswordUtils:
    def test_hash_and_verify(self) -> None:
        """bcrypt hash can be verified."""
        from ainews.api.auth import hash_password, verify_password

        hashed = hash_password("my_password")
        assert hashed != "my_password"
        assert verify_password("my_password", hashed)
        assert not verify_password("wrong_password", hashed)

    def test_hash_is_unique(self) -> None:
        """Different calls produce different hashes (salted)."""
        from ainews.api.auth import hash_password

        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


# ── JWT Tokens ───────────────────────────────────────────


class TestJWT:
    def test_create_and_decode(self) -> None:
        """JWT round-trips correctly."""
        from ainews.api.auth import (
            create_access_token,
            decode_access_token,
        )

        token = create_access_token(42, "test@example.com")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "test@example.com"

    def test_invalid_token_returns_none(self) -> None:
        """Invalid JWT string returns None."""
        from ainews.api.auth import decode_access_token

        assert decode_access_token("garbage.token.here") is None


# ── Login Flow ───────────────────────────────────────────


class TestLoginFlow:
    def test_login_page_renders(self, client: TestClient) -> None:
        """GET /login returns the login form."""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Terminal Login" in resp.text
        assert 'name="email"' in resp.text

    def test_login_invalid_credentials(self, client: TestClient, engine: Any) -> None:
        """POST /login with wrong credentials re-renders with error."""
        _seed_admin(engine)
        token = client.get("/login").cookies.get("csrf_token", "")
        resp = client.post(
            "/login",
            data={
                "email": "admin@test.com",
                "password": "wrong",
                "csrf_token": token,
            },
            cookies={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        assert "Invalid" in resp.text

    def test_login_success_sets_cookie(self, client: TestClient, engine: Any) -> None:
        """Successful login sets JWT cookie and redirects."""
        _seed_admin(engine)
        token = client.get("/login").cookies.get("csrf_token", "")
        resp = client.post(
            "/login",
            data={
                "email": "admin@test.com",
                "password": "secret123",
                "csrf_token": token,
            },
            cookies={"csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"
        assert "access_token" in resp.cookies

    def test_logout_clears_cookie(self, client: TestClient, engine: Any) -> None:
        """GET /logout clears the JWT cookie."""
        _seed_admin(engine)
        # Login first
        token = client.get("/login").cookies.get("csrf_token", "")
        login_resp = client.post(
            "/login",
            data={
                "email": "admin@test.com",
                "password": "secret123",
                "csrf_token": token,
            },
            cookies={"csrf_token": token},
            follow_redirects=False,
        )
        jwt_cookie = login_resp.cookies.get("access_token", "")

        # Now logout
        resp = client.get(
            "/logout",
            cookies={"access_token": jwt_cookie},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


# ── Auth-Gated Pages ────────────────────────────────────


class TestAuthGating:
    def test_dashboard_requires_auth(self, client: TestClient) -> None:
        """GET / without auth redirects to /login."""
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_dashboard_accessible_after_login(
        self, client: TestClient, engine: Any
    ) -> None:
        """GET / with valid JWT shows dashboard."""
        _seed_admin(engine)
        token = client.get("/login").cookies.get("csrf_token", "")
        login_resp = client.post(
            "/login",
            data={
                "email": "admin@test.com",
                "password": "secret123",
                "csrf_token": token,
            },
            cookies={"csrf_token": token},
            follow_redirects=False,
        )
        jwt_cookie = login_resp.cookies.get("access_token", "")

        resp = client.get(
            "/",
            cookies={"access_token": jwt_cookie},
        )
        assert resp.status_code == 200
        assert "Dashboard" in resp.text


# ── Create Admin User ───────────────────────────────────


class TestCreateAdminUser:
    def test_create_admin(self, engine: Any) -> None:
        """create_admin_user persists a user with hashed password."""
        from ainews.api.auth import (
            create_admin_user,
            verify_password,
        )
        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            user = create_admin_user(session, "new@admin.com", "pass123")
            session.commit()
            # Access attrs while session is still open
            assert user.email == "new@admin.com"
            assert user.role == "admin"
            assert verify_password("pass123", user.hashed_pw)

    def test_duplicate_email_raises(self, engine: Any) -> None:
        """Duplicate email raises ValueError."""
        from ainews.api.auth import create_admin_user
        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            create_admin_user(session, "dup@admin.com", "pass")
            session.commit()

        with (
            pytest.raises(ValueError, match="already exists"),
            get_db_session(engine) as session,
        ):
            create_admin_user(session, "dup@admin.com", "pass2")
