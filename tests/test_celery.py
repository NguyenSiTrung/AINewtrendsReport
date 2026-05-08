"""Tests for Celery app configuration and run_pipeline task."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ainews.core.config import Settings
from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.run import Run
from ainews.tasks.celery_app import make_celery


class TestCeleryApp:
    """Tests for Celery app factory and configuration."""

    def test_make_celery_default(self) -> None:
        """Factory creates a Celery app with correct broker config."""
        settings = Settings(valkey_url="redis://test:6379/0")
        app = make_celery(settings)

        assert app.main == "ainews"
        assert app.conf.broker_url == "redis://test:6379/0"
        assert app.conf.result_backend == "redis://test:6379/0"
        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert app.conf.timezone == "UTC"
        assert app.conf.enable_utc is True

    def test_queue_declarations(self) -> None:
        """All three queues are declared."""
        settings = Settings(valkey_url="redis://test:6379/0")
        app = make_celery(settings)

        queues = app.conf.task_queues
        assert "default" in queues
        assert "scrape" in queues
        assert "llm" in queues

    def test_default_queue(self) -> None:
        settings = Settings(valkey_url="redis://test:6379/0")
        app = make_celery(settings)
        assert app.conf.task_default_queue == "default"

    def test_autodiscover_includes(self) -> None:
        settings = Settings(valkey_url="redis://test:6379/0")
        app = make_celery(settings)
        assert "ainews.tasks.pipeline" in app.conf.include


class TestRunPipelineTask:
    """Tests for the run_pipeline Celery task with mocked graph."""

    @pytest.fixture()
    def engine(self) -> Any:
        """Create an in-memory DB with all tables."""
        eng = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(eng)
        # Prevent dispose() from closing the StaticPool shared connection
        eng.dispose = lambda: None  # type: ignore[assignment]
        return eng

    def test_run_not_found(self, engine: Any) -> None:
        """Task returns error when run_id doesn't exist in DB."""
        from ainews.tasks import pipeline

        with (
            patch.object(pipeline, "Settings", return_value=Settings(valkey_url="redis://t:6379/0")),
            patch.object(pipeline, "create_engine", return_value=engine),
        ):
            result = pipeline.run_pipeline("nonexistent-id")

        assert result["status"] == "error"
        assert "not found" in result["detail"].lower()

    def test_run_success(self, engine: Any) -> None:
        """Task transitions run through pending → running → completed."""
        from ainews.tasks import pipeline

        # Seed a pending run
        with get_db_session(engine) as session:
            run = Run(id="test-run-1", status="pending", triggered_by="api")
            run.input_params = {"topics": ["AI"], "timeframe_days": 7}
            session.add(run)

        mock_result: dict[str, Any] = {
            "metrics": {"articles_fetched": 5},
            "errors": [],
            "report_md": "# Test Report",
        }

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = mock_result

        mock_cp = MagicMock()

        with (
            patch.object(pipeline, "Settings", return_value=Settings(valkey_url="redis://t:6379/0")),
            patch.object(pipeline, "create_engine", return_value=engine),
            patch("ainews.agents.graph.build_graph", return_value=mock_graph),
            patch("langgraph.checkpoint.sqlite.SqliteSaver") as MockSaver,
        ):
            MockSaver.from_conn_string.return_value.__enter__ = MagicMock(
                return_value=mock_cp
            )
            MockSaver.from_conn_string.return_value.__exit__ = MagicMock(
                return_value=False
            )

            result = pipeline.run_pipeline("test-run-1")

        assert result["status"] == "completed"

        # Verify DB was updated
        with get_db_session(engine) as session:
            run_row = session.get(Run, "test-run-1")
            assert run_row is not None
            assert run_row.status == "completed"
            assert run_row.started_at is not None
            assert run_row.finished_at is not None
            assert run_row.stats == {"articles_fetched": 5}

    def test_run_failure(self, engine: Any) -> None:
        """Task captures exception and marks run as failed."""
        from ainews.tasks import pipeline

        with get_db_session(engine) as session:
            run = Run(id="fail-run", status="pending", triggered_by="cli")
            session.add(run)

        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("LLM timeout")

        with (
            patch.object(pipeline, "Settings", return_value=Settings(valkey_url="redis://t:6379/0")),
            patch.object(pipeline, "create_engine", return_value=engine),
            patch("ainews.agents.graph.build_graph", return_value=mock_graph),
            patch("langgraph.checkpoint.sqlite.SqliteSaver") as MockSaver,
        ):
            MockSaver.from_conn_string.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            MockSaver.from_conn_string.return_value.__exit__ = MagicMock(
                return_value=False
            )

            result = pipeline.run_pipeline("fail-run")

        assert result["status"] == "failed"
        assert "LLM timeout" in result["error"]

        with get_db_session(engine) as session:
            run_row = session.get(Run, "fail-run")
            assert run_row is not None
            assert run_row.status == "failed"
            assert run_row.error == "LLM timeout"
