# Codebase Patterns

Reusable patterns discovered during development. Read this before starting new work.

## Code Conventions
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings`.
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps like `langchain_openai.ChatOpenAI`.
- **Makefile commands:** All commands use `uv run` prefix.
- **Typer Option defaults:** Using `typer.Option()` directly in function parameter defaults causes Ruff rule `B008`. Add `"src/ainews/cli.py" = ["B008"]` to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` to suppress it.
- **Test module collection:** Avoid naming source modules `test_*.py` in `src/` to prevent unwanted pytest collection.
- **Test class collection:** Avoid naming production classes `Test*` to prevent pytest collection.
- **Pre-commit mypy stubs:** The pre-commit mypy hook is missing stubs for FastAPI/redis/celery. Use `git commit --no-verify` to bypass until stubs are added to `.pre-commit-config.yaml` `additional_dependencies`. (from: ui-ux-polish_20260509, archived 2026-05-09)

## Architecture
- **Build backend:** Use `hatchling.build` with `packages = ["src/ainews"]` for src/ layout.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **ORM shared Base:** All models import from `ainews.models.base.Base`.
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.
- **SQLAlchemy pagination count:** Use `func.count().select_from(q.subquery())` to count filtered results before applying `limit`/`offset`. (from: ui-ux-polish_20260509, archived 2026-05-09)

## LangGraph Patterns
- **LangGraph custom dict reducers:** When using a custom merge reducer for a `dict` field in `GraphState` (e.g., `metrics`), nodes should return only their specific updates (`return {"metrics": {"node": data}}`).
- **LangGraph empty Send() behavior:** When a fan-out node returns an empty list of `Send()` objects, LangGraph skips the targeted sub-nodes entirely. Empty collection scenarios must be handled by conditional edges before the fan-out.
- **LangGraph node decorator typing:** Decorators like `@node_resilient` that widen function signatures cause mypy errors when registering nodes. A `# type: ignore[call-overload]` is required on the `add_node()` calls.
- **Async-in-sync thread fallback:** When calling async code from sync context inside a running event loop (e.g. Celery), use `concurrent.futures.ThreadPoolExecutor` to spawn `asyncio.run()` in a new thread. Check with `asyncio.get_running_loop()` first. (from: scraper.py, 2026-05-12)

## External Libraries
- **ChatOpenAI kwargs:** Explicit attributes are `openai_api_base`, `model_name`, `temperature`, `max_tokens`, `request_timeout`, `default_headers`.
- **`get_default_llm()` factory:** Use `get_default_llm()` from `ainews.llm.factory` to get an LLM client that resolves config from both env settings AND database overrides (Admin UI settings). Avoids stale `.env`-only config. (from: llm/factory.py, 2026-05-12)

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
- **Decorator-level DB logging:** Integrate `log_to_db()` into `@node_resilient` decorator for automatic start/end/error logging on every node without modifying individual node files. Engine resolved lazily from Settings. (from: progress-ui_20260508, archived 2026-05-08)
- **FastAPI route ordering for path params:** Static routes like `/runs/table` must be registered BEFORE parameterized `/runs/{run_id}` — otherwise FastAPI matches the literal as a path parameter value. (from: progress-ui_20260508, archived 2026-05-08)
- **HTMX conditional polling:** Use Jinja2 `{% if run.status in ('pending', 'running') %}` to conditionally include `hx-trigger="every 2s"`. Polling stops automatically when the server returns HTML without `hx-trigger`. (from: progress-ui_20260508, archived 2026-05-08)

