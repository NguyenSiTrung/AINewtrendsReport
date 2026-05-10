"""Tests for Phase 1 Foundation & Base Layout.

Covers static files, templates, CSRF, flash.
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
    """FastAPI test client with overridden DB engine."""
    from ainews.api.main import create_app

    app = create_app()
    app.state.engine = engine

    return TestClient(app, raise_server_exceptions=False)


def _login(client: TestClient, engine: Any) -> dict[str, str]:
    """Create admin and login, returning cookies dict."""
    from ainews.api.auth import create_admin_user
    from ainews.core.database import get_db_session

    with get_db_session(engine) as session:
        create_admin_user(session, "admin@test.com", "pass123")
        session.commit()

    csrf = client.get("/login").cookies.get("csrf_token", "")
    resp = client.post(
        "/login",
        data={
            "email": "admin@test.com",
            "password": "pass123",
            "csrf_token": csrf,
        },
        headers={"x-csrf-token": csrf},
        cookies={"csrf_token": csrf},
        follow_redirects=False,
    )
    return {
        "access_token": resp.cookies.get("access_token", ""),
        "csrf_token": resp.cookies.get("csrf_token", csrf),
    }


# ── Static File Serving ──────────────────────────────────


class TestStaticFiles:
    def test_css_output_served(self, client: TestClient) -> None:
        """GET /static/css/output.css returns 200."""
        resp = client.get("/static/css/output.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_missing_static_404(self, client: TestClient) -> None:
        """Missing static files return 404."""
        resp = client.get("/static/nonexistent.js")
        assert resp.status_code == 404


# ── Template Rendering ───────────────────────────────────


class TestBaseTemplate:
    def test_dashboard_renders_html(self, client: TestClient, engine: Any) -> None:
        """GET / returns HTML containing the base layout."""
        cookies = _login(client, engine)
        resp = client.get("/", cookies=cookies)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        html = resp.text
        assert "AI News" in html
        assert "Dashboard" in html

    def test_dashboard_has_tailwind_link(self, client: TestClient, engine: Any) -> None:
        """Base template includes the compiled Tailwind CSS."""
        cookies = _login(client, engine)
        resp = client.get("/", cookies=cookies)
        assert "/static/css/output.css" in resp.text

    def test_dashboard_has_htmx_script(self, client: TestClient, engine: Any) -> None:
        """Base template includes HTMX."""
        cookies = _login(client, engine)
        resp = client.get("/", cookies=cookies)
        assert "htmx.org" in resp.text

    def test_dashboard_has_alpine_script(self, client: TestClient, engine: Any) -> None:
        """Base template includes Alpine.js."""
        cookies = _login(client, engine)
        resp = client.get("/", cookies=cookies)
        assert "alpinejs" in resp.text

    def test_dashboard_has_nav_links(self, client: TestClient, engine: Any) -> None:
        """Sidebar contains navigation links to all pages."""
        cookies = _login(client, engine)
        resp = client.get("/", cookies=cookies)
        html = resp.text
        pages = [
            "/sites",
            "/schedules",
            "/runs",
            "/trigger",
            "/logs",
            "/llm",
            "/settings",
            "/health",
        ]
        for page in pages:
            assert f'href="{page}"' in html, f"Nav: {page}"


# ── CSRF Protection ──────────────────────────────────────


class TestCSRF:
    def test_csrf_cookie_set(self, client: TestClient) -> None:
        """First request sets the csrf_token cookie."""
        resp = client.get("/login")
        assert "csrf_token" in resp.cookies

    def test_csrf_meta_tag_in_html(self, client: TestClient) -> None:
        """The login template includes a CSRF meta tag."""
        resp = client.get("/login")
        assert 'name="csrf-token"' in resp.text

    def test_post_without_csrf_fails(self, client: TestClient) -> None:
        """POST without any CSRF cookie returns 403."""
        # POST without any cookies — no csrf_token cookie
        resp = client.post(
            "/login",
            data={"email": "a@b.com", "password": "x"},
        )
        assert resp.status_code == 403

    def test_post_with_valid_csrf_passes(self, client: TestClient) -> None:
        """POST with matching CSRF cookie passes validation."""
        resp = client.get("/login")
        token = resp.cookies.get("csrf_token", "")
        assert token, "No CSRF token cookie set"

        # POST with CSRF cookie present — should not be 403
        resp = client.post(
            "/login",
            data={
                "email": "test@example.com",
                "password": "wrong",
                "csrf_token": token,
            },
            headers={"x-csrf-token": token},
            cookies={"csrf_token": token},
        )
        # Should not be 403 — CSRF passed (may be 200 with error)
        assert resp.status_code != 403

    def test_api_routes_exempt_from_csrf(self, client: TestClient) -> None:
        """POST to /api/* routes does NOT require CSRF (uses JWT auth instead)."""
        resp = client.post(
            "/api/sites",
            json={"url": "https://api-test.com"},
        )
        # Should be 401 (auth required), NOT 403 (CSRF blocked)
        # This proves the CSRF middleware correctly exempts /api/* routes.
        assert resp.status_code == 401


# ── Flash Messages ───────────────────────────────────────


class TestFlashMessages:
    def test_flash_set_and_read(self) -> None:
        """Flash utility correctly creates messages."""
        from starlette.responses import Response

        from ainews.api.flash import FlashMessage, flash

        resp = Response()
        flash(resp, "Test success", "success")

        # The cookie should have been set on the response
        cookie_header = dict(resp.headers).get("set-cookie", "")
        assert "_flash" in cookie_header

        # Check the dataclass
        msg = FlashMessage(text="Test success", category="success")
        assert msg.text == "Test success"
        assert msg.category == "success"

    def test_flash_cookie_round_trip(self, client: TestClient, engine: Any) -> None:
        """Flash message cookie is rendered in the dashboard."""
        import json

        from ainews.api.flash import FLASH_COOKIE

        cookies = _login(client, engine)
        flash_data = json.dumps({"text": "Created!", "category": "success"})
        cookies[FLASH_COOKIE] = flash_data
        resp = client.get("/", cookies=cookies)
        assert resp.status_code == 200
        assert "Created!" in resp.text
