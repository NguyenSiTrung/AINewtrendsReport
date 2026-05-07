"""Tests for the Article ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

import ainews.models.schedule  # noqa: F401 - registers Schedule with Base.metadata
from ainews.core.database import create_engine, make_session_factory
from ainews.models.article import Article
from ainews.models.base import Base
from ainews.models.run import Run


@pytest.fixture()
def engine():  # type: ignore[misc]
    """In-memory SQLite engine with all model tables created."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):  # type: ignore[misc]
    """Session bound to the in-memory engine."""
    factory = make_session_factory(engine)
    sess = factory()
    yield sess
    sess.close()


@pytest.fixture()
def run(session):  # type: ignore[misc]
    """A persisted Run instance for FK references."""
    r = Run()
    session.add(r)
    session.commit()
    return r


# ── Table creation ────────────────────────────────────────────────────────────


def test_article_table_created(engine) -> None:  # type: ignore[no-untyped-def]
    """articles table is created by Base.metadata.create_all."""
    inspector = inspect(engine)
    assert "articles" in inspector.get_table_names()


# ── Primary key ───────────────────────────────────────────────────────────────


def test_article_autoincrement_pk(session, run) -> None:  # type: ignore[no-untyped-def]
    """Article.id is an autoincrement integer PK."""
    a = Article(run_id=run.id, url="https://example.com/1")
    session.add(a)
    session.commit()
    assert isinstance(a.id, int)
    assert a.id >= 1


def test_article_pk_increments(session, run) -> None:  # type: ignore[no-untyped-def]
    """Subsequent articles get increasing PKs."""
    a1 = Article(run_id=run.id, url="https://example.com/1")
    a2 = Article(run_id=run.id, url="https://example.com/2")
    session.add_all([a1, a2])
    session.commit()
    assert a2.id > a1.id


# ── Status default ────────────────────────────────────────────────────────────


def test_article_default_status(session, run) -> None:  # type: ignore[no-untyped-def]
    """Article.status defaults to 'fetched'."""
    a = Article(run_id=run.id, url="https://example.com/1")
    session.add(a)
    session.commit()
    session.refresh(a)
    assert a.status == "fetched"


# ── Nullable fields ───────────────────────────────────────────────────────────


def test_article_optional_fields_default_none(session, run) -> None:  # type: ignore[no-untyped-def]
    """All optional Article fields default to None."""
    a = Article(run_id=run.id, url="https://example.com/1")
    session.add(a)
    session.commit()
    session.refresh(a)
    assert a.source is None
    assert a.title is None
    assert a.content_md is None
    assert a.relevance is None
    assert a.hash is None
    assert a.shingles is None
    assert a.created_at is None


# ── Full field round-trip ─────────────────────────────────────────────────────


def test_article_full_fields_round_trip(session, run) -> None:  # type: ignore[no-untyped-def]
    """Article accepts and returns all column values correctly."""
    a = Article(
        run_id=run.id,
        url="https://example.com/article",
        source="example.com",
        title="Test Article",
        content_md="## Heading\nContent here.",
        relevance=0.85,
        hash="abc123",
        shingles=[1, 2, 3, 4],
        status="kept",
        created_at="2026-05-07T10:00:00Z",
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    assert a.source == "example.com"
    assert a.title == "Test Article"
    assert a.content_md == "## Heading\nContent here."
    assert a.relevance == pytest.approx(0.85)
    assert a.hash == "abc123"
    assert a.shingles == [1, 2, 3, 4]
    assert a.status == "kept"
    assert a.created_at == "2026-05-07T10:00:00Z"


# ── FK relationship ───────────────────────────────────────────────────────────


def test_article_run_id_fk(session, run) -> None:  # type: ignore[no-untyped-def]
    """Article.run_id references a valid Run.id."""
    a = Article(run_id=run.id, url="https://example.com/1")
    session.add(a)
    session.commit()
    assert a.run_id == run.id


# ── UniqueConstraint ──────────────────────────────────────────────────────────


def test_article_unique_run_url_constraint(session, run) -> None:  # type: ignore[no-untyped-def]
    """UniqueConstraint on (run_id, url) rejects duplicate URL within same run."""
    url = "https://example.com/dup"
    a1 = Article(run_id=run.id, url=url)
    session.add(a1)
    session.commit()

    a2 = Article(run_id=run.id, url=url)
    session.add(a2)
    with pytest.raises(IntegrityError):
        session.commit()


def test_article_same_url_in_different_runs_allowed(session) -> None:  # type: ignore[no-untyped-def]
    """Same URL can appear in different runs (constraint is per run)."""
    r1 = Run()
    r2 = Run()
    session.add_all([r1, r2])
    session.commit()

    url = "https://example.com/shared"
    a1 = Article(run_id=r1.id, url=url)
    a2 = Article(run_id=r2.id, url=url)
    session.add_all([a1, a2])
    session.commit()
    assert a1.id != a2.id


# ── Indexes ───────────────────────────────────────────────────────────────────


def test_article_indexes_exist(engine) -> None:  # type: ignore[no-untyped-def]
    """Required indexes exist on the articles table."""
    inspector = inspect(engine)
    indexes = {ix["name"] for ix in inspector.get_indexes("articles")}
    assert "ix_articles_run_id" in indexes
    assert "ix_articles_hash" in indexes
    assert "ix_articles_status" in indexes
