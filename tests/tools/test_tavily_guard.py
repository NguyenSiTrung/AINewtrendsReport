"""Tests for Tavily monthly-quota guard."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session

from ainews.models.base import Base
from ainews.models.settings_kv import SettingsKV
from ainews.tools.tavily_guard import (
    _month_key,
    check_and_increment,
    get_current_count,
    get_monthly_cap,
    increment_count,
    is_quota_available,
)


@pytest.fixture
def session() -> Session:
    """Create an in-memory DB session with SettingsKV table."""
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class TestMonthKey:
    def test_format(self) -> None:
        key = _month_key()
        assert key.startswith("tavily_calls_")
        assert len(key) == len("tavily_calls_YYYY_MM")


class TestGetMonthlyCap:
    def test_returns_default_when_not_set(self, session: Session) -> None:
        assert get_monthly_cap(session) == 1000

    def test_returns_custom_cap(self, session: Session) -> None:
        session.add(SettingsKV(key="tavily_monthly_cap", value=500))
        session.flush()
        assert get_monthly_cap(session) == 500


class TestGetCurrentCount:
    def test_returns_zero_when_no_entry(self, session: Session) -> None:
        assert get_current_count(session) == 0

    def test_returns_stored_count(self, session: Session) -> None:
        key = _month_key()
        session.add(SettingsKV(key=key, value=42))
        session.flush()
        assert get_current_count(session) == 42


class TestIncrementCount:
    def test_creates_entry_on_first_call(self, session: Session) -> None:
        result = increment_count(session)
        assert result == 1

    def test_increments_existing(self, session: Session) -> None:
        key = _month_key()
        session.add(SettingsKV(key=key, value=10))
        session.flush()
        result = increment_count(session)
        assert result == 11


class TestIsQuotaAvailable:
    def test_available_when_under_cap(self, session: Session) -> None:
        assert is_quota_available(session) is True

    def test_not_available_when_at_cap(self, session: Session) -> None:
        key = _month_key()
        session.add(SettingsKV(key=key, value=1000))
        session.flush()
        assert is_quota_available(session) is False

    def test_not_available_when_over_cap(self, session: Session) -> None:
        key = _month_key()
        session.add(SettingsKV(key=key, value=1500))
        session.flush()
        assert is_quota_available(session) is False


class TestCheckAndIncrement:
    def test_allows_and_increments(self, session: Session) -> None:
        assert check_and_increment(session) is True
        assert get_current_count(session) == 1

    def test_rejects_when_at_cap(self, session: Session) -> None:
        key = _month_key()
        session.add(SettingsKV(key=key, value=1000))
        session.flush()
        assert check_and_increment(session) is False
        # Count should NOT increment when rejected
        assert get_current_count(session) == 1000

    def test_monthly_auto_reset(self, session: Session) -> None:
        """Verify that a new month gets a fresh counter."""
        # Set count for a previous month
        session.add(SettingsKV(key="tavily_calls_2025_01", value=999))
        session.flush()
        # Current month should be fresh
        assert is_quota_available(session) is True
