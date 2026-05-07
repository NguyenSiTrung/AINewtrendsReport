# Spec: Phase 1 — Data Layer

## Overview

Establish the complete persistence layer for the AI News & Trends Report system.
This includes SQLAlchemy ORM models for all 7 application tables defined in PLAN.md §2.3,
SQLite-specific pragmas via a connection event listener, Alembic schema migrations,
FTS5 full-text search on reports, and an idempotent CLI seed command for starter data.

## Functional Requirements

### FR-1: SQLAlchemy ORM Models
- Define models for all tables from PLAN.md §2.3:
  - `Site` — target news sites with URL, category, priority, crawl config
  - `Schedule` — cron-driven run schedules with topic/site filters
  - `Run` — pipeline execution records with status tracking
  - `Article` — fetched/scraped articles with dedup hashes
  - `Report` — generated report metadata with file paths
  - `RunLog` — per-node structured log entries
  - `User` — single-admin auth (email + hashed password)
  - `SettingsKV` — key-value runtime configuration store
- All models use proper column types, constraints, indexes, and FK relationships
- JSON columns (selectors, topics, site_filter, input_params, stats, payload, trends, token_usage)
  use SQLAlchemy's `JSON` type backed by SQLite JSON1
- Timestamps stored as ISO 8601 TEXT (SQLite has no native datetime)
- Boolean fields stored as INTEGER (0/1) per SQLite convention

### FR-2: SQLite Connection Configuration
- Connection event listener applies pragmas on every new connection:
  - `journal_mode=WAL`
  - `synchronous=NORMAL`
  - `foreign_keys=ON`
  - `busy_timeout=5000`
  - `temp_store=MEMORY`
  - `mmap_size=268435456`
- Pragmas are hardcoded (architectural invariants, not configurable)
- Database engine factory uses the `AINEWS_DATABASE_URL` from Settings

### FR-3: Alembic Baseline Migration
- Single initial migration creating all 7 tables + indexes
- FTS5 virtual table `reports_fts` on (title, summary_md) with content=reports
- INSERT/UPDATE/DELETE triggers to keep FTS5 in sync with `reports` table
- `alembic upgrade head` creates a ready-to-use database from scratch
- `alembic downgrade base` cleanly drops everything (including FTS5)

### FR-4: Database Session Management
- Async-compatible session factory (or sync with proper scoping)
- Context manager / dependency for FastAPI injection (future Phase 5)
- Proper connection pooling configuration for SQLite (pool_size=1 for writer safety)

### FR-5: Seed Data Command
- Extend existing `ainews seed` CLI stub with actual implementation
- Seed 10 starter sites:
  1. TechCrunch AI
  2. The Verge
  3. MIT Technology Review
  4. Hugging Face Blog
  5. OpenAI Blog
  6. Anthropic News
  7. Google AI Blog
  8. ArXiv-sanity
  9. Stratechery
  10. Ben's Bites
- Seed 1 weekly schedule: `weekly-ai-news` (cron: `0 7 * * 1`, timeframe: 7 days)
- Idempotent: upsert by URL (sites) and name (schedules) — safe to re-run
- Reports count of created/skipped records

## Non-Functional Requirements

- **Test coverage:** ≥ 80% on all new modules (models, database, migrations, seed)
- **Type safety:** All models and DB functions pass mypy strict mode
- **Lint clean:** ruff check + ruff format pass
- **No new runtime dependencies** — SQLAlchemy and Alembic are already in pyproject.toml from Phase 0

## Acceptance Criteria

1. `alembic upgrade head` creates all tables, indexes, FTS5, and triggers in a fresh SQLite file
2. `alembic downgrade base` cleanly drops everything
3. `ainews seed` populates 10 sites + 1 schedule (idempotent on re-run)
4. All SQLite pragmas verified active via a test that inspects `PRAGMA` results
5. FTS5 search returns results after inserting a test report
6. `make lint && make typecheck && make test` all green
7. ≥ 80% test coverage on new modules

## Out of Scope

- FastAPI route integration (Phase 5)
- User seeding / auth setup (Phase 6)
- LangGraph checkpoint table (managed by `langgraph-checkpoint-sqlite`, Phase 3)
- Embedding columns or vector tables (v2)
- PostgreSQL compatibility (documented upgrade path only)
