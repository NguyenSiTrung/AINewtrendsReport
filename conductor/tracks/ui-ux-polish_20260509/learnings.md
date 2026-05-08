# Track Learnings: ui-ux-polish_20260509

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Tailwind v4 standalone:** Uses CSS-based `@theme` and `@source` directives instead of `tailwind.config.js`. `@custom-variant dark` replaces the old `darkMode: 'class'` config.
- **Starlette TemplateResponse API:** Use `TemplateResponse(request, name, context)` — not `(name, {request: ..., ...})`.
- **Jinja2Templates initialization:** Create in `create_app()`, not `lifespan()`, because test fixtures bypass lifespan.
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()`.
- **Auth gating pattern:** Use `_require_auth(request, session)` helper in all protected routes.
- **RunLog timestamp field:** The field is `ts`, not `created_at`. Templates and queries must use `RunLog.ts`.
- **FastAPI route ordering for path params:** Static routes must be registered BEFORE parameterized routes.
- **HTMX conditional polling:** Use Jinja2 `{% if %}` to conditionally include `hx-trigger`. Polling stops when server returns HTML without it.

---

<!-- Learnings from implementation will be appended below -->
