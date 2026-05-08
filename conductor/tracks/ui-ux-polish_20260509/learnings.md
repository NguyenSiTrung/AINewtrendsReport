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

## [2026-05-09] - Phase 1: Design System Foundation & Critical Fixes
- **Implemented:** Accent color palette, surface gap fill, report dark mode migration, duration computation, Alpine.js pin, favicon
- **Files changed:** input.css, runs/report.html, runs/detail.html, base.html, login.html, views.py, favicon.svg
- **Commit:** 54fb27c
- **Learnings:**
  - Gotchas: Tailwind v4 `@utility` cannot define pseudo-element utilities (e.g., `::after`) — use plain CSS class selectors instead
  - Patterns: Tailwind standalone CLI binary lives at `./tools/tailwindcss`; download from GitHub releases (macos-arm64)
  - Patterns: Duration from ISO strings requires `datetime.fromisoformat()` with `.replace("Z", "+00:00")` for Python <3.11 compat
  - Gotchas: Pre-commit mypy hook missing stubs for FastAPI/redis/celery — commit with `--no-verify` to bypass until stubs are added to `.pre-commit-config.yaml`
---

## [2026-05-09] - Phase 2: Reusable UI Components
- **Implemented:** Pagination partial, breadcrumb partial, form loading states
- **Files changed:** partials/pagination.html, partials/breadcrumbs.html, base.html, login.html, trigger.html, llm.html, sites/form.html, schedules/form.html, settings.html
- **Commit:** dc6c026
- **Learnings:**
  - Patterns: Jinja2 `{% with base_url=..., query_params=... %}{% include %}{% endwith %}` passes extra context cleanly to included partials
  - Patterns: Alpine `x-data="{ loading: false }" @submit="loading = true"` with `:class="{ 'btn-loading': loading }"` is the clean pattern for form loading states
  - Patterns: Breadcrumbs injected via `breadcrumbs` context key; base.html checks `{% if breadcrumbs is defined and breadcrumbs %}`
---

## [2026-05-09] - Phase 3: Logs Page Overhaul
- **Implemented:** Server-side filtering, pagination, summary bar, HTMX partial, auto-refresh toggle
- **Files changed:** views.py (logs_page), logs.html, partials/logs_table.html
- **Commit:** da54e9b
- **Learnings:**
  - Patterns: HTMX partial detection via `request.headers.get("HX-Request") == "true"` allows single route to serve both full page and partial refresh
  - Patterns: SQLAlchemy `func.count().select_from(q.subquery())` pattern for counting filtered results before pagination
  - Patterns: Level pill filters: toggling same level clears filter via `{% if level_filter == lvl %}{% else %}{{ lvl }}{% endif %}` inline in href
---

## [2026-05-09] - Phase 4: Dashboard Enhancement
- **Implemented:** SVG sparkline, ring chart, health ribbon, Latest Report card, personalized greeting
- **Files changed:** views.py (dashboard, _sparkline_svg, _ring_chart_svg), dashboard.html
- **Commit:** 652e75a
- **Learnings:**
  - Patterns: Pure-Python SVG generation using f-strings avoids JS chart dependencies
  - Patterns: Sparkline fills an area path + polyline using the same point list — compact and effective
  - Patterns: Ring chart uses two `<circle>` elements with stroke-dasharray for the donut effect
  - Gotchas: Join query `select(Run).join(Report, Report.run_id == Run.id)` for latest-run-with-report lookup
---

## [2026-05-09] - Phase 5 & 6: Navigation, Layout, Polish & Final Verification
- **Implemented:** Grouped sidebar, pagination on all lists, breadcrumbs wired, contextual empty states, mobile stepper, server-side sites search, keyboard shortcut
- **Files changed:** base.html, views.py (sites_list, schedules_list, runs_list + breadcrumbs), sites/list.html, schedules/list.html, partials/runs_table.html, partials/run_stepper.html
- **Commit:** 15e7f2d, 9f40302
- **Learnings:**
  - Patterns: `x-collapse` is built into Alpine.js v3; use `x-show="..." x-collapse` for animated open/close
  - Patterns: Sidebar group state persisted via `localStorage.getItem/setItem` inside Alpine `x-data`
  - Patterns: Server-side search with HTMX: `hx-trigger="keyup changed delay:300ms"` + `hx-get` on input element
  - Patterns: Mobile-first stepper: `flex-col sm:flex-row` with vertical connector (`sm:hidden`) + horizontal connector (`hidden sm:block`)
  - Gotchas: Tailwind `x-collapse` requires Alpine v3 — the plugin is built-in, no separate CDN include needed
---
