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
- **Alembic check:** `alembic check` returns non-zero when pending migrations exist — expected before first `revision --autogenerate`; use it to verify metadata is loaded correctly (from: data-layer_20260507, 2026-05-07)
- **FTS5 rowid:** FTS5 content tables with `content_rowid=id` require the `id` column to be INTEGER PK in SQLite (which maps `rowid = id`) (from: data-layer_20260507, 2026-05-07)
- **CliRunner env injection:** `CliRunner` from `typer.testing` supports `env={"KEY": "value"}` to inject env vars; use with `AINEWS_DB_PATH` to redirect DB for tests (from: data-layer_20260507, 2026-05-07)
- **JSON columns:** JSON columns typed as `Mapped[dict[str, Any] | None]` or `Mapped[list[Any] | None]` with `sqlalchemy.JSON` column type (from: data-layer_20260507, 2026-05-07)
- **Session defaults:** Raw `session.execute(text("INSERT ..."))` bypasses Python-level ORM defaults — use ORM objects for seeding FK-parent rows in tests (from: data-layer_20260507, 2026-05-07)
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close pattern (from: data-layer_20260507, 2026-05-07)
- **Ruff SIM117:** Ruff SIM117 flags nested `with` statements — flatten to `with pytest.raises(...), ctx_mgr as x:` pattern or split using a named variable (from: data-layer_20260507, 2026-05-07)
- **Test module collection:** Naming source modules `test_*.py` in `src/` causes pytest to collect them — rename to avoid (e.g. `connectivity.py`) (from: llm-tools_20260507, 2026-05-08)
- **Test class collection:** Classes named `Test*` in production code get collected by pytest — use prefixes like `ConnectionTestResult` (from: llm-tools_20260507, 2026-05-08)
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps (e.g. `langchain_openai.ChatOpenAI`) to keep module load fast (from: llm-tools_20260507, 2026-05-08)
- **httpx mocking:** Use `respx.mock` decorator for httpx tests; use `with respx.mock:` context manager for CliRunner tests (from: llm-tools_20260507, 2026-05-08)
- **ChatOpenAI kwargs:** `ChatOpenAI` kwargs mapping: `openai_api_base`, `model_name`, `temperature`, `max_tokens`, `request_timeout`, `default_headers` (from: llm-tools_20260507, 2026-05-08)
- **LangGraph custom dict reducers:** When using a custom merge reducer for a `dict` field in `GraphState` (e.g., `metrics`), nodes should return only their specific updates (`return {"metrics": {"node": data}}`), rather than trying to copy and merge with the existing state themselves (from: langgraph-workflow_20260508, 2026-05-08)
- **LangGraph empty Send() behavior:** When a fan-out node returns an empty list of `Send()` objects, LangGraph skips the targeted sub-nodes entirely. The fan-in node is not executed, so any conditional edges after the fan-in will not trigger. Empty collection scenarios must be handled by conditional edges before the fan-out (from: langgraph-workflow_20260508, 2026-05-08)
- **LangGraph node decorator typing:** Decorators like `@node_resilient` that widen function signatures to `Callable[[Any], ...]` will cause mypy errors when registering nodes. A `# type: ignore[call-overload]` is required on the `add_node()` calls (from: langgraph-workflow_20260508, 2026-05-08)
- **Typer Option defaults:** Using `typer.Option()` directly in function parameter defaults causes Ruff rule `B008` (false positive for Typer's standard pattern). Add `"src/ainews/cli.py" = ["B008"]` to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` to suppress it (from: langgraph-workflow_20260508, 2026-05-08)

---
Last refreshed: 2026-05-08T01:27:00+07:00
