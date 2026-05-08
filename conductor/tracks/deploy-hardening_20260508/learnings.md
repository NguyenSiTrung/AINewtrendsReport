# Track Learnings: deploy-hardening_20260508

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings`.
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps.
- **Makefile commands:** All commands use `uv run` prefix.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.
- **LangGraph node decorator typing:** `# type: ignore[call-overload]` on `add_node()` calls.
- **httpx mocking:** Use `respx.mock` decorator for httpx tests.
- **Tailwind v4 standalone:** Uses CSS-based `@theme` and `@source` directives.
- **Starlette TemplateResponse API:** Use `TemplateResponse(request, name, context)`.
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()`.
- **Auth gating pattern:** Use `_require_auth(request, session)` helper.
- **RunLog timestamp field:** The field is `ts`, not `created_at`.

---

<!-- Learnings from implementation will be appended below -->
