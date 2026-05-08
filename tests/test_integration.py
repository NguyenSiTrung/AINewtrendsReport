"""Integration tests: API → Service → Celery task chain (eager mode)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.schedule import Schedule


@pytest.fixture()
def engine() -> Any:
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    eng.dispose = lambda: None  # type: ignore[assignment]
    return eng


@pytest.fixture()
def client(engine: Any) -> TestClient:
    from ainews.api.main import create_app

    app = create_app()
    app.state.engine = engine
    return TestClient(app, raise_server_exceptions=False)


class TestTriggerRunLifecycle:
    """Full trigger → run creation → query lifecycle via API."""

    def test_trigger_then_query_run(self, client: TestClient, engine: Any) -> None:
        """POST /trigger → GET /runs/{id} shows pending run."""
        with patch("ainews.services.pipeline.run_pipeline") as mock_task:
            resp = client.post(
                "/api/trigger",
                json={"topics": ["AI"], "timeframe_days": 7},
            )

        assert resp.status_code == 201
        run_id = resp.json()["run_id"]
        mock_task.delay.assert_called_once_with(run_id)

        # Query the run
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        detail = resp.json()["run"]
        assert detail["id"] == run_id
        assert detail["status"] == "pending"
        assert detail["triggered_by"] == "api"

    def test_trigger_schedule_then_list(self, client: TestClient, engine: Any) -> None:
        """Trigger via schedule, then list runs filtered by status."""
        with get_db_session(engine) as session:
            session.add(
                Schedule(
                    name="test-sched",
                    cron_expr="0 7 * * 1",
                    timeframe_days=14,
                    topics=["ML"],
                )
            )

        with patch("ainews.services.pipeline.run_pipeline"):
            client.post(
                "/api/trigger",
                json={"schedule_name": "test-sched"},
            )

        resp = client.get("/api/runs?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_site_schedule_then_trigger(self, client: TestClient, engine: Any) -> None:
        """Create site + schedule via CRUD, then trigger a run referencing them."""
        # Create site
        resp = client.post("/api/sites", json={"url": "https://test.com"})
        assert resp.status_code == 201

        # Create schedule
        resp = client.post(
            "/api/schedules",
            json={"name": "e2e-test", "cron_expr": "0 7 * * 1", "timeframe_days": 7},
        )
        assert resp.status_code == 201

        # Trigger with schedule
        with patch("ainews.services.pipeline.run_pipeline"):
            resp = client.post(
                "/api/trigger",
                json={"schedule_name": "e2e-test"},
            )

        assert resp.status_code == 201


class TestHealthE2E:
    """Health endpoint with real DB, mocked Valkey."""

    def test_health_db_ok_valkey_down(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["components"]["db"]["status"] == "ok"
        # Without real Valkey running, should be degraded
        if data["components"]["valkey"]["status"] == "down":
            assert data["status"] == "degraded"

    def test_health_all_ok_with_mocked_valkey(self, client: TestClient) -> None:
        import sys
        import types

        mock_redis_mod = types.ModuleType("redis")
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_mod.from_url = MagicMock(return_value=mock_redis_client)  # type: ignore[attr-defined]

        # Mock LLM connectivity check to return success
        mock_llm_result = MagicMock()
        mock_llm_result.success = True
        mock_llm_result.model_name = "test-model"
        mock_llm_result.latency_ms = 10.0

        with (
            patch.dict(sys.modules, {"redis": mock_redis_mod}),
            patch(
                "ainews.llm.connectivity.check_llm_connection",
                return_value=mock_llm_result,
            ),
        ):
            resp = client.get("/api/health")

        data = resp.json()
        assert data["status"] == "ok"
        assert data["components"]["valkey"]["status"] == "ok"
        assert data["components"]["llm"]["status"] == "ok"