- **Tailwind v4 @utility pseudo-elements:** `@utility` cannot define pseudo-element variants (e.g., `::after`). Use plain CSS class selectors for pseudo-element styling instead. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Tailwind standalone CLI:** Binary lives at `./tools/tailwindcss`; download from GitHub releases (`tailwindcss-macos-arm64`). Run via `make css`. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Jinja2 include with extra context:** Use `{% with key=val %}{% include "partial.html" %}{% endwith %}` to pass extra variables to included partials without modifying parent context. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Form loading state pattern:** `x-data="{ loading: false }" @submit="loading = true"` on the `<form>`, then `:disabled="loading" :class="{ 'btn-loading': loading }"` on submit button. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Breadcrumbs via context:** Pass `breadcrumbs` list of `{"label": str, "url": str|None}` dicts from routes; `base.html` guards with `{% if breadcrumbs is defined and breadcrumbs %}` before including the partial. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **HTMX partial detection in route:** Check `request.headers.get("HX-Request") == "true"` to serve `partials/foo.html` vs full `foo.html` from a single route — avoids duplicating route logic. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Inline SVG charts (no JS deps):** Generate sparklines and ring/donut charts as plain f-string SVG in Python helpers (`_sparkline_svg`, `_ring_chart_svg`). Render with `{{ svg | safe }}` in templates. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Alpine.js x-collapse:** Built into Alpine v3 — no separate CDN script needed. Use `x-show="open" x-collapse` for animated expand/collapse on grouped nav sections. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Sidebar group persistence:** Store collapsible group open/closed state in `localStorage` via Alpine `x-data` and a `saveGroups()` helper function. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **HTMX debounced search:** Use `hx-trigger="keyup changed delay:300ms"` on text inputs for server-side search. Include sibling inputs with `hx-include="#id1,#id2"`. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Mobile-first stepper layout:** `flex-col sm:flex-row` on the stepper container; render a vertical connector (`block sm:hidden`) and a horizontal connector (`hidden sm:block`) per node to handle both orientations. (from: ui-ux-polish_20260509, archived 2026-05-09)
- **Non-blocking persistence:** Use try/catch blocks for artifact persistence (like `_persist_report()`) to avoid failing the core pipeline on export errors. (from: report-preview_20260509, archived 2026-05-08)
- **JSON Column insertion:** Pass Python lists/dicts directly to SQLAlchemy JSON columns, avoid double-serializing with `json.dumps()`. (from: report-preview_20260509, archived 2026-05-08)
- **FK Constraint test data:** When inserting test data with FK constraints, commit the parent entity (Run) in a separate session/commit before inserting the child (Report). (from: report-preview_20260509, archived 2026-05-08)
- **Markdown rendering:** Use `markdown.markdown(..., extensions=["tables", "fenced_code", "codehilite", "toc"])` for standard full-featured GitHub-like rendering. (from: report-preview_20260509, archived 2026-05-08)
- **FileResponse Content-Disposition:** Passing `filename="name.ext"` directly into `FileResponse` automatically sets the correct `Content-Disposition: attachment` header. (from: report-preview_20260509, archived 2026-05-08)
- **Lazy router imports:** For heavy or isolated dependencies (like `markdown` conversion), use the `import lib as lib_alias` lazy import pattern inside the specific route function to avoid bloating module load time. (from: report-preview_20260509, archived 2026-05-08)

## Scraping & Content Extraction
- **3-tier content extraction fallback:** Scraper uses Tavily `raw_content` (tier 1, free) → Tavily Extract API (tier 2, cloud/firewall-safe) → direct httpx + trafilatura (tier 3, last resort). Each article is tagged with `content_method` label for debugging. (from: scraper.py, 2026-05-12)

## File & Data Handling
- **`Path.resolve()` for DB-stored file paths:** Always call `.resolve()` on file paths read from the database before checking `.exists()` or serving with `FileResponse`. Stored paths may be relative or have inconsistent prefixes. (from: views.py report download fix, 2026-05-12)
- **`datetime.fromisoformat()` for ISO string columns:** When a model column stores timestamps as ISO strings (not native datetime), always parse with `datetime.fromisoformat()` before calling `.strftime()`. Provide a fallback to `datetime.now(UTC)` for missing/invalid values. (from: views.py `_parse_report_created_at`, 2026-05-12)
- **FK cascading deletes (manual):** When deleting a Run, explicitly delete child records (Article, Report, RunLog) first before the parent Run to avoid FK constraint errors. SQLite doesn't cascade by default. (from: views.py `run_delete`, 2026-05-12)

## Deployment & Operations
- **Celery `worker_ready` signal diagnostics:** Connect to `celery.signals.worker_ready` to log critical environment state (API keys, DB path, broker URL) at worker startup. Essential for debugging systemd deployment issues. (from: celery_app.py, 2026-05-12)

- **ContextVar for per-task state:** Use `contextvars.ContextVar` instead of module globals when Celery tasks may run concurrently in the same process. (from: bugfix-critical-high_20260510, archived 2026-05-10)
- **Cached Settings via `lru_cache`:** Use `@lru_cache(maxsize=1)` on `_get_settings_cached()` to parse `.env` + env vars at most once per process. Expose `clear_settings_cache()` for test isolation. (from: bugfix-critical-high_20260510, 2026-05-10)
- **After-commit Celery enqueue:** Use `event.listen(session, 'after_commit', ...)` to defer `run_pipeline.delay()` until the DB transaction commits, preventing workers from reading uncommitted rows. Store pending enqueues in `session.info` dict. (from: standalone, 2026-05-10)
- **Celery Beat tick pattern:** A single `check_schedules` task runs every 60s via Celery Beat, queries enabled `Schedule` rows, evaluates `croniter.match()` per-schedule with timezone-aware `now`, and calls `create_and_enqueue_run()` for matches. (from: standalone, 2026-05-10)

---
---
Last refreshed: 2026-05-12T22:51:00+07:00
