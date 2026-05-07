"""Integration tests for Alembic migrations, FTS5 virtual table, and sync triggers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

_ALEMBIC_INI = str(Path(__file__).parent.parent / "alembic.ini")
_EXPECTED_APP_TABLES = frozenset(
    {
        "articles",
        "reports",
        "run_logs",
        "runs",
        "schedules",
        "settings_kv",
        "sites",
        "users",
    }
)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_migrations.db"


@pytest.fixture()
def alembic_cfg(db_path: Path) -> Config:
    cfg = Config(_ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")
    return cfg


@pytest.fixture()
def upgraded_db(alembic_cfg: Config, db_path: Path) -> sqlite3.Connection:
    """Yield a raw sqlite3 connection to a freshly upgraded database."""
    command.upgrade(alembic_cfg, "head")
    conn = sqlite3.connect(str(db_path))
    yield conn
    conn.close()


# ── Upgrade / downgrade cycle ─────────────────────────────────────────────────


def test_upgrade_creates_all_app_tables(upgraded_db: sqlite3.Connection) -> None:
    """upgrade head creates all 8 application tables."""
    tables = {
        row[0]
        for row in upgraded_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert _EXPECTED_APP_TABLES.issubset(tables)


def test_upgrade_creates_fts5_table(upgraded_db: sqlite3.Connection) -> None:
    """upgrade head creates the reports_fts virtual table."""
    tables = {
        row[0]
        for row in upgraded_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "reports_fts" in tables


def test_upgrade_creates_sync_triggers(upgraded_db: sqlite3.Connection) -> None:
    """upgrade head creates the 3 FTS5 sync triggers."""
    triggers = {
        row[0]
        for row in upgraded_db.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
    }
    assert {"reports_ai", "reports_au", "reports_ad"}.issubset(triggers)


def test_downgrade_drops_all_app_tables(alembic_cfg: Config, db_path: Path) -> None:
    """downgrade base cleanly drops all app tables, FTS5, and triggers."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

    conn = sqlite3.connect(str(db_path))
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    triggers = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    conn.close()

    assert _EXPECTED_APP_TABLES.isdisjoint(tables), f"Leftover tables: {tables}"
    assert "reports_fts" not in tables
    assert triggers == set(), f"Leftover triggers: {triggers}"


# ── FTS5 search ───────────────────────────────────────────────────────────────


def test_fts5_insert_trigger_makes_report_searchable(
    upgraded_db: sqlite3.Connection,
) -> None:
    """Inserting a report fires the INSERT trigger and makes it FTS-searchable."""
    upgraded_db.execute("INSERT INTO runs (id, status) VALUES ('run-fts-001', 'done')")
    upgraded_db.execute(
        "INSERT INTO reports (run_id, title, summary_md)"
        " VALUES ('run-fts-001', 'TransformerWeekly', 'Attention mechanisms overview')",
    )
    upgraded_db.commit()

    hits = upgraded_db.execute(
        "SELECT rowid FROM reports_fts WHERE reports_fts MATCH 'TransformerWeekly'"
    ).fetchall()
    assert len(hits) == 1


def test_fts5_update_trigger_replaces_index_entry(
    upgraded_db: sqlite3.Connection,
) -> None:
    """Updating a report fires the UPDATE trigger; old terms no longer match."""
    upgraded_db.execute("INSERT INTO runs (id, status) VALUES ('run-fts-002', 'done')")
    upgraded_db.execute(
        "INSERT INTO reports (run_id, title, summary_md)"
        " VALUES ('run-fts-002', 'ZephyrLLM', 'original zephyr content')",
    )
    upgraded_db.commit()

    upgraded_db.execute(
        "UPDATE reports SET title='MistralUpdate', summary_md='mistral content'"
        " WHERE run_id='run-fts-002'"
    )
    upgraded_db.commit()

    old_hits = upgraded_db.execute(
        "SELECT rowid FROM reports_fts WHERE reports_fts MATCH 'ZephyrLLM'"
    ).fetchall()
    new_hits = upgraded_db.execute(
        "SELECT rowid FROM reports_fts WHERE reports_fts MATCH 'MistralUpdate'"
    ).fetchall()

    assert len(old_hits) == 0, "Old term should be removed from FTS after update"
    assert len(new_hits) == 1, "New term should be in FTS after update"


def test_fts5_delete_trigger_removes_index_entry(
    upgraded_db: sqlite3.Connection,
) -> None:
    """Deleting a report fires the DELETE trigger; it is no longer FTS-searchable."""
    upgraded_db.execute("INSERT INTO runs (id, status) VALUES ('run-fts-003', 'done')")
    upgraded_db.execute(
        "INSERT INTO reports (run_id, title, summary_md)"
        " VALUES ('run-fts-003', 'EphemeralClaude', 'to be deleted soon')",
    )
    upgraded_db.commit()

    before = upgraded_db.execute(
        "SELECT rowid FROM reports_fts WHERE reports_fts MATCH 'EphemeralClaude'"
    ).fetchall()
    assert len(before) == 1

    upgraded_db.execute("DELETE FROM reports WHERE run_id='run-fts-003'")
    upgraded_db.commit()

    after = upgraded_db.execute(
        "SELECT rowid FROM reports_fts WHERE reports_fts MATCH 'EphemeralClaude'"
    ).fetchall()
    assert len(after) == 0, "Deleted report should be removed from FTS index"
