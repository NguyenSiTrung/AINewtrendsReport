# Codebase Patterns

Reusable patterns discovered during development. Read this before starting new work.

## Code Conventions
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings`.
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps like `langchain_openai.ChatOpenAI`.
- **Makefile commands:** All commands use `uv run` prefix.
- **Typer Option defaults:** Using `typer.Option()` directly in function parameter defaults causes Ruff rule `B008`. Add `"src/ainews/cli.py" = ["B008"]` to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` to suppress it.
- **Test module collection:** Avoid naming source modules `test_*.py` in `src/` to prevent unwanted pytest collection.
- **Test class collection:** Avoid naming production classes `Test*` to prevent pytest collection.

## Architecture
- **Build backend:** Use `hatchling.build` with `packages = ["src/ainews"]` for src/ layout.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **ORM shared Base:** All models import from `ainews.models.base.Base`.
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.

## LangGraph Patterns
- **LangGraph custom dict reducers:** When using a custom merge reducer for a `dict` field in `GraphState` (e.g., `metrics`), nodes should return only their specific updates (`return {"metrics": {"node": data}}`).
- **LangGraph empty Send() behavior:** When a fan-out node returns an empty list of `Send()` objects, LangGraph skips the targeted sub-nodes entirely. Empty collection scenarios must be handled by conditional edges before the fan-out.
- **LangGraph node decorator typing:** Decorators like `@node_resilient` that widen function signatures cause mypy errors when registering nodes. A `# type: ignore[call-overload]` is required on the `add_node()` calls.

## External Libraries
- **ChatOpenAI kwargs:** Explicit attributes are `openai_api_base`, `model_name`, `temperature`, `max_tokens`, `request_timeout`, `default_headers`.

## Testing
- **httpx mocking:** Use `respx.mock` decorator for httpx tests; `with respx.mock:` for CliRunner tests.

## Admin UI / Frontend
- **Tailwind v4 standalone:** Uses CSS-based `@theme` and `@source` directives instead of `tailwind.config.js`. `@custom-variant dark` replaces the old `darkMode: 'class'` config. (from: admin-ui_20260508, archived 2026-05-08)
- **Starlette TemplateResponse API:** Use `TemplateResponse(request, name, context)` — not `(name, {request: ..., ...})`. (from: admin-ui_20260508, archived 2026-05-08)
- **Jinja2Templates initialization:** Create in `create_app()`, not `lifespan()`, because test fixtures bypass lifespan by setting `app.state.engine` directly. (from: admin-ui_20260508, archived 2026-05-08)
- **python-multipart dependency:** Required for `Form()` parameter parsing and CSRF middleware form access. Must be in `pyproject.toml`. (from: admin-ui_20260508, archived 2026-05-08)
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()` — this prevents downstream FastAPI `Form()` injection from working. Compare header/cookie values instead. (from: admin-ui_20260508, archived 2026-05-08)
- **Auth gating pattern:** Use `_require_auth(request, session)` helper that returns `RedirectResponse` or sets `request.state.user`. All protected routes call this first. (from: admin-ui_20260508, archived 2026-05-08)
- **RunLog timestamp field:** The field is `ts`, not `created_at`. Templates and queries must use `RunLog.ts`. (from: admin-ui_20260508, archived 2026-05-08)

---
Last refreshed: 2026-05-08T13:44:00+07:00
