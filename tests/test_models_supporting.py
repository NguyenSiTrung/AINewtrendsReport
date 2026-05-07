"""Tests for Report, RunLog, User, and SettingsKV ORM models."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ainews.core.database import create_engine
from ainews.models.base import Base
from ainews.models.report import Report
from ainews.models.run import Run
from ainews.models.run_log import RunLog
from ainews.models.settings_kv import SettingsKV
from ainews.models.user import User

_TEST_RUN_ID = "test-run-00000001"


@pytest.fixture()
def engine():  # type: ignore[misc]
    """In-memory SQLite engine with all required tables created."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:  # type: ignore[misc]
    """Session with a seeded run row for FK-dependent inserts."""
    with Session(engine) as s:
        s.add(Run(id=_TEST_RUN_ID, status="pending"))
        s.commit()
        yield s


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_report_minimal_insert(session: Session) -> None:
    """Report can be created with only the required run_id."""
    report = Report(run_id=_TEST_RUN_ID)
    session.add(report)
    session.commit()
    session.refresh(report)

    assert report.id is not None
    assert report.run_id == _TEST_RUN_ID


def test_report_optional_fields_default_to_none(session: Session) -> None:
    """All optional Report fields default to None."""
    report = Report(run_id=_TEST_RUN_ID)
    session.add(report)
    session.commit()
    session.refresh(report)

    assert report.title is None
    assert report.summary_md is None
    assert report.html_path is None
    assert report.pdf_path is None
    assert report.trends is None
    assert report.token_usage is None
    assert report.created_at is None


def test_report_json_fields_roundtrip(session: Session) -> None:
    """Report stores and retrieves JSON trends and token_usage correctly."""
    trends = [{"name": "LLM agents", "score": 0.95}]
    token_usage = {"prompt": 100, "completion": 200, "total": 300}

    report = Report(
        run_id=_TEST_RUN_ID,
        trends=trends,
        token_usage=token_usage,
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    assert report.trends == trends
    assert report.token_usage == token_usage


def test_report_all_fields(session: Session) -> None:
    """Report stores all text fields without data loss."""
    report = Report(
        run_id=_TEST_RUN_ID,
        title="AI Weekly #1",
        summary_md="# Trends\nLLMs are everywhere.",
        html_path="/var/reports/2026-05-07.html",
        pdf_path="/var/reports/2026-05-07.pdf",
        trends=[],
        token_usage={"prompt": 50, "completion": 150, "total": 200},
        created_at="2026-05-07T00:00:00",
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    assert report.title == "AI Weekly #1"
    assert report.html_path == "/var/reports/2026-05-07.html"
    assert report.pdf_path == "/var/reports/2026-05-07.pdf"
    assert report.created_at == "2026-05-07T00:00:00"


# ---------------------------------------------------------------------------
# RunLog
# ---------------------------------------------------------------------------


def test_run_log_minimal_insert(session: Session) -> None:
    """RunLog can be created with required fields only."""
    log = RunLog(run_id=_TEST_RUN_ID, node="fetcher", message="Starting fetch")
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.id is not None
    assert log.node == "fetcher"
    assert log.message == "Starting fetch"


def test_run_log_default_level_is_info(session: Session) -> None:
    """RunLog.level defaults to 'info' when omitted."""
    log = RunLog(run_id=_TEST_RUN_ID, node="ranker", message="Ranking articles")
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.level == "info"


def test_run_log_custom_levels(session: Session) -> None:
    """RunLog accepts all expected log-level values."""
    for lvl in ("debug", "info", "warning", "error"):
        log = RunLog(
            run_id=_TEST_RUN_ID,
            node="writer",
            message=f"level={lvl}",
            level=lvl,
        )
        session.add(log)
    session.commit()


def test_run_log_payload_json_roundtrip(session: Session) -> None:
    """RunLog payload JSON stores and retrieves correctly."""
    payload = {"count": 42, "source": "hackernews"}
    log = RunLog(
        run_id=_TEST_RUN_ID,
        node="fetcher",
        message="Fetched articles",
        payload=payload,
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.payload == payload


def test_run_log_optional_fields_default_to_none(session: Session) -> None:
    """RunLog optional fields (payload, ts) default to None."""
    log = RunLog(run_id=_TEST_RUN_ID, node="exporter", message="Exporting")
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.payload is None
    assert log.ts is None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


def test_user_minimal_insert(session: Session) -> None:
    """User can be created with email and hashed_pw."""
    user = User(email="admin@example.com", hashed_pw="hashed_secret")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.email == "admin@example.com"


def test_user_default_role_is_admin(session: Session) -> None:
    """User.role defaults to 'admin' when omitted."""
    user = User(email="newuser@example.com", hashed_pw="pw")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.role == "admin"


def test_user_unique_email_constraint(session: Session) -> None:
    """Inserting two Users with the same email raises IntegrityError."""
    session.add(User(email="dup@example.com", hashed_pw="pw1"))
    session.commit()

    session.add(User(email="dup@example.com", hashed_pw="pw2"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_user_multiple_distinct_emails(session: Session) -> None:
    """Multiple users with distinct emails can coexist."""
    session.add(User(email="alice@example.com", hashed_pw="pa"))
    session.add(User(email="bob@example.com", hashed_pw="pb"))
    session.commit()

    count = session.query(User).count()
    assert count == 2


# ---------------------------------------------------------------------------
# SettingsKV
# ---------------------------------------------------------------------------


def test_settings_kv_minimal_insert(session: Session) -> None:
    """SettingsKV can be created with key and value."""
    setting = SettingsKV(key="smtp.host", value="smtp.example.com")
    session.add(setting)
    session.commit()
    session.refresh(setting)

    assert setting.key == "smtp.host"
    assert setting.value == "smtp.example.com"


def test_settings_kv_json_value_types(session: Session) -> None:
    """SettingsKV stores integers, booleans, and lists as JSON."""
    session.add(SettingsKV(key="smtp.port", value=587))
    session.add(SettingsKV(key="smtp.tls", value=True))
    session.add(SettingsKV(key="allowed_domains", value=["example.com", "test.com"]))
    session.commit()

    port = session.get(SettingsKV, "smtp.port")
    assert port is not None
    assert port.value == 587

    tls = session.get(SettingsKV, "smtp.tls")
    assert tls is not None
    assert tls.value is True

    domains = session.get(SettingsKV, "allowed_domains")
    assert domains is not None
    assert domains.value == ["example.com", "test.com"]


def test_settings_kv_primary_key_lookup(session: Session) -> None:
    """SettingsKV can be retrieved by its string primary key."""
    session.add(SettingsKV(key="feature.dark_mode", value={"enabled": False}))
    session.commit()

    retrieved = session.get(SettingsKV, "feature.dark_mode")
    assert retrieved is not None
    assert retrieved.value == {"enabled": False}


def test_settings_kv_value_update(session: Session) -> None:
    """SettingsKV value can be updated in-place."""
    session.add(SettingsKV(key="feature.flag", value=False))
    session.commit()

    setting = session.get(SettingsKV, "feature.flag")
    assert setting is not None
    setting.value = True
    session.commit()

    updated = session.get(SettingsKV, "feature.flag")
    assert updated is not None
    assert updated.value is True
