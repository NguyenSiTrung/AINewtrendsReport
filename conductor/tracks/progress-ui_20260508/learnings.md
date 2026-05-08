# Track Learnings: progress-ui_20260508

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Tailwind v4 standalone:** Uses CSS-based `@theme` and `@source` directives instead of `tailwind.config.js`. `@custom-variant dark` replaces the old `darkMode: 'class'` config.
- **Starlette TemplateResponse API:** Use `TemplateResponse(request, name, context)` — not `(name, {request: ..., ...})`.
- **Jinja2Templates initialization:** Create in `create_app()`, not `lifespan()`, because test fixtures bypass lifespan by setting `app.state.engine` directly.
- **python-multipart dependency:** Required for `Form()` parameter parsing and CSRF middleware form access.
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()` — compare header/cookie values instead.
- **Auth gating pattern:** Use `_require_auth(request, session)` helper that returns `RedirectResponse` or sets `request.state.user`.
- **RunLog timestamp field:** The field is `ts`, not `created_at`. Templates and queries must use `RunLog.ts`.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.

---

<!-- Learnings from implementation will be appended below -->
