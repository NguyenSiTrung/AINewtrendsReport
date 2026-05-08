"""Tests for Phase 5-7: Trigger, LLM Settings, Runs, Logs, Settings.

Covers all remaining admin UI pages.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.run import Run
from ainews.models.run_log import RunLog
from ainews.models.schedule import Schedule


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
        cookies={"csrf_token": csrf},
        follow_redirects=False,
    )
    return {
        "access_token": resp.cookies.get("access_token", ""),
        "csrf_token": resp.cookies.get("csrf_token", csrf),
    }


# ── Trigger ──────────────────────────────────────────────


class TestTriggerPage:
    def test_trigger_page_renders(self, client: TestClient, engine: Any) -> None:
        """Trigger page shows form."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/trigger", cookies=cookies)
        assert resp.status_code == 200
        assert "Trigger Run" in resp.text
        assert "Start Pipeline Run" in resp.text

    def test_trigger_lists_schedules(self, client: TestClient, engine: Any) -> None:
        """Trigger page shows available schedules."""
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
        resp = client.get("/trigger", cookies=cookies)
        assert "weekly-ai" in resp.text

    def test_trigger_requires_auth(self, client: TestClient) -> None:
        """Trigger page redirects without auth."""
        resp = client.get("/trigger", follow_redirects=False)
        assert resp.status_code == 303


# ── LLM Settings ─────────────────────────────────────────


class TestLLMSettings:
    def test_llm_page_renders(self, client: TestClient, engine: Any) -> None:
        """LLM settings page renders form."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/llm", cookies=cookies)
        assert resp.status_code == 200
        assert "LLM Settings" in resp.text
        assert "Base URL" in resp.text

    def test_llm_save_settings(self, client: TestClient, engine: Any) -> None:
        """POST /llm saves settings to DB."""
        cookies = _auth_cookies(client, engine)
        resp = client.post(
            "/llm",
            data={
                "base_url": "http://localhost:11434/v1",
                "model": "llama3.1",
                "api_key": "sk-test123",
                "temperature": "0.5",
                "max_tokens": "8000",
                "csrf_token": cookies["csrf_token"],
            },
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303

        # Verify settings were saved
        from ainews.models.settings_kv import SettingsKV

        with get_db_session(engine) as session:
            row = session.get(SettingsKV, "llm")
            assert row is not None
            assert row.value["model"] == "llama3.1"
            assert row.value["api_key"] == "sk-test123"

    def test_llm_preserves_api_key(self, client: TestClient, engine: Any) -> None:
        """POST /llm without api_key preserves existing key."""
        from ainews.models.settings_kv import SettingsKV

        with get_db_session(engine) as session:
            session.add(
                SettingsKV(
                    key="llm",
                    value={
                        "base_url": "http://old",
                        "model": "old",
                        "api_key": "sk-secret",
                    },
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        client.post(
            "/llm",
            data={
                "base_url": "http://new",
                "model": "new-model",
                "api_key": "",
                "temperature": "0.3",
                "max_tokens": "4096",
                "csrf_token": cookies["csrf_token"],
            },
            cookies=cookies,
            follow_redirects=False,
        )

        with get_db_session(engine) as session:
            row = session.get(SettingsKV, "llm")
            assert row is not None
            assert row.value["api_key"] == "sk-secret"
            assert row.value["model"] == "new-model"


# ── Runs ─────────────────────────────────────────────────


class TestRunsPages:
    def test_runs_list_renders(self, client: TestClient, engine: Any) -> None:
        """Runs list page shows runs."""
        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="test-run-001",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs", cookies=cookies)
        assert resp.status_code == 200
        assert "test-run-001" in resp.text

    def test_run_detail_renders(self, client: TestClient, engine: Any) -> None:
        """Run detail page shows run info and logs."""
        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="detail-run",
                    status="completed",
                    triggered_by="cli",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.add(
                RunLog(
                    run_id="detail-run",
                    node="searcher",
                    level="INFO",
                    message="Pipeline started",
                    ts="2026-01-01T00:00:01Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/detail-run", cookies=cookies)
        assert resp.status_code == 200
        assert "detail-run" in resp.text
        assert "Pipeline started" in resp.text

    def test_run_detail_not_found(self, client: TestClient, engine: Any) -> None:
        """Missing run redirects to runs list."""
        cookies = _auth_cookies(client, engine)
        resp = client.get(
            "/runs/nonexistent",
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303


# ── Logs ─────────────────────────────────────────────────


class TestLogsPage:
    def test_logs_page_renders(self, client: TestClient, engine: Any) -> None:
        """Logs page shows log entries."""
        with get_db_session(engine) as session:
            session.add(Run(id="log-run", status="running"))
            session.add(
                RunLog(
                    run_id="log-run",
                    node="writer",
                    level="ERROR",
                    message="Something broke",
                    ts="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/logs", cookies=cookies)
        assert resp.status_code == 200
        assert "Something broke" in resp.text
        assert "log-error" in resp.text


# ── Settings ─────────────────────────────────────────────


class TestSettingsPage:
    def test_settings_page_renders(self, client: TestClient, engine: Any) -> None:
        """Settings page shows system info."""
        cookies = _auth_cookies(client, engine)
        resp = client.get("/settings", cookies=cookies)
        assert resp.status_code == 200
        assert "Settings" in resp.text
        assert "System Information" in resp.text

    def test_settings_seed(self, client: TestClient, engine: Any) -> None:
        """POST /settings/seed runs seed and redirects."""
        cookies = _auth_cookies(client, engine)
        resp = client.post(
            "/settings/seed",
            data={"csrf_token": cookies["csrf_token"]},
            cookies=cookies,
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/settings"
