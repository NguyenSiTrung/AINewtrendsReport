"""Tests for the Schedule ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ainews.core.database import create_engine, make_session_factory
from ainews.models.base import Base
from ainews.models.schedule import Schedule


@pytest.fixture()  # type: ignore[misc]
def engine():  # type: ignore[no-untyped-def]
    """In-memory SQLite engine with all registered tables created."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()  # type: ignore[misc]
def session(engine):  # type: ignore[no-untyped-def]
    """Session bound to the in-memory engine."""
    factory = make_session_factory(engine)
    sess = factory()
    yield sess
    sess.close()


class TestScheduleDefaults:
    def test_instantiation_with_required_fields(self, session: Session) -> None:
        """Schedule can be created with name and cron_expr only."""
        schedule = Schedule(name="weekly", cron_expr="0 7 * * 1")
        session.add(schedule)
        session.commit()
        assert schedule.id is not None
        assert schedule.name == "weekly"
        assert schedule.cron_expr == "0 7 * * 1"

    def test_timeframe_days_default(self, session: Session) -> None:
        """Schedule timeframe_days defaults to 7."""
        schedule = Schedule(name="weekly", cron_expr="0 7 * * 1")
        session.add(schedule)
        session.commit()
        assert schedule.timeframe_days == 7

    def test_enabled_default(self, session: Session) -> None:
        """Schedule enabled defaults to 1."""
        schedule = Schedule(name="weekly", cron_expr="0 7 * * 1")
        session.add(schedule)
        session.commit()
        assert schedule.enabled == 1

    def test_nullable_fields_default_to_none(self, session: Session) -> None:
        """Nullable Schedule fields default to None when not provided."""
        schedule = Schedule(name="weekly", cron_expr="0 7 * * 1")
        session.add(schedule)
        session.commit()
        assert schedule.site_filter is None
        assert schedule.topics is None
        assert schedule.model_override is None
        assert schedule.created_at is None


class TestScheduleConstraints:
    def test_name_unique_constraint(self, session: Session) -> None:
        """Inserting two Schedules with the same name raises IntegrityError."""
        s1 = Schedule(name="weekly", cron_expr="0 7 * * 1")
        s2 = Schedule(name="weekly", cron_expr="0 8 * * 2")
        session.add(s1)
        session.commit()
        session.add(s2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_name_not_null_constraint(self, session: Session) -> None:
        """Inserting a Schedule without name raises IntegrityError."""
        schedule = Schedule(cron_expr="0 7 * * 1")  # type: ignore[call-arg]
        session.add(schedule)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_cron_expr_not_null_constraint(self, session: Session) -> None:
        """Inserting a Schedule without cron_expr raises IntegrityError."""
        schedule = Schedule(name="weekly")  # type: ignore[call-arg]
        session.add(schedule)
        with pytest.raises(IntegrityError):
            session.commit()


class TestScheduleTableStructure:
    def test_table_name(self) -> None:
        """Schedule maps to the 'schedules' table."""
        assert Schedule.__tablename__ == "schedules"

    def test_enabled_index_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        """An index on the 'enabled' column is present in 'schedules'."""
        inspector = sa_inspect(engine)
        indexes = inspector.get_indexes("schedules")
        indexed_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "enabled" in indexed_columns


class TestScheduleFields:
    def test_all_fields_stored_and_retrieved(self, session: Session) -> None:
        """All Schedule fields round-trip correctly through the DB."""
        schedule = Schedule(
            name="weekly",
            cron_expr="0 7 * * 1",
            timeframe_days=14,
            site_filter=["tech", "ai"],
            topics=["machine learning", "LLM"],
            model_override="gpt-4",
            enabled=0,
            created_at="2026-01-01T00:00:00",
        )
        session.add(schedule)
        session.commit()
        session.refresh(schedule)

        assert schedule.name == "weekly"
        assert schedule.cron_expr == "0 7 * * 1"
        assert schedule.timeframe_days == 14
        assert schedule.site_filter == ["tech", "ai"]
        assert schedule.topics == ["machine learning", "LLM"]
        assert schedule.model_override == "gpt-4"
        assert schedule.enabled == 0
        assert schedule.created_at == "2026-01-01T00:00:00"

    def test_site_filter_json_stored_as_list(self, session: Session) -> None:
        """site_filter JSON column stores and retrieves a list."""
        schedule = Schedule(
            name="weekly",
            cron_expr="0 7 * * 1",
            site_filter=["tech", "ai"],
        )
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        assert isinstance(schedule.site_filter, list)
        assert schedule.site_filter == ["tech", "ai"]

    def test_topics_json_stored_as_list(self, session: Session) -> None:
        """topics JSON column stores and retrieves a list."""
        schedule = Schedule(
            name="weekly",
            cron_expr="0 7 * * 1",
            topics=["llm", "agents"],
        )
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        assert isinstance(schedule.topics, list)
        assert schedule.topics == ["llm", "agents"]
