"""Tests for Report Preview & Download feature.

Covers:
- Pipeline → Report persistence (Phase 1)
- Report summary card on run detail (Phase 2)
- Report preview page & download endpoints (Phase 3)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ainews.core.config import Settings
from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.report import Report
from ainews.models.run import Run

# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture()
def engine() -> Any:
    """In-memory SQLite engine with all tables."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def non_dispose_engine(engine: Any) -> Any:
    """Engine that won't dispose (for pipeline task tests)."""
    engine.dispose = lambda: None  # type: ignore[assignment]
    return engine


@pytest.fixture()
def client(engine: Any) -> TestClient:
    """FastAPI test client."""
    from ainews.api.main import create_app

    app = create_app()
    app.state.engine = engine
    return TestClient(app, raise_server_exceptions=False)


def _auth_cookies(client: TestClient, engine: Any) -> dict[str, str]:
    """Create admin user, login, return auth cookies."""
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


# ── Phase 1: Pipeline → Report Persistence ──────────────


class TestPipelineReportCreation:
    """Verify run_pipeline creates Report row on success."""

    def test_report_created_on_success(
        self, non_dispose_engine: Any, tmp_path: Path
    ) -> None:
        """Successful pipeline run creates a Report row with correct fields."""
        from ainews.tasks import pipeline

        engine = non_dispose_engine

        with get_db_session(engine) as session:
            run = Run(id="report-run-1", status="pending", triggered_by="api")
            run.input_params = {"topics": ["AI"], "timeframe_days": 7}
            session.add(run)

        mock_result: dict[str, Any] = {
            "metrics": {"articles_fetched": 5},
            "errors": [],
            "report_md": "# AI News Report\n\nExecutive summary here.",
            "summaries": [
                {"headline": "Story 1", "bullets": ["p1"], "sources": ["http://a.com"]}
            ],
            "trends": [{"name": "Trend A", "description": "Desc A"}],
            "xlsx_path": str(tmp_path / "report-run-1" / "report.xlsx"),
        }

        # Pre-create the xlsx file so export check passes
        xlsx_dir = tmp_path / "report-run-1"
        xlsx_dir.mkdir(parents=True, exist_ok=True)
        (xlsx_dir / "report.xlsx").write_bytes(b"fake xlsx")

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = mock_result

        settings_with_path = Settings(valkey_url="redis://t:6379/0")

        with (
            patch.object(pipeline, "Settings", return_value=settings_with_path),
            patch.object(pipeline, "create_engine", return_value=engine),
            patch("ainews.agents.graph.build_graph", return_value=mock_graph),
            patch("langgraph.checkpoint.sqlite.SqliteSaver") as mock_saver,
            patch(
                "ainews.tasks.pipeline.export_markdown",
                return_value=tmp_path / "report-run-1" / "report.md",
            ),
            patch(
                "ainews.tasks.pipeline.export_xlsx",
                return_value=tmp_path / "report-run-1" / "report.xlsx",
            ),
        ):
            mock_saver.from_conn_string.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_saver.from_conn_string.return_value.__exit__ = MagicMock(
                return_value=False
            )

            result = pipeline.run_pipeline("report-run-1")

        assert result["status"] == "completed"

        # Verify Report row was created
        with get_db_session(engine) as session:
            report = session.query(Report).filter_by(run_id="report-run-1").first()
            assert report is not None
            assert report.full_md_path is not None
            assert report.xlsx_path is not None
            assert report.summary_md is not None
            assert report.title is not None
            assert report.trends is not None
            assert report.created_at is not None

    def test_no_report_on_failure(self, non_dispose_engine: Any) -> None:
        """Failed pipeline run does NOT create a Report row."""
        from ainews.tasks import pipeline

        engine = non_dispose_engine

        with get_db_session(engine) as session:
            run = Run(id="fail-report-run", status="pending", triggered_by="cli")
            session.add(run)

        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("boom")

        with (
            patch.object(
                pipeline,
                "Settings",
                return_value=Settings(valkey_url="redis://t:6379/0"),
            ),
            patch.object(pipeline, "create_engine", return_value=engine),
            patch("ainews.agents.graph.build_graph", return_value=mock_graph),
            patch("langgraph.checkpoint.sqlite.SqliteSaver") as mock_saver,
        ):
            mock_saver.from_conn_string.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_saver.from_conn_string.return_value.__exit__ = MagicMock(
                return_value=False
            )

            result = pipeline.run_pipeline("fail-report-run")

        assert result["status"] == "failed"

        with get_db_session(engine) as session:
            report = session.query(Report).filter_by(run_id="fail-report-run").first()
            assert report is None


# ── Phase 2: Report Summary Card on Run Detail ──────────


