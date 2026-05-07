# Codebase Patterns

Reusable patterns discovered during development. Read this before starting new work.

---

- **Build backend:** Use `hatchling.build` (not `hatchling.backends`) with `packages = ["src/ainews"]` for src/ layout (from: foundations_20260507, 2026-05-07)
- **Ruff excludes:** Add `exclude = [".agents", ".beads", ".claude", "alembic"]` to `[tool.ruff]` to skip non-project directories (from: foundations_20260507, 2026-05-07)
- **Gitignore negation:** When a parent dir is ignored (e.g. `var/`), use `!var/.gitkeep` negation pattern and `git add -f` to force-track the gitkeep (from: foundations_20260507, 2026-05-07)
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings` `SettingsConfigDict(env_prefix="AINEWS_")` (from: foundations_20260507, 2026-05-07)
- **Makefile commands:** All commands use `uv run` prefix (e.g., `uv run ruff check .`, `uv run pytest --cov`) (from: foundations_20260507, 2026-05-07)
- **SQLAlchemy engine factory:** Use a custom `create_engine(url)` wrapping `event.listen(engine, "connect", handler)` to apply SQLite pragmas on every new DBAPI connection; use `StaticPool` for in-memory URLs (from: data-layer_20260507, 2026-05-07)
- **SQLite WAL tests:** WAL journal mode only applies to file-based SQLite — use `tmp_path` fixture for WAL pragma tests, not `":memory:"` (from: data-layer_20260507, 2026-05-07)
- **ORM shared Base:** All models import from `ainews.models.base.Base` (DeclarativeBase); `ainews/models/__init__.py` imports all models to populate `Base.metadata` for Alembic autogenerate (from: data-layer_20260507, 2026-05-07)
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())` — fires at ORM flush time, not model init time; tests must `session.commit()` to see the generated UUID (from: data-layer_20260507, 2026-05-07)
- **Alembic src-layout:** Set `prepend_sys_path = . src` in `alembic.ini` OR add `sys.path.insert(0, str(Path(...) / "src"))` in `env.py`; `render_as_batch=True` required in both offline and online `context.configure()` for SQLite (from: data-layer_20260507, 2026-05-07)
- **FTS5 sync triggers:** Content table FTS5 (`content=reports, content_rowid=id`) requires manual INSERT/UPDATE/DELETE triggers; UPDATE = DELETE old + INSERT new using the `'delete'` special FTS5 command (from: data-layer_20260507, 2026-05-07)
- **pre-commit mypy deps:** When adding new runtime packages (e.g., sqlalchemy, alembic), also add them to `additional_dependencies` in the `mirrors-mypy` hook in `.pre-commit-config.yaml` (from: data-layer_20260507, 2026-05-07)
- **Idempotent upsert:** Use `select(Model).filter_by(key=value).scalar_one_or_none()` — if None insert, else skip; count both outcomes for user-facing output (from: data-layer_20260507, 2026-05-07)
- **Typer sub-app invoke:** `seed_app = typer.Typer(invoke_without_command=True)` + `@seed_app.callback(invoke_without_command=True)` makes `ainews seed` run directly; check `ctx.invoked_subcommand is not None` to guard against subcommand passthrough (from: data-layer_20260507, 2026-05-07)
