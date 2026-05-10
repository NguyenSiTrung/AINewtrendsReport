"""Tests for Phase 4: Sites & Schedules CRUD Pages.

Covers list, create, edit routes for both sites and schedules.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.schedule import Schedule
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


# ── Sites ────────────────────────────────────────────────


class TestSitesPages:
    def test_sites_list_empty(self, client: TestClient, engine: Any) -> None:
        """Sites page shows empty state."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/sites", cookies=cookies)
        assert resp.status_code == 200
        assert "No sites configured" in resp.text

    def test_sites_list_with_data(self, client: TestClient, engine: Any) -> None:
        """Sites page lists existing sites."""
        with get_db_session(engine) as session:
            session.add(Site(url="https://test.com/ai", priority=8))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/sites", cookies=cookies)
        assert resp.status_code == 200
        assert "test.com" in resp.text

    def test_site_new_form(self, client: TestClient, engine: Any) -> None:
        """New site form renders."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/sites/new", cookies=cookies)
        assert resp.status_code == 200
        assert "New Site" in resp.text

    def test_site_create(self, client: TestClient, engine: Any) -> None:
        """POST /sites/new creates a site and redirects."""
        cookies = _auth_cookies(client, engine)
        resp = client.post(
            "/sites/new",
            data={
                "url": "https://new-site.com",
                "category": "tech",
                "priority": "7",
                "csrf_token": cookies["csrf_token"],
            },
            headers={"x-csrf-token": cookies["csrf_token"]},
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/sites"

        # Verify it was created
        with get_db_session(engine) as session:
            from sqlalchemy import select

            site = session.execute(
                select(Site).where(Site.url == "https://new-site.com")
            ).scalar_one()
            assert site.priority == 7

    def test_site_edit_form(self, client: TestClient, engine: Any) -> None:
        """Edit site form shows existing data."""
        with get_db_session(engine) as session:
            session.add(Site(url="https://edit-me.com", priority=5))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/sites/1/edit", cookies=cookies)
        assert resp.status_code == 200
        assert "edit-me.com" in resp.text
        assert "Edit Site" in resp.text

    def test_site_update(self, client: TestClient, engine: Any) -> None:
        """POST /sites/:id updates the site."""
        with get_db_session(engine) as session:
            session.add(Site(url="https://old.com", priority=3))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.post(
            "/sites/1",
            data={
                "url": "https://updated.com",
                "category": "research",
                "priority": "9",
                "csrf_token": cookies["csrf_token"],
            },
            headers={"x-csrf-token": cookies["csrf_token"]},
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303

        with get_db_session(engine) as session:
            site = session.get(Site, 1)
            assert site is not None
            assert site.url == "https://updated.com"
            assert site.priority == 9

    def test_sites_requires_auth(self, client: TestClient) -> None:
        """Sites page redirects without auth."""
        resp = client.get("/sites", follow_redirects=False)
        assert resp.status_code == 303


# ── Schedules ────────────────────────────────────────────


class TestSchedulesPages:
    def test_schedules_list_empty(self, client: TestClient, engine: Any) -> None:
        """Schedules page shows empty state."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/schedules", cookies=cookies)
        assert resp.status_code == 200
        assert "No schedules configured" in resp.text

    def test_schedules_list_with_data(self, client: TestClient, engine: Any) -> None:
        """Schedules page lists existing schedules."""
        with get_db_session(engine) as session:
            session.add(
                Schedule(
                    name="weekly-ai",
                    cron_expr="0 7 * * 1",
                    timeframe_days=7,
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/schedules", cookies=cookies)
        assert resp.status_code == 200
        assert "weekly-ai" in resp.text

    def test_schedule_create(self, client: TestClient, engine: Any) -> None:
        """POST /schedules/new creates a schedule."""
        cookies = _auth_cookies(client, engine)
        resp = client.post(
            "/schedules/new",
            data={
                "name": "daily-ml",
                "cron_expr": "0 8 * * *",
                "timeframe_days": "1",
                "csrf_token": cookies["csrf_token"],
            },
            headers={"x-csrf-token": cookies["csrf_token"]},
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303

        with get_db_session(engine) as session:
            from sqlalchemy import select

            sched = session.execute(
                select(Schedule).where(Schedule.name == "daily-ml")
            ).scalar_one()
            assert sched.cron_expr == "0 8 * * *"

    def test_schedule_edit_form(self, client: TestClient, engine: Any) -> None:
        """Edit form shows existing schedule data."""
        with get_db_session(engine) as session:
            session.add(
                Schedule(
                    name="edit-me",
                    cron_expr="0 0 * * *",
                    timeframe_days=3,
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/schedules/1/edit", cookies=cookies)
        assert resp.status_code == 200
        assert "edit-me" in resp.text
        assert "Edit Schedule" in resp.text

    def test_schedule_update(self, client: TestClient, engine: Any) -> None:
        """POST /schedules/:id updates the schedule."""
        with get_db_session(engine) as session:
            session.add(
                Schedule(
                    name="old-name",
                    cron_expr="0 0 * * *",
                    timeframe_days=7,
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.post(
            "/schedules/1",
            data={
                "name": "new-name",
                "cron_expr": "0 12 * * 1-5",
                "timeframe_days": "14",
                "csrf_token": cookies["csrf_token"],
            },
            headers={"x-csrf-token": cookies["csrf_token"]},
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303

        with get_db_session(engine) as session:
            sched = session.get(Schedule, 1)
            assert sched is not None
            assert sched.name == "new-name"
            assert sched.timeframe_days == 14
