# Plan: Phase 1 — Data Layer

Track: `data-layer_20260507`

## Phase 1: Database Infrastructure

- [x] Task 1: Database engine factory with SQLite pragma event listener
  - [x] Write tests verifying all 6 pragmas are applied on new connections
  - [x] Create `src/ainews/core/database.py` with `create_engine()` factory
  - [x] Implement `@event.listens_for(engine, "connect")` handler for pragmas
  - [x] Use `AINEWS_DATABASE_URL` from existing Settings class
  - [x] Verify tests pass with in-memory SQLite

- [x] Task 2: Session management factory
  - [x] Write tests for session creation, context manager, and cleanup
  - [x] Create `sessionmaker` bound to the engine
  - [x] Create `get_db_session()` context manager for dependency injection
  - [x] Ensure proper connection pooling config (`StaticPool` for SQLite)

- [x] Task 3: Conductor - User Manual Verification 'Database Infrastructure' (Protocol in workflow.md)

## Phase 2: ORM Models
<!-- execution: parallel -->

- [x] Task 1: Site and Schedule models
  <!-- files: src/ainews/models/site.py, src/ainews/models/schedule.py, tests/test_models_site.py, tests/test_models_schedule.py -->
  - [x] Write tests for model instantiation, defaults, constraints, and relationships
  - [x] Define `Site` model (url UNIQUE, category, priority, crawl_depth, selectors JSON, js_render, enabled)
  - [x] Define `Schedule` model (name, cron_expr, timeframe_days, site_filter JSON, topics JSON, model_override, enabled)
  - [x] Add appropriate indexes

- [x] Task 2: Run and Article models
  <!-- files: src/ainews/models/run.py, src/ainews/models/article.py, tests/test_models_run.py, tests/test_models_article.py -->
  - [x] Write tests for model instantiation, FK relationships, unique constraints
  - [x] Define `Run` model (uuid PK, schedule_id FK nullable, status, timestamps, input_params JSON, stats JSON)
  - [x] Define `Article` model (run_id FK, url, source, title, content_md, relevance, hash, shingles JSON, status, UNIQUE(run_id, url))
  - [x] Add appropriate indexes

- [x] Task 3: Report, RunLog, User, and SettingsKV models
  <!-- files: src/ainews/models/report.py, src/ainews/models/run_log.py, src/ainews/models/user.py, src/ainews/models/settings_kv.py, tests/test_models_supporting.py -->
  - [x] Write tests for model instantiation, FK relationships, constraints
  - [x] Define `Report` model (run_id FK, title, summary_md, file paths, trends JSON, token_usage JSON)
  - [x] Define `RunLog` model (run_id FK, node, level, message, payload JSON, ts)
  - [x] Define `User` model (email unique, hashed_pw, role)
  - [x] Define `SettingsKV` model (key PK, value JSON, updated_at)

- [x] Task 4: Conductor - User Manual Verification 'ORM Models' (Protocol in workflow.md)

## Phase 3: Alembic Migration & FTS5

- [x] Task 1: Configure Alembic for the project
  - [x] Update `alembic/env.py` to import models and use engine factory
  - [x] Set `target_metadata` to the shared `Base.metadata`
  - [x] Ensure `alembic.ini` points to correct database URL

- [x] Task 2: Create baseline migration with all tables, indexes, FTS5, and triggers
  - [x] Auto-generate migration from ORM models (`alembic revision --autogenerate`)
  - [x] Manually add FTS5 virtual table: `CREATE VIRTUAL TABLE reports_fts USING fts5(title, summary_md, content=reports)`
  - [x] Add INSERT/UPDATE/DELETE triggers to sync `reports_fts` with `reports`
  - [x] Verify `alembic upgrade head` creates all tables from scratch
  - [x] Verify `alembic downgrade base` cleanly drops everything (including FTS5)

- [x] Task 3: Write migration integration tests
  - [x] Test full upgrade/downgrade cycle
  - [x] Test FTS5 insert + search returns results
  - [x] Test FTS5 trigger sync (insert/update/delete on reports reflects in FTS)

- [x] Task 4: Conductor - User Manual Verification 'Alembic Migration & FTS5' (Protocol in workflow.md)

## Phase 4: Seed Data Command

- [x] Task 1: Implement seed data and upsert logic
  - [x] Write tests for seed upsert (create new, skip existing, count reporting)
  - [x] Define 10 starter sites as structured data in seed module
  - [x] Define 1 weekly schedule (`weekly-ai-news`, cron `0 7 * * 1`, timeframe 7 days)
  - [x] Implement idempotent upsert logic (match by URL for sites, name for schedules)

- [x] Task 2: Wire `ainews seed` CLI command
  - [x] Write CLI integration test (invoke seed, verify DB contents)
  - [x] Replace existing stub with working implementation
  - [x] Output created/skipped counts to console
  - [x] Verify idempotency (run twice, second run skips all)

- [x] Task 3: Conductor - User Manual Verification 'Seed Data Command' (Protocol in workflow.md)

## Exit Criteria (from PLAN.md)

- [x] `alembic upgrade head` + `ainews seed` work end-to-end
- [x] `make lint && make typecheck && make test` all green
- [x] ≥ 80% test coverage on new modules