class TestReportSummaryCard:
    """Verify run detail page shows report card when Report exists."""

    def test_detail_shows_report_card(self, client: TestClient, engine: Any) -> None:
        """Run detail includes report summary card when Report row exists."""
        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="run-with-report",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        with get_db_session(engine) as session:
            session.add(
                Report(
                    run_id="run-with-report",
                    title="AI News Report — 2026-01-01",
                    summary_md="Executive summary of the report with key findings.",
                    full_md_path="/tmp/reports/run-with-report/report.md",
                    xlsx_path="/tmp/reports/run-with-report/report.xlsx",
                    trends=[{"name": "Trend A"}, {"name": "Trend B"}],
                    created_at="2026-01-01T00:00:05Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/run-with-report", cookies=cookies)
        assert resp.status_code == 200
        assert "AI News Report" in resp.text
        assert "View Full Report" in resp.text
        assert "Download" in resp.text

    def test_detail_no_report_section(self, client: TestClient, engine: Any) -> None:
        """Run detail omits report section when no Report row exists."""
        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="run-no-report",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/run-no-report", cookies=cookies)
        assert resp.status_code == 200
        assert "View Full Report" not in resp.text


# ── Phase 3: Report Preview Page ─────────────────────────


class TestReportPreviewPage:
    """Verify /runs/{run_id}/report renders markdown as HTML."""

    def test_preview_renders_html(
        self, client: TestClient, engine: Any, tmp_path: Path
    ) -> None:
        """GET /runs/{run_id}/report converts markdown file to HTML."""
        # Create md file on disk
        md_file = tmp_path / "report.md"
        md_file.write_text("# Test Report\n\nSome **bold** text.", encoding="utf-8")

        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="preview-run",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        with get_db_session(engine) as session:
            session.add(
                Report(
                    run_id="preview-run",
                    title="Test Report",
                    full_md_path=str(md_file),
                    created_at="2026-01-01T00:00:05Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/preview-run/report", cookies=cookies)
        assert resp.status_code == 200
        assert "<h1>" in resp.text or "<h1" in resp.text
        assert "<strong>bold</strong>" in resp.text

    def test_preview_404_no_report(self, client: TestClient, engine: Any) -> None:
        """GET /runs/{run_id}/report returns 404 when no Report exists."""
        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="no-report-run",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get(
            "/runs/no-report-run/report",
            cookies=cookies,
            follow_redirects=False,
        )
        # Should redirect back or return 404
        assert resp.status_code in (303, 404)

    def test_preview_requires_auth(self, client: TestClient) -> None:
        """Report preview page redirects without auth."""
        resp = client.get("/runs/some-id/report", follow_redirects=False)
        assert resp.status_code == 303


# ── Phase 3: File Download Endpoints ─────────────────────


class TestFileDownloads:
    """Verify download endpoints serve files correctly."""

    def test_download_md(self, client: TestClient, engine: Any, tmp_path: Path) -> None:
        """GET .../download/md returns the markdown file."""
        md_file = tmp_path / "report.md"
        md_file.write_text("# Report Content", encoding="utf-8")

        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="dl-md-run",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        with get_db_session(engine) as session:
            session.add(
                Report(
                    run_id="dl-md-run",
                    full_md_path=str(md_file),
                    created_at="2026-01-01T00:00:05Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/dl-md-run/report/download/md", cookies=cookies)
        assert resp.status_code == 200
        assert "# Report Content" in resp.text
        assert "content-disposition" in resp.headers

    def test_download_xlsx(
        self, client: TestClient, engine: Any, tmp_path: Path
    ) -> None:
        """GET .../download/xlsx returns the xlsx file."""
        xlsx_file = tmp_path / "report.xlsx"
        xlsx_file.write_bytes(b"PK\x03\x04fake xlsx content")

        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="dl-xlsx-run",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        with get_db_session(engine) as session:
            session.add(
                Report(
                    run_id="dl-xlsx-run",
                    xlsx_path=str(xlsx_file),
                    created_at="2026-01-01T00:00:05Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)
        resp = client.get("/runs/dl-xlsx-run/report/download/xlsx", cookies=cookies)
        assert resp.status_code == 200
        assert "content-disposition" in resp.headers

    def test_download_404_missing_file(self, client: TestClient, engine: Any) -> None:
        """Download returns 404 when file doesn't exist on disk."""
        with get_db_session(engine) as session:
            session.add(
                Run(
                    id="dl-missing-run",
                    status="completed",
                    triggered_by="api",
                    created_at="2026-01-01T00:00:00Z",
                )
            )
            session.commit()

        with get_db_session(engine) as session:
            session.add(
                Report(
                    run_id="dl-missing-run",
                    full_md_path="/nonexistent/report.md",
                    xlsx_path="/nonexistent/report.xlsx",
                    created_at="2026-01-01T00:00:05Z",
                )
            )
            session.commit()

        cookies = _auth_cookies(client, engine)

        resp_md = client.get("/runs/dl-missing-run/report/download/md", cookies=cookies)
        assert resp_md.status_code == 404

        resp_xlsx = client.get(
            "/runs/dl-missing-run/report/download/xlsx", cookies=cookies
        )
        assert resp_xlsx.status_code == 404

    def test_download_requires_auth(self, client: TestClient) -> None:
        """Download endpoints redirect without auth."""
        resp = client.get("/runs/some-id/report/download/md", follow_redirects=False)
        assert resp.status_code == 303

        resp = client.get("/runs/some-id/report/download/xlsx", follow_redirects=False)
        assert resp.status_code == 303
