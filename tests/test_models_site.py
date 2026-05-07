"""Tests for the Site ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ainews.core.database import create_engine, make_session_factory
from ainews.models.base import Base
from ainews.models.site import Site


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


class TestSiteDefaults:
    def test_instantiation_with_required_fields(self, session: Session) -> None:
        """Site can be created with only the required url field."""
        site = Site(url="https://example.com")
        session.add(site)
        session.commit()
        assert site.id is not None
        assert site.url == "https://example.com"

    def test_priority_default(self, session: Session) -> None:
        """Site priority defaults to 5."""
        site = Site(url="https://example.com")
        session.add(site)
        session.commit()
        assert site.priority == 5

    def test_crawl_depth_default(self, session: Session) -> None:
        """Site crawl_depth defaults to 2."""
        site = Site(url="https://example.com")
        session.add(site)
        session.commit()
        assert site.crawl_depth == 2

    def test_js_render_default(self, session: Session) -> None:
        """Site js_render defaults to 0."""
        site = Site(url="https://example.com")
        session.add(site)
        session.commit()
        assert site.js_render == 0

    def test_enabled_default(self, session: Session) -> None:
        """Site enabled defaults to 1."""
        site = Site(url="https://example.com")
        session.add(site)
        session.commit()
        assert site.enabled == 1

    def test_nullable_fields_default_to_none(self, session: Session) -> None:
        """Nullable Site fields default to None when not provided."""
        site = Site(url="https://example.com")
        session.add(site)
        session.commit()
        assert site.category is None
        assert site.selectors is None
        assert site.created_at is None


class TestSiteConstraints:
    def test_url_unique_constraint(self, session: Session) -> None:
        """Inserting two Sites with the same url raises IntegrityError."""
        site1 = Site(url="https://example.com")
        site2 = Site(url="https://example.com")
        session.add(site1)
        session.commit()
        session.add(site2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_url_not_null_constraint(self, session: Session) -> None:
        """Inserting a Site without url raises IntegrityError."""
        site = Site()  # type: ignore[call-arg]
        session.add(site)
        with pytest.raises(IntegrityError):
            session.commit()


class TestSiteTableStructure:
    def test_table_name(self) -> None:
        """Site maps to the 'sites' table."""
        assert Site.__tablename__ == "sites"

    def test_enabled_index_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        """An index on the 'enabled' column is present in 'sites'."""
        inspector = sa_inspect(engine)
        indexes = inspector.get_indexes("sites")
        indexed_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "enabled" in indexed_columns

    def test_category_index_exists(self, engine) -> None:  # type: ignore[no-untyped-def]
        """An index on the 'category' column is present in 'sites'."""
        inspector = sa_inspect(engine)
        indexes = inspector.get_indexes("sites")
        indexed_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "category" in indexed_columns


class TestSiteFields:
    def test_all_fields_stored_and_retrieved(self, session: Session) -> None:
        """All Site fields round-trip correctly through the DB."""
        site = Site(
            url="https://example.com",
            category="tech",
            priority=3,
            crawl_depth=1,
            selectors={"article": ".post", "title": "h1"},
            js_render=1,
            enabled=0,
            created_at="2026-01-01T00:00:00",
        )
        session.add(site)
        session.commit()
        session.refresh(site)

        assert site.url == "https://example.com"
        assert site.category == "tech"
        assert site.priority == 3
        assert site.crawl_depth == 1
        assert site.selectors == {"article": ".post", "title": "h1"}
        assert site.js_render == 1
        assert site.enabled == 0
        assert site.created_at == "2026-01-01T00:00:00"

    def test_selectors_json_stored_as_dict(self, session: Session) -> None:
        """selectors JSON column stores and retrieves a dict."""
        site = Site(url="https://example.com", selectors={"link": "a.article"})
        session.add(site)
        session.commit()
        session.refresh(site)
        assert isinstance(site.selectors, dict)
        assert site.selectors["link"] == "a.article"
