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
    def test_dashboard_renders_html(self, client: TestClient) -> None:
        """GET / returns HTML containing the base layout."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        html = resp.text
        assert "AI News" in html
        assert "Dashboard" in html

    def test_dashboard_has_tailwind_link(self, client: TestClient) -> None:
        """Base template includes the compiled Tailwind CSS."""
        resp = client.get("/")
        assert "/static/css/output.css" in resp.text

    def test_dashboard_has_htmx_script(self, client: TestClient) -> None:
        """Base template includes HTMX."""
        resp = client.get("/")
        assert "htmx.org" in resp.text

    def test_dashboard_has_alpine_script(self, client: TestClient) -> None:
        """Base template includes Alpine.js."""
        resp = client.get("/")
        assert "alpinejs" in resp.text

    def test_dashboard_has_nav_links(self, client: TestClient) -> None:
        """Sidebar contains navigation links to all pages."""
        resp = client.get("/")
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
        resp = client.get("/")
        assert "csrf_token" in resp.cookies

    def test_csrf_meta_tag_in_html(self, client: TestClient) -> None:
        """The base template includes a CSRF meta tag."""
        resp = client.get("/")
        assert 'name="csrf-token"' in resp.text

    def test_post_without_csrf_fails(self, client: TestClient) -> None:
        """POST to a view route without CSRF token returns 403."""
        # POST without CSRF token to a non-API route
        # The middleware should reject before the route handler runs
        resp = client.post("/", data={"dummy": "data"})
        assert resp.status_code == 403

    def test_post_with_valid_csrf_passes(self, client: TestClient) -> None:
        """POST with matching CSRF token in header passes validation."""
        # Get the CSRF token from cookie
        resp = client.get("/")
        token = resp.cookies.get("csrf_token", "")
        assert token, "No CSRF token cookie set"

        # POST with CSRF header — this may 404/405 since route might not exist yet,
        # but should NOT be 403 (CSRF failure)
        resp = client.post(
            "/sites",
            data={"url": "https://test.com", "csrf_token": token},
            cookies={"csrf_token": token},
        )
        # Should not be 403 — CSRF passed
        assert resp.status_code != 403

    def test_api_routes_exempt_from_csrf(self, client: TestClient) -> None:
        """POST to /api/* routes does NOT require CSRF."""
        resp = client.post(
            "/api/sites",
            json={"url": "https://api-test.com"},
        )
        # Should create successfully (201) — no CSRF block
        assert resp.status_code == 201


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

    def test_flash_cookie_round_trip(self, client: TestClient) -> None:
        """Flash message cookie can be read back via get_flashed_messages."""
        import json

        from ainews.api.flash import FLASH_COOKIE

        # Simulate setting a flash cookie and requesting a page
        flash_data = json.dumps({"text": "Created!", "category": "success"})
        resp = client.get("/", cookies={FLASH_COOKIE: flash_data})
        assert resp.status_code == 200
        # The flash partial should render the message text
        assert "Created!" in resp.text
