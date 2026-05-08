# Track Learnings: admin-ui_20260508

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings`.
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps like `langchain_openai.ChatOpenAI`.
- **Makefile commands:** All commands use `uv run` prefix.
- **Typer Option defaults:** Using `typer.Option()` directly in function parameter defaults causes Ruff rule `B008`. Add `"src/ainews/cli.py" = ["B008"]` to `[tool.ruff.lint.per-file-ignores]`.
- **Build backend:** Use `hatchling.build` with `packages = ["src/ainews"]` for src/ layout.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **ORM shared Base:** All models import from `ainews.models.base.Base`.
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.
- **httpx mocking:** Use `respx.mock` decorator for httpx tests; `with respx.mock:` for CliRunner tests.

---

<!-- Learnings from implementation will be appended below -->

## [2026-05-08 12:58] - Phase 1: Foundation & Base Layout
- **Implemented:** Tailwind CSS v4 standalone, Jinja2 templates, CSRF middleware, flash messages, base layout, views router
- **Files changed:** Makefile, pyproject.toml, src/ainews/api/main.py, src/ainews/api/flash.py, src/ainews/api/middleware/__init__.py, src/ainews/api/middleware/csrf.py, src/ainews/api/routes/views.py, src/ainews/api/static/src/input.css, src/ainews/api/static/css/output.css, src/ainews/api/templates/base.html, src/ainews/api/templates/dashboard.html, src/ainews/api/templates/partials/flash.html, tests/test_admin_foundation.py
- **Commit:** b74c6d6
- **Learnings:**
  - Patterns: Tailwind v4 uses CSS-based `@theme` and `@source` instead of `tailwind.config.js`. `@custom-variant dark` replaces the old `darkMode: 'class'` config.
  - Patterns: Starlette's `TemplateResponse` API changed to `(request, name, context)` instead of `(name, {request: ..., ...})` — must use the new signature.
  - Gotchas: `Jinja2Templates` must be created in `create_app()`, not in `lifespan()`, because test fixtures bypass lifespan by setting `app.state.engine` directly.
  - Gotchas: `python-multipart` is required for form parsing in CSRF middleware. Must be added to `pyproject.toml` dependencies.
  - Context: The views router uses a `_render()` helper that injects `get_flashed_messages` into every template context.
---

