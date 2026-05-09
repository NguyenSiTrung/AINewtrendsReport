"""Tests for all FastAPI routers using TestClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine
from ainews.models import Base
from ainews.models.run import Run
from ainews.models.schedule import Schedule


@pytest.fixture()
def engine() -> Any:
    """In-memory SQLite engine with all tables."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def _seed_admin_and_get_token(engine: Any) -> str:
    """Create an admin user and return a valid JWT token."""
    from ainews.api.auth import create_access_token, create_admin_user
    from ainews.core.database import get_db_session

    with get_db_session(engine) as session:
        user = create_admin_user(session, "admin@test.com", "pass123")
        session.commit()
        user_id = user.id

    return create_access_token(user_id, "admin@test.com")


@pytest.fixture()
def client(engine: Any) -> TestClient:
    """FastAPI test client with overridden DB engine and auth cookies."""
    from ainews.api.main import create_app

    app = create_app()
    app.state.engine = engine

    token = _seed_admin_and_get_token(engine)
    tc = TestClient(app, raise_server_exceptions=False, cookies={"access_token": token})
    return tc


# ── Health ────────────────────────────────────────────────


class TestHealthRouter:
    def test_health_ok(self, client: TestClient) -> None:
        """Health returns ok when DB is accessible."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["components"]["db"]["status"] == "ok"
        # Valkey is likely down in test, so overall may be degraded
        assert data["status"] in ("ok", "degraded")

    def test_health_valkey_down(self, client: TestClient) -> None:
        """Valkey being unavailable should yield degraded status."""
        resp = client.get("/api/health")
        data = resp.json()
        # In CI without Valkey, this should be degraded
        if data["components"]["valkey"]["status"] == "down":
            assert data["status"] == "degraded"


# ── Trigger ───────────────────────────────────────────────


class TestTriggerRouter:
    def test_trigger_adhoc(self, client: TestClient) -> None:
        """Trigger with inline params creates a pending run."""
        with patch("ainews.services.pipeline.run_pipeline") as mock_task:
            resp = client.post(
                "/api/trigger",
                json={"topics": ["AI"], "timeframe_days": 7},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert "run_id" in data
        mock_task.delay.assert_called_once()

    def test_trigger_schedule_not_found(self, client: TestClient) -> None:
        """Trigger with unknown schedule returns 400."""
        with patch("ainews.services.pipeline.run_pipeline"):
            resp = client.post(
                "/api/trigger",
                json={"schedule_name": "nonexistent"},
            )

        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_trigger_with_schedule(self, client: TestClient, engine: Any) -> None:
        """Trigger with valid schedule_name resolves config."""
        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            session.add(
                Schedule(
                    name="weekly-ai",
                    cron_expr="0 7 * * 1",
                    timeframe_days=7,
                    topics=["AI"],
                )
            )

        with patch("ainews.services.pipeline.run_pipeline"):
            resp = client.post(
                "/api/trigger",
                json={"schedule_name": "weekly-ai"},
            )

        assert resp.status_code == 201


# ── Runs ──────────────────────────────────────────────────


class TestRunsRouter:
    def _seed_runs(self, engine: Any) -> None:
        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            for i in range(5):
                session.add(
                    Run(
                        id=f"run-{i}",
                        status="completed" if i < 3 else "pending",
                        triggered_by="api",
                        created_at=f"2026-01-0{i + 1}T00:00:00Z",
                    )
                )

    def test_list_runs(self, client: TestClient, engine: Any) -> None:
        self._seed_runs(engine)
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["runs"]) == 5

    def test_list_runs_pagination(self, client: TestClient, engine: Any) -> None:
        self._seed_runs(engine)
        resp = client.get("/api/runs?offset=2&limit=2")
        data = resp.json()
        assert len(data["runs"]) == 2
        assert data["offset"] == 2

    def test_list_runs_filter_status(self, client: TestClient, engine: Any) -> None:
        self._seed_runs(engine)
        resp = client.get("/api/runs?status=pending")
        data = resp.json()
        assert data["total"] == 2
        assert all(r["status"] == "pending" for r in data["runs"])

    def test_get_run(self, client: TestClient, engine: Any) -> None:
        self._seed_runs(engine)
        resp = client.get("/api/runs/run-0")
        assert resp.status_code == 200
        assert resp.json()["run"]["id"] == "run-0"

    def test_get_run_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404


# ── Sites CRUD ────────────────────────────────────────────


class TestSitesRouter:
    def test_crud_lifecycle(self, client: TestClient) -> None:
        """Full create → read → update → delete cycle."""
        # Create
        resp = client.post(
            "/api/sites",
            json={"url": "https://example.com", "priority": 8},
        )
        assert resp.status_code == 201
        site_id = resp.json()["id"]

        # Read
        resp = client.get(f"/api/sites/{site_id}")
        assert resp.status_code == 200
        assert resp.json()["priority"] == 8

        # Update
        resp = client.put(
            f"/api/sites/{site_id}",
            json={"priority": 3},
        )
        assert resp.status_code == 200
        assert resp.json()["priority"] == 3

        # Delete
        resp = client.delete(f"/api/sites/{site_id}")
        assert resp.status_code == 204

        # Verify gone
        resp = client.get(f"/api/sites/{site_id}")
        assert resp.status_code == 404

    def test_list_sites(self, client: TestClient) -> None:
        client.post("/api/sites", json={"url": "https://a.com"})
        client.post("/api/sites", json={"url": "https://b.com"})
        resp = client.get("/api/sites")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_duplicate_url_409(self, client: TestClient) -> None:
        client.post("/api/sites", json={"url": "https://dup.com"})
        resp = client.post("/api/sites", json={"url": "https://dup.com"})
        assert resp.status_code == 409

    def test_bad_url_422(self, client: TestClient) -> None:
        resp = client.post("/api/sites", json={"url": "not-a-url"})
        assert resp.status_code == 422

    def test_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/sites/999")
        assert resp.status_code == 404


# ── Schedules CRUD ────────────────────────────────────────


class TestSchedulesRouter:
    def test_crud_lifecycle(self, client: TestClient) -> None:
        """Full create → read → update → delete cycle."""
        # Create
        resp = client.post(
            "/api/schedules",
            json={"name": "weekly", "cron_expr": "0 7 * * 1"},
        )
        assert resp.status_code == 201
        sched_id = resp.json()["id"]

        # Read
        resp = client.get(f"/api/schedules/{sched_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "weekly"

        # Update
        resp = client.put(
            f"/api/schedules/{sched_id}",
            json={"timeframe_days": 30},
        )
        assert resp.status_code == 200
        assert resp.json()["timeframe_days"] == 30

        # Delete
        resp = client.delete(f"/api/schedules/{sched_id}")
        assert resp.status_code == 204

        # Verify gone
        resp = client.get(f"/api/schedules/{sched_id}")
        assert resp.status_code == 404

    def test_bad_cron_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/schedules",
            json={"name": "bad", "cron_expr": "not-cron"},
        )
        assert resp.status_code == 422

    def test_duplicate_name_409(self, client: TestClient) -> None:
        client.post(
            "/api/schedules",
            json={"name": "dup", "cron_expr": "0 7 * * 1"},
        )
        resp = client.post(
            "/api/schedules",
            json={"name": "dup", "cron_expr": "0 8 * * 1"},
        )
        assert resp.status_code == 409
