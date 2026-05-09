"""Tests for the pipeline service layer."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from ainews.core.database import create_engine, get_db_session, make_session_factory
from ainews.models import Base
from ainews.models.run import Run
from ainews.models.run_log import RunLog
from ainews.models.schedule import Schedule


@pytest.fixture()
def engine() -> Any:
    """In-memory SQLite with all tables created."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


class TestCreateAndEnqueueRun:
    """Tests for create_and_enqueue_run service function."""

    def test_adhoc_run(self, engine: Any) -> None:
        """Create a run with inline params, no schedule."""
        from ainews.services.pipeline import create_and_enqueue_run

        with (
            patch("ainews.services.pipeline.run_pipeline") as mock_task,
            get_db_session(engine) as session,
        ):
            run_id = create_and_enqueue_run(
                session,
                params={"topics": ["AI"], "timeframe_days": 7},
                triggered_by="api",
            )

        assert run_id is not None
        mock_task.delay.assert_called_once_with(run_id)

        # Verify DB row
        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            assert run.status == "pending"
            assert run.triggered_by == "api"
            assert run.input_params == {"topics": ["AI"], "timeframe_days": 7}

    def test_created_run_emits_system_logs(self, engine: Any) -> None:
        """Creating a run records system log entries before workers start."""
        from sqlalchemy import select

        from ainews.services.pipeline import create_and_enqueue_run

        with (
            patch("ainews.services.pipeline.run_pipeline"),
            get_db_session(engine) as session,
        ):
            run_id = create_and_enqueue_run(
                session,
                params={"topics": ["AI"]},
                triggered_by="api",
            )

        with get_db_session(engine) as session:
            logs = (
                session.execute(
                    select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.id)
                )
                .scalars()
                .all()
            )
            log_rows = [(log.message, log.node, log.level) for log in logs]

        assert [row[0] for row in log_rows] == [
            "Run created",
            "Pipeline task enqueued",
        ]
        assert {row[1] for row in log_rows} == {"pipeline"}
        assert {row[2] for row in log_rows} == {"INFO"}

    def test_enqueues_task_after_transaction_commits(self, engine: Any) -> None:
        """Task is enqueued only after the Run row is committed."""
        from ainews.services.pipeline import create_and_enqueue_run

        with (
            patch("ainews.services.pipeline.run_pipeline") as mock_task,
            get_db_session(engine) as session,
        ):
            run_id = create_and_enqueue_run(
                session,
                params={"topics": ["AI"]},
                triggered_by="api",
            )
            mock_task.delay.assert_not_called()

        mock_task.delay.assert_called_once_with(run_id)

    def test_enqueue_failure_marks_run_failed(self, engine: Any) -> None:
        """Broker enqueue failures are recorded after the run commits."""
        from sqlalchemy import select

        from ainews.services.pipeline import create_and_enqueue_run

        with patch("ainews.services.pipeline.run_pipeline") as mock_task:
            mock_task.delay.side_effect = RuntimeError("broker down")
            with get_db_session(engine) as session:
                run_id = create_and_enqueue_run(
                    session,
                    params={"topics": ["AI"]},
                    triggered_by="api",
                )

        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            run_status = run.status
            run_error = run.error
            logs = (
                session.execute(
                    select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.id)
                )
                .scalars()
                .all()
            )
            messages = [log.message for log in logs]

        assert run_status == "failed"
        assert run_error == "Failed to enqueue pipeline task: broker down"
        assert messages == [
            "Run created",
            "Pipeline task enqueue failed: broker down",
        ]

    def test_rolled_back_run_is_not_enqueued_on_later_commit(
        self,
        engine: Any,
    ) -> None:
        """Rollback removes pending enqueue callbacks for reusable sessions."""
        from ainews.services.pipeline import create_and_enqueue_run

        factory = make_session_factory(engine)
        session = factory()
        try:
            with patch("ainews.services.pipeline.run_pipeline") as mock_task:
                create_and_enqueue_run(
                    session,
                    params={"topics": ["AI"]},
                    triggered_by="api",
                )
                session.rollback()

                session.add(Run(id="unrelated-run", status="pending"))
                session.commit()

            mock_task.delay.assert_not_called()
        finally:
            session.close()

    def test_schedule_run(self, engine: Any) -> None:
        """Create a run from a named schedule."""
        from ainews.services.pipeline import create_and_enqueue_run

        # Seed schedule
        with get_db_session(engine) as session:
            sched = Schedule(
                name="weekly-ai",
                cron_expr="0 7 * * 1",
                timeframe_days=7,
                topics=["AI", "ML"],
            )
            session.add(sched)

        with (
            patch("ainews.services.pipeline.run_pipeline") as mock_task,
            get_db_session(engine) as session,
        ):
            run_id = create_and_enqueue_run(
                session,
                schedule_name="weekly-ai",
                triggered_by="cron",
            )

        mock_task.delay.assert_called_once_with(run_id)

        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            assert run.schedule_id is not None
            assert run.triggered_by == "cron"
            assert run.input_params is not None
            assert run.input_params["topics"] == ["AI", "ML"]

    def test_schedule_not_found(self, engine: Any) -> None:
        """Raise ValueError when schedule doesn't exist."""
        from ainews.services.pipeline import create_and_enqueue_run

        with (
            patch("ainews.services.pipeline.run_pipeline"),
            get_db_session(engine) as session,
            pytest.raises(ValueError, match="not found"),
        ):
            create_and_enqueue_run(
                session,
                schedule_name="nonexistent",
                triggered_by="api",
            )

    def test_cli_triggered_by(self, engine: Any) -> None:
        """CLI runs set triggered_by='cli'."""
        from ainews.services.pipeline import create_and_enqueue_run

        with (
            patch("ainews.services.pipeline.run_pipeline"),
            get_db_session(engine) as session,
        ):
            run_id = create_and_enqueue_run(
                session,
                params={"topics": ["AI"]},
                triggered_by="cli",
            )

        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            assert run.triggered_by == "cli"
