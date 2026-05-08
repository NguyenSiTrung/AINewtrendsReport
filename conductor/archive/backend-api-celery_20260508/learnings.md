# Track Learnings: backend-api-celery_20260508

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings`.
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps like `langchain_openai.ChatOpenAI`.
- **Makefile commands:** All commands use `uv run` prefix.
- **Typer Option defaults:** Using `typer.Option()` directly causes Ruff B008. Suppressed in `pyproject.toml`.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **ORM shared Base:** All models import from `ainews.models.base.Base`.
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.
- **LangGraph node decorator typing:** `# type: ignore[call-overload]` required on `add_node()` calls.
- **httpx mocking:** Use `respx.mock` decorator for httpx tests; `with respx.mock:` for CliRunner tests.

---

<!-- Learnings from implementation will be appended below -->
