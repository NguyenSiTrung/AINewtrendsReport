"""CLI integration tests for the `ainews seed` command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ainews.cli import app
from ainews.core.database import create_engine, get_db_session
from ainews.models.base import Base
from ainews.models.schedule import Schedule
from ainews.models.site import Site

runner = CliRunner()


def _setup_db(db_path: Path) -> None:
    """Create schema in a fresh SQLite file (bypasses Alembic for speed)."""
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()


def test_seed_creates_sites_and_schedules(tmp_path: Path) -> None:
    """ainews seed populates 10 sites and 1 schedule on first run."""
    db_path = tmp_path / "test.db"
    _setup_db(db_path)

    result = runner.invoke(app, ["seed"], env={"AINEWS_DB_PATH": str(db_path)})

    assert result.exit_code == 0, result.output
    assert "Sites: 10 created, 0 skipped" in result.output
    assert "Schedules: 1 created, 0 skipped" in result.output

    engine = create_engine(f"sqlite:///{db_path}")
    with get_db_session(engine) as session:
        assert session.query(Site).count() == 10
        assert session.query(Schedule).count() == 1
    engine.dispose()


def test_seed_idempotent_second_run_skips_all(tmp_path: Path) -> None:
    """Running ainews seed twice skips everything on the second invocation."""
    db_path = tmp_path / "test.db"
    _setup_db(db_path)

    env = {"AINEWS_DB_PATH": str(db_path)}
    runner.invoke(app, ["seed"], env=env)
    result = runner.invoke(app, ["seed"], env=env)

    assert result.exit_code == 0, result.output
    assert "Sites: 0 created, 10 skipped" in result.output
    assert "Schedules: 0 created, 1 skipped" in result.output

    engine = create_engine(f"sqlite:///{db_path}")
    with get_db_session(engine) as session:
        assert session.query(Site).count() == 10  # unchanged
        assert session.query(Schedule).count() == 1  # unchanged
    engine.dispose()
