"""Unit tests for the run_logger service — log_to_db() helper."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from ainews.core.database import create_engine
from ainews.models import Base
from ainews.models.run import Run
from ainews.models.run_log import RunLog
from ainews.services.run_logger import log_to_db


@pytest.fixture()
def engine() -> Any:
    """In-memory SQLite engine with all tables."""
    eng = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def run_id(engine: Any) -> str:
    """Create a run and return its id."""
    from ainews.core.database import get_db_session

    with get_db_session(engine) as session:
        run = Run(id="test-run-001", status="running", triggered_by="test")
        session.add(run)
        session.commit()
    return "test-run-001"


class TestLogToDb:
    """Tests for log_to_db() helper function."""

    def test_creates_run_log_row(self, engine: Any, run_id: str) -> None:
        """log_to_db creates a RunLog row with correct fields."""
        log_to_db(engine, run_id, "planner", "INFO", "Node started")

        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            logs = (
                session.execute(select(RunLog).where(RunLog.run_id == run_id))
                .scalars()
                .all()
            )
            assert len(logs) == 1
            log = logs[0]
            assert log.run_id == run_id
            assert log.node == "planner"
            assert log.level == "INFO"
            assert log.message == "Node started"
            assert log.ts is not None  # auto-set timestamp

    def test_creates_log_with_payload(self, engine: Any, run_id: str) -> None:
        """log_to_db stores optional JSON payload."""
        payload = {"articles_found": 42, "queries_used": 5}
        log_to_db(
            engine,
            run_id,
            "retriever",
            "INFO",
            "Node completed",
            payload=payload,
        )

        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            log = session.execute(
                select(RunLog).where(RunLog.run_id == run_id)
            ).scalar_one()
            assert log.payload == payload

    def test_auto_sets_timestamp(self, engine: Any, run_id: str) -> None:
        """log_to_db auto-sets ts to current UTC ISO timestamp."""
        log_to_db(engine, run_id, "filter", "INFO", "Node started")

        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            log = session.execute(
                select(RunLog).where(RunLog.run_id == run_id)
            ).scalar_one()
            # Should be an ISO-format timestamp string
            assert "T" in log.ts
            assert len(log.ts) >= 19  # At least YYYY-MM-DDTHH:MM:SS

    def test_handles_missing_run_id_gracefully(self, engine: Any) -> None:
        """log_to_db suppresses FK constraint errors for missing run_id."""
        # Should not raise — silently suppresses DB errors
        log_to_db(engine, "nonexistent-run", "planner", "INFO", "Node started")

    def test_suppresses_db_exceptions(self, engine: Any) -> None:
        """log_to_db suppresses DB exceptions without raising."""
        # Call with intentionally bad engine should not crash
        from unittest.mock import MagicMock, patch

        bad_engine = MagicMock()
        bad_session = MagicMock()
        bad_session.add.side_effect = Exception("DB connection lost")
        bad_factory = MagicMock(return_value=bad_session)

        target = "ainews.services.run_logger.make_session_factory"
        with patch(target, return_value=bad_factory):
            # Should not raise
            log_to_db(bad_engine, "some-run", "planner", "ERROR", "Node failed")

    def test_multiple_logs_for_same_run(self, engine: Any, run_id: str) -> None:
        """log_to_db can create multiple logs for the same run."""
        log_to_db(engine, run_id, "planner", "INFO", "Node started")
        log_to_db(
            engine,
            run_id,
            "planner",
            "INFO",
            "Node completed",
            payload={"queries": 3},
        )
        log_to_db(engine, run_id, "retriever", "INFO", "Node started")

        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            logs = (
                session.execute(
                    select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.id)
                )
                .scalars()
                .all()
            )
            assert len(logs) == 3
            assert logs[0].message == "Node started"
            assert logs[1].message == "Node completed"
            assert logs[2].node == "retriever"

    def test_error_level_log(self, engine: Any, run_id: str) -> None:
        """log_to_db correctly stores ERROR level logs."""
        log_to_db(engine, run_id, "scraper", "ERROR", "Node failed: TimeoutError")

        from ainews.core.database import get_db_session

        with get_db_session(engine) as session:
            log = session.execute(
                select(RunLog).where(RunLog.run_id == run_id)
            ).scalar_one()
            assert log.level == "ERROR"
            assert "TimeoutError" in log.message
