# Track Learnings: langgraph-workflow_20260508

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Build backend:** Use `hatchling.build` with `packages = ["src/ainews"]` for src/ layout
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings`
- **Makefile commands:** All commands use `uv run` prefix
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs
- **ORM shared Base:** All models import from `ainews.models.base.Base`
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close
- **Test module collection:** Avoid naming source modules `test_*.py` in `src/` (pytest collects them)
- **Test class collection:** Classes named `Test*` in production code get collected — use different prefixes
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps (e.g. `langchain_openai.ChatOpenAI`)
- **httpx mocking:** Use `respx.mock` decorator for httpx tests; `with respx.mock:` for CliRunner tests
- **ChatOpenAI kwargs:** `openai_api_base`, `model_name`, `temperature`, `max_tokens`, `request_timeout`, `default_headers`

---

<!-- Learnings from implementation will be appended below -->
