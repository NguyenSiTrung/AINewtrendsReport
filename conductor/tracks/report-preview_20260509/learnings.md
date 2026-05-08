# Track Learnings: report-preview_20260509

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Starlette TemplateResponse API:** Use `TemplateResponse(request, name, context)` — not `(name, {request: ..., ...})`.
- **Auth gating pattern:** Use `_require_auth(request, session)` helper that returns `RedirectResponse` or sets `request.state.user`.
- **RunLog timestamp field:** The field is `ts`, not `created_at`. Templates and queries must use `RunLog.ts`.
- **FastAPI route ordering for path params:** Static routes like `/runs/table` must be registered BEFORE parameterized `/runs/{run_id}`.
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()`.
- **Tailwind v4 standalone:** Uses CSS-based `@theme` and `@source` directives instead of `tailwind.config.js`.

---

<!-- Learnings from implementation will be appended below -->
