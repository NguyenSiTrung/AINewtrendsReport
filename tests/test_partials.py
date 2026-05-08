"""Tests for HTMX polling partial endpoints.

Covers: stepper partial, logs partial, runs table partial.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.run import Run
from ainews.models.run_log import RunLog


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


def _auth_cookies(
    client: TestClient, engine: Any,
) -> dict[str, str]:
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
        cookies={"csrf_token": csrf},
        follow_redirects=False,
    )
    return {
        "access_token": resp.cookies.get("access_token", ""),
        "csrf_token": resp.cookies.get("csrf_token", csrf),
    }


def _seed_run_with_logs(engine: Any) -> str:
    """Create a run with sample logs and return run_id."""
    run_id = "stepper-test-run"
    with get_db_session(engine) as session:
        session.add(Run(
            id=run_id,
            status="running",
            triggered_by="test",
            created_at="2026-01-01T00:00:00Z",
        ))
        session.add(RunLog(
            run_id=run_id,
            node="planner",
            level="INFO",
            message="Node started",
            ts="2026-01-01T00:00:01Z",
        ))
        session.add(RunLog(
            run_id=run_id,
            node="planner",
            level="INFO",
            message="Node completed",
            ts="2026-01-01T00:00:02Z",
        ))
        session.add(RunLog(
            run_id=run_id,
            node="retriever",
            level="INFO",
            message="Node started",
            ts="2026-01-01T00:00:03Z",
        ))
        session.commit()
    return run_id


class TestStepperPartial:
    """Tests for GET /runs/{run_id}/stepper."""

    def test_stepper_returns_node_states(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Stepper partial shows correct node states."""
        run_id = _seed_run_with_logs(engine)
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/stepper", cookies=cookies,
        )
        assert resp.status_code == 200
        # Planner completed, retriever running
        assert "stepper-completed" in resp.text
        assert "stepper-running" in resp.text
        assert "stepper-pending" in resp.text

    def test_stepper_shows_failed_state(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Stepper shows failed state for error logs."""
        run_id = "fail-run"
        with get_db_session(engine) as session:
            session.add(Run(
                id=run_id, status="failed",
                triggered_by="test",
            ))
            session.add(RunLog(
                run_id=run_id,
                node="scraper",
                level="ERROR",
                message="Node failed: timeout",
                ts="2026-01-01T00:00:01Z",
            ))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/stepper", cookies=cookies,
        )
        assert resp.status_code == 200
        assert "stepper-failed" in resp.text

    def test_stepper_includes_polling_for_active(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Stepper includes hx-trigger for active runs."""
        run_id = _seed_run_with_logs(engine)
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/stepper", cookies=cookies,
        )
        assert "hx-trigger" in resp.text
        assert "every 2s" in resp.text

    def test_stepper_no_polling_for_completed(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Stepper omits hx-trigger for terminal runs."""
        run_id = "done-run"
        with get_db_session(engine) as session:
            session.add(Run(
                id=run_id, status="completed",
                triggered_by="test",
            ))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/stepper", cookies=cookies,
        )
        assert "hx-trigger" not in resp.text

    def test_stepper_requires_auth(
        self, client: TestClient,
    ) -> None:
        """Stepper endpoint redirects without auth."""
        resp = client.get(
            "/runs/some-id/stepper",
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_stepper_not_found(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Stepper returns empty for non-existent run."""
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            "/runs/nonexistent/stepper", cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.text == ""


class TestLogsPartial:
    """Tests for GET /runs/{run_id}/logs-partial."""

    def test_logs_returns_entries(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Logs partial shows RunLog entries."""
        run_id = _seed_run_with_logs(engine)
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/logs-partial", cookies=cookies,
        )
        assert resp.status_code == 200
        assert "Node started" in resp.text
        assert "Node completed" in resp.text
        assert "planner" in resp.text

    def test_logs_ordered_by_timestamp(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Logs partial returns entries ordered by ts."""
        run_id = _seed_run_with_logs(engine)
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/logs-partial", cookies=cookies,
        )
        text = resp.text
        # "started" should appear before "completed"
        started_pos = text.find("Node started")
        completed_pos = text.find("Node completed")
        assert started_pos < completed_pos

    def test_logs_requires_auth(
        self, client: TestClient,
    ) -> None:
        """Logs partial redirects without auth."""
        resp = client.get(
            "/runs/some-id/logs-partial",
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_logs_includes_polling_for_active(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Logs partial includes hx-trigger for active runs."""
        run_id = _seed_run_with_logs(engine)
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            f"/runs/{run_id}/logs-partial", cookies=cookies,
        )
        assert "hx-trigger" in resp.text


class TestRunsTablePartial:
    """Tests for GET /runs/table."""

    def test_table_shows_runs(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Runs table partial lists runs."""
        with get_db_session(engine) as session:
            session.add(Run(
                id="table-run-1",
                status="completed",
                triggered_by="api",
                created_at="2026-01-01T00:00:00Z",
            ))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/table", cookies=cookies)
        assert resp.status_code == 200
        assert "table-run-1" in resp.text

    def test_table_polling_when_active(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Runs table includes polling when active runs."""
        with get_db_session(engine) as session:
            session.add(Run(
                id="active-run",
                status="running",
                triggered_by="api",
            ))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/table", cookies=cookies)
        assert "hx-trigger" in resp.text
        assert "every 5s" in resp.text

    def test_table_no_polling_all_complete(
        self, client: TestClient, engine: Any,
    ) -> None:
        """Runs table omits polling when all runs terminal."""
        with get_db_session(engine) as session:
            session.add(Run(
                id="done-run",
                status="completed",
                triggered_by="api",
            ))
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/table", cookies=cookies)
        assert "hx-trigger" not in resp.text

    def test_table_requires_auth(
        self, client: TestClient,
    ) -> None:
        """Runs table redirects without auth."""
        resp = client.get(
            "/runs/table", follow_redirects=False,
        )
        assert resp.status_code == 303


class TestDeriveNodeStates:
    """Unit tests for _derive_node_states()."""

    def test_empty_logs(self) -> None:
        """Empty logs returns empty states."""
        from ainews.api.routes.views import _derive_node_states

        assert _derive_node_states([]) == {}

    def test_started_is_running(self) -> None:
        """Node with only 'started' log is running."""
        from ainews.api.routes.views import _derive_node_states

        from types import SimpleNamespace

        log = SimpleNamespace(
            node="planner", level="INFO",
            message="Node started",
        )
        states = _derive_node_states([log])
        assert states["planner"] == "running"

    def test_completed_overrides_running(self) -> None:
        """Node with 'completed' log overrides running."""
        from ainews.api.routes.views import _derive_node_states

        from types import SimpleNamespace

        logs = [
            SimpleNamespace(
                node="planner", level="INFO",
                message="Node started",
            ),
            SimpleNamespace(
                node="planner", level="INFO",
                message="Node completed",
            ),
        ]
        states = _derive_node_states(logs)
        assert states["planner"] == "completed"

    def test_error_is_failed(self) -> None:
        """ERROR level log marks node as failed."""
        from ainews.api.routes.views import _derive_node_states

        from types import SimpleNamespace

        log = SimpleNamespace(
            node="scraper", level="ERROR",
            message="Node failed: timeout",
        )
        states = _derive_node_states([log])
        assert states["scraper"] == "failed"

    def test_failed_not_overridden(self) -> None:
        """Failed state not overridden by completed."""
        from ainews.api.routes.views import _derive_node_states

        from types import SimpleNamespace

        logs = [
            SimpleNamespace(
                node="scraper", level="ERROR",
                message="Node failed",
            ),
            SimpleNamespace(
                node="scraper", level="INFO",
                message="Node completed",
            ),
        ]
        states = _derive_node_states(logs)
        assert states["scraper"] == "failed"
