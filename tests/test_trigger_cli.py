"""Tests for the ainews trigger-run CLI command."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from ainews.cli import app
from ainews.core.config import Settings
from ainews.core.database import create_engine, get_db_session
from ainews.models import Base
from ainews.models.schedule import Schedule

runner = CliRunner()


def _make_engine() -> Any:
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    eng.dispose = lambda: None  # type: ignore[assignment]
    return eng


class TestTriggerRunCLI:
    def test_trigger_adhoc(self) -> None:
        """trigger-run with --topics creates a run."""
        engine = _make_engine()
        settings = Settings(valkey_url="redis://test:6379/0")

        with (
            patch("ainews.core.config.Settings", return_value=settings),
            patch("ainews.core.database.create_engine", return_value=engine),
            patch("ainews.services.pipeline.run_pipeline") as mock_task,
        ):
            result = runner.invoke(
                app, ["trigger-run", "--topics", "AI,ML", "--days", "7"]
            )

        assert result.exit_code == 0
        assert "Run enqueued" in result.output
        assert "triggered_by: cli" in result.output
        mock_task.delay.assert_called_once()

    def test_trigger_with_schedule(self) -> None:
        """trigger-run with --schedule resolves from DB."""
        engine = _make_engine()
        settings = Settings(valkey_url="redis://test:6379/0")

        # Seed schedule
        with get_db_session(engine) as session:
            session.add(
                Schedule(
                    name="weekly-ai",
                    cron_expr="0 7 * * 1",
                    timeframe_days=7,
                    topics=["AI"],
                )
            )

        with (
            patch("ainews.core.config.Settings", return_value=settings),
            patch("ainews.core.database.create_engine", return_value=engine),
            patch("ainews.services.pipeline.run_pipeline"),
        ):
            result = runner.invoke(app, ["trigger-run", "--schedule", "weekly-ai"])

        assert result.exit_code == 0
        assert "schedule: weekly-ai" in result.output

    def test_trigger_schedule_not_found(self) -> None:
        """trigger-run with unknown schedule exits with error."""
        engine = _make_engine()
        settings = Settings(valkey_url="redis://test:6379/0")

        with (
            patch("ainews.core.config.Settings", return_value=settings),
            patch("ainews.core.database.create_engine", return_value=engine),
            patch("ainews.services.pipeline.run_pipeline"),
        ):
            result = runner.invoke(app, ["trigger-run", "--schedule", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
