# Track Learnings: llm-tools_20260507

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Build backend:** Use `hatchling.build` (not `hatchling.backends`) with `packages = ["src/ainews"]` for src/ layout
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings` `SettingsConfigDict(env_prefix="AINEWS_")`
- **Makefile commands:** All commands use `uv run` prefix (e.g., `uv run ruff check .`, `uv run pytest --cov`)
- **SQLAlchemy engine factory:** Use a custom `create_engine(url)` wrapping `event.listen(engine, "connect", handler)` to apply SQLite pragmas
- **ORM shared Base:** All models import from `ainews.models.base.Base`
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`
- **pre-commit mypy deps:** When adding new runtime packages, also add them to `additional_dependencies` in the `mirrors-mypy` hook
- **Ruff SIM117:** Flatten nested `with` statements — `with pytest.raises(...), ctx_mgr as x:` pattern
- **CliRunner env injection:** `CliRunner` from `typer.testing` supports `env={"KEY": "value"}` to inject env vars
- **Typer sub-app invoke:** Use `invoke_without_command=True` + `@app.callback(invoke_without_command=True)` for direct sub-app commands

---

<!-- Learnings from implementation will be appended below -->
