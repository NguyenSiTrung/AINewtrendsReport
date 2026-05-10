"""Tests for Phase 3: Dashboard & Health Pages.

Covers dashboard data rendering, health probes, and HTMX partial.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.run import Run
from ainews.models.site import Site


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


def _auth_cookies(client: TestClient, engine: Any) -> dict[str, str]:
    """Create admin, login, return auth cookies."""
    from ainews.api.auth import create_admin_user

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


# ── Dashboard ────────────────────────────────────────────


class TestDashboard:
    def test_dashboard_shows_stats(self, client: TestClient, engine: Any) -> None:
        """Dashboard displays run stats and site count."""
        # Seed some data
        with get_db_session(engine) as session:
            session.add(Site(url="https://a.com", priority=5))
            session.add(Site(url="https://b.com", priority=5))
            session.add(
                Run(
                    id="run-1",
                    status="completed",
                    triggered_by="api",
                )
            )
            session.add(
                Run(
                    id="run-2",
                    status="failed",
                    triggered_by="cli",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/", cookies=cookies)
        assert resp.status_code == 200
        html = resp.text
        # Check stats
        assert ">2<" in html  # Total Runs = 2
        assert ">50%" in html  # Success Rate = 50%
        assert "run-1" in html or "run-2" in html

    def test_dashboard_empty_state(self, client: TestClient, engine: Any) -> None:
        """Dashboard shows empty state when no runs exist."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/", cookies=cookies)
        assert resp.status_code == 200
        assert "No runs yet" in resp.text

    def test_dashboard_shows_recent_runs(self, client: TestClient, engine: Any) -> None:
        """Dashboard shows recent runs with status badges."""
        with get_db_session(engine) as session:
            for i in range(3):
                session.add(
                    Run(
                        id=f"run-{i}",
                        status="completed",
                        triggered_by="api",
                        created_at="2026-01-01T00:00:00Z",
                    )
                )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/", cookies=cookies)
        assert resp.status_code == 200
        assert "badge-success" in resp.text
        assert "100%" in resp.text  # All 3 completed


# ── Health Page ──────────────────────────────────────────


class TestHealthPage:
    def test_health_page_renders(self, client: TestClient, engine: Any) -> None:
        """Health page renders with component statuses."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/health", cookies=cookies)
        assert resp.status_code == 200
        html = resp.text
        assert "System Health" in html
        assert "Database" in html

    def test_health_page_requires_auth(self, client: TestClient) -> None:
        """Health page redirects to login without auth."""
        resp = client.get("/health", follow_redirects=False)
        assert resp.status_code == 303

    def test_health_probes_partial(self, client: TestClient, engine: Any) -> None:
        """HTMX partial returns health grid."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/health/probes", cookies=cookies)
        assert resp.status_code == 200
        html = resp.text
        assert "Database" in html
        # DB should be ok in test
        assert "OK" in html

    def test_health_db_ok(self, client: TestClient, engine: Any) -> None:
        """DB probe returns ok with in-memory SQLite."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/health/probes", cookies=cookies)
        assert "Database" in resp.text
        assert "badge-success" in resp.text
