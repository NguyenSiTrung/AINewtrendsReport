# Track Learnings: data-layer_20260507

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Build backend:** Use `hatchling.build` (not `hatchling.backends`) with `packages = ["src/ainews"]` for src/ layout
- **Ruff excludes:** Add `exclude = [".agents", ".beads", ".claude", "alembic"]` to `[tool.ruff]` to skip non-project directories
- **Gitignore negation:** When a parent dir is ignored (e.g. `var/`), use `!var/.gitkeep` negation pattern and `git add -f` to force-track the gitkeep
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings` `SettingsConfigDict(env_prefix="AINEWS_")`
- **Makefile commands:** All commands use `uv run` prefix (e.g., `uv run ruff check .`, `uv run pytest --cov`)

---

<!-- Learnings from implementation will be appended below -->

## [2026-05-07] - Phase 1 Task 1: Database engine factory with SQLite pragma listener
- **Implemented:** `create_engine()` factory in `src/ainews/core/database.py` with `@event.listen` pragma handler and `StaticPool` for in-memory URLs
- **Files changed:** `src/ainews/core/database.py`, `tests/test_database.py`, `pyproject.toml`, `.pre-commit-config.yaml`
- **Commit:** 0c1004f
- **Learnings:**
  - Patterns: SQLAlchemy 2.0 `event.listen(engine, "connect", handler)` applies pragmas on every new raw DBAPI connection
  - Gotchas: WAL mode (`journal_mode=WAL`) only works on file-based SQLite — in-memory databases silently ignore it. Use `tmp_path` fixture (not `":memory:"`) when testing WAL
  - Gotchas: pre-commit `mirrors-mypy` hook needs `additional_dependencies` updated with new packages (sqlalchemy, alembic) or mypy fails with `import-not-found`
  - Context: sqlalchemy/alembic were NOT pre-installed in pyproject.toml despite spec saying they were from Phase 0 — had to add them
## [2026-05-07] - Phase 3: Alembic Migration & FTS5
- **Implemented:** `alembic/env.py` with models metadata + pragma engine; baseline migration `dc09fc4f2f6d`; FTS5 virtual table + 3 sync triggers; 7 integration tests
- **Commits:** Alembic config, migration, tests
- **Learnings:**
  - Patterns: `alembic check` returns non-zero when pending migrations exist — expected before first `revision --autogenerate`; use it to verify metadata is loaded correctly
  - Patterns: `render_as_batch=True` is required in both offline and online `context.configure()` for SQLite — otherwise Alembic can't generate ALTER TABLE operations
  - Patterns: FTS5 `content=reports, content_rowid=id` requires manual triggers for sync; `'delete'` special command removes an FTS entry; INSERT + DELETE pattern handles UPDATE
  - Gotchas: `alembic.ini` `prepend_sys_path = .` only adds project root; src-layout projects need `prepend_sys_path = . src` OR `sys.path.insert` in env.py
  - Gotchas: FTS5 content tables with `content_rowid=id` require the `id` column to be INTEGER PK in SQLite (which maps `rowid = id`)
---

## [2026-05-07] - Phase 4: Seed Data Command
- **Implemented:** `src/ainews/seed.py` with `STARTER_SITES` (10), `STARTER_SCHEDULES` (1), `seed_all()` function, `SeedResult` dataclass; `ainews seed` CLI command; 14 tests total
- **Commits:** seed module, CLI command
- **Learnings:**
  - Patterns: Idempotent upsert via `select(...).filter_by(...).scalar_one_or_none()` — if exists skip, else insert + commit
  - Patterns: Typer sub-app with `invoke_without_command=True` + `@seed_app.callback(invoke_without_command=True)` makes `ainews seed` run directly without a subcommand
  - Gotchas: Typer's `invoke_without_command` must be set on BOTH the `Typer(...)` constructor AND the `@callback(invoke_without_command=True)` decorator for correct behavior
  - Patterns: `CliRunner` from `typer.testing` supports `env={"KEY": "value"}` to inject env vars; use with `AINEWS_DB_PATH` to redirect DB for tests
---

## [2026-05-07] - Phase 2: ORM Models (parallel execution — 3 workers)
- **Implemented:** 8 models across 8 files (Site, Schedule, Run, Article, Report, RunLog, User, SettingsKV) + shared Base
- **Commits:** ac8835c (Site/Schedule), 7345e7c (Run/Article), 1a46edb (supporting), + aggregation commit
- **Learnings:**
  - Patterns: All models use `DeclarativeBase` subclass from `ainews.models.base.Base`; import all models in `ainews/models/__init__.py` to populate `Base.metadata` for Alembic
  - Patterns: UUID PKs stored as `String(36)` with Python `default=lambda: str(uuid.uuid4())` — fires at flush/INSERT time, not model init time; tests need session.commit() to see the UUID
  - Patterns: JSON columns typed as `Mapped[dict[str, Any] | None]` or `Mapped[list[Any] | None]` with `sqlalchemy.JSON` column type
  - Gotchas: Parallel worker stub `runs` table (for FK resolution) becomes stale when the real `Run` model is imported by other test modules in the same pytest process — fix by using the ORM `Run` model directly in test fixtures after parallel phase completes
  - Gotchas: Raw `session.execute(text("INSERT INTO runs (id) VALUES (...)"))` bypasses Python-level ORM defaults (e.g., `status NOT NULL`) — use ORM objects for seeding FK-parent rows in tests
---

## [2026-05-07] - Phase 1 Task 2: Session management factory
- **Implemented:** `make_session_factory()` and `get_db_session()` context manager in `src/ainews/core/database.py`
- **Files changed:** `src/ainews/core/database.py`, `tests/test_database.py`
- **Commit:** 1a8b5fd
- **Learnings:**
  - Patterns: `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close pattern
  - Gotchas: Ruff SIM117 flags nested `with` statements — flatten to `with pytest.raises(...), ctx_mgr as x:` pattern or split using a named variable
  - Context: `StaticPool` is already handled in `create_engine()` for in-memory URLs; no special session factory config needed for file-based SQLite in WAL mode
---
