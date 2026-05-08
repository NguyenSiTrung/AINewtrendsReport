# Plan: Admin UI/UX Polish & Enhancement

## Phase 1: Design System Foundation & Critical Fixes
<!-- execution: parallel -->

- [x] Task 1: Define accent color & fill surface palette gaps
  <!-- files: src/ainews/api/static/src/input.css -->
  - [x] Add `--color-accent-*` scale (teal/emerald hue) to `@theme`
  - [x] Add `surface-300` through `surface-600` steps
  - [x] Rebuild Tailwind output: `npx @tailwindcss/cli -i ... -o ...`
  - [x] Verify accent color renders in report card

- [x] Task 2: Fix report dark mode & move inline styles
  <!-- files: src/ainews/api/templates/runs/report.html, src/ainews/api/static/src/input.css -->
  - [x] Remove `@media (prefers-color-scheme: dark)` block from report.html
  - [x] Migrate `.dark .report-content` styles to `input.css`
  - [x] Remove inline `<style>` block from report.html
  - [x] Verify dark mode renders consistently

- [x] Task 3: Fix duration card & pin Alpine.js
  <!-- files: src/ainews/api/templates/runs/detail.html, src/ainews/api/templates/base.html, src/ainews/api/templates/login.html -->
  - [x] Compute `finished_at - started_at` as human-readable duration
  - [x] Replace `{{ run.finished_at[:19] }}` with computed value
  - [x] Pin Alpine.js to specific version in base.html and login.html

- [x] Task 4: Add favicon
  <!-- files: src/ainews/api/static/favicon.svg, src/ainews/api/templates/base.html, src/ainews/api/templates/login.html -->
  - [x] Create lightning-bolt SVG favicon
  - [x] Add `<link rel="icon">` to base.html and login.html

- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

**Exit Criteria:** Accent color visible in report card, dark mode consistent, duration shows "Xm Ys", Alpine pinned, favicon in browser tab.

---

## Phase 2: Reusable UI Components
<!-- execution: parallel -->

- [x] Task 1: Pagination partial
  <!-- files: src/ainews/api/templates/partials/pagination.html -->
  - [x] Create reusable pagination component accepting `page`, `total_pages`, `base_url`
  - [x] Support query param preservation
  - [x] Dark mode styling
  - [x] HTMX `hx-get` integration with `hx-push-url`

- [x] Task 2: Breadcrumb partial
  <!-- files: src/ainews/api/templates/partials/breadcrumbs.html, src/ainews/api/templates/base.html -->
  - [x] Create breadcrumb component accepting `breadcrumbs` context list
  - [x] Add to base.html main content area (above page content)
  - [x] Style with muted separators and active item highlight

- [x] Task 3: Form loading state pattern
  <!-- files: src/ainews/api/static/src/input.css, src/ainews/api/templates/login.html, src/ainews/api/templates/trigger.html, src/ainews/api/templates/llm.html, src/ainews/api/templates/sites/form.html, src/ainews/api/templates/schedules/form.html, src/ainews/api/templates/settings.html -->
  - [x] Add `btn-loading` CSS utility with spinner animation
  - [x] Add Alpine.js loading pattern to all form submit buttons
  - [x] Disable button during submission

- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

**Exit Criteria:** Pagination, breadcrumbs, and loading states render correctly in isolation.

---

## Phase 3: Logs Page Overhaul
<!-- depends: phase2 -->

- [x] Task 1: Server-side log filtering & pagination backend
  <!-- files: src/ainews/api/routes/views.py -->
  - [x] Add query params: `level`, `search`, `run_id`, `page`, `per_page`
  - [x] Build SQLAlchemy query with conditional `.where()` clauses
  - [x] Compute level counts via `func.count` grouped by level
  - [x] Return pagination metadata in template context
  - [x] Write tests for filter combinations

- [x] Task 2: Logs page template redesign
  <!-- files: src/ainews/api/templates/logs.html, src/ainews/api/templates/partials/logs_table.html -->
  - [x] Create toolbar with level-filter pills, search input, run-id filter
  - [x] Extract log entries into `partials/logs_table.html`
  - [x] Add summary bar showing counts per level
  - [x] Wire HTMX `hx-get` on filter changes with `hx-push-url`
  - [x] Add auto-refresh toggle (Alpine + HTMX conditional polling)
  - [x] Include pagination partial
  - [x] Dark mode parity

- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

**Exit Criteria:** Logs page filters by level, searches text, paginates, shows summary counts, optional auto-refresh works.

---

## Phase 4: Dashboard Enhancement
<!-- depends: phase1 -->

- [x] Task 1: SVG sparkline & ring chart helpers
  <!-- files: src/ainews/api/routes/views.py -->
  - [x] Create `_sparkline_svg(data_points, width, height)` helper returning SVG string
  - [x] Create `_ring_chart_svg(percentage, size)` helper returning SVG donut
  - [x] Compute runs-per-day for last 7 days from DB
  - [x] Pass SVG strings and chart data to dashboard template context

- [x] Task 2: Dashboard template enhancements
  <!-- files: src/ainews/api/templates/dashboard.html -->
  - [x] Add health ribbon at top (dot + label, HTMX-refreshed)
  - [x] Embed sparkline SVG in "Total Runs" card
  - [x] Embed ring chart SVG in "Success Rate" card
  - [x] Add "Latest Report" quick-access card
  - [x] Add personalized greeting with time-of-day context
  - [x] Dark mode parity

- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)

**Exit Criteria:** Dashboard shows sparkline, ring chart, health ribbon, latest report card, and greeting.

---

## Phase 5: Navigation, Layout & Polish
<!-- execution: parallel -->
<!-- depends: phase2 -->

- [x] Task 1: Sidebar navigation groups
  <!-- files: src/ainews/api/templates/base.html -->
  - [x] Group nav items: Overview, Pipeline, System
  - [x] Add muted uppercase section headers
  - [x] Alpine.js collapsible groups with localStorage persistence

- [x] Task 2: Wire pagination into list pages
  <!-- files: src/ainews/api/routes/views.py, src/ainews/api/templates/partials/runs_table.html, src/ainews/api/templates/sites/list.html, src/ainews/api/templates/schedules/list.html -->
  - [x] Add `page`/`per_page` params to sites, schedules, runs routes
  - [x] Include pagination partial in each list template
  - [x] Write tests for pagination boundary cases

- [x] Task 3: Wire breadcrumbs into sub-pages
  <!-- files: src/ainews/api/routes/views.py, src/ainews/api/templates/sites/form.html, src/ainews/api/templates/schedules/form.html, src/ainews/api/templates/runs/detail.html, src/ainews/api/templates/runs/report.html, src/ainews/api/templates/settings.html, src/ainews/api/templates/llm.html -->
  - [x] Add `breadcrumbs` list to template context in each route
  - [x] Include breadcrumb partial in base.html

- [x] Task 4: Contextual empty states
  <!-- files: src/ainews/api/templates/sites/list.html, src/ainews/api/templates/schedules/list.html, src/ainews/api/templates/partials/runs_table.html, src/ainews/api/templates/logs.html -->
  - [x] Per-page SVG icons and descriptive guidance copy
  - [x] Dark mode parity

- [x] Task 5: Mobile stepper responsiveness
  <!-- files: src/ainews/api/templates/partials/run_stepper.html, src/ainews/api/static/src/input.css -->
  - [x] Vertical layout on small viewports
  - [x] Fade-gradient scroll indicators for horizontal overflow
  - [x] Test on narrow viewport

- [x] Task 6: Server-side sites search
  <!-- files: src/ainews/api/routes/views.py, src/ainews/api/templates/sites/list.html -->
  - [x] Replace Alpine `x-show` with HTMX `hx-get` search
  - [x] Add "showing X of Y" counter
  - [x] Debounce search input with `hx-trigger="keyup changed delay:300ms"`

- [x] Task 7: Keyboard shortcuts
  <!-- files: src/ainews/api/templates/base.html -->
  - [x] Add JS `@keydown.window` listener for Ctrl/Cmd+K
  - [x] Focus search input or show command palette stub
  - [x] Visual hint in sidebar footer

- [ ] Task: Conductor - User Manual Verification 'Phase 5' (Protocol in workflow.md)

**Exit Criteria:** Sidebar grouped, all lists paginated, breadcrumbs on sub-pages, empty states contextual, stepper mobile-friendly, sites search server-side, keyboard shortcut works.

---

## Phase 6: Final Verification & Tailwind Rebuild
<!-- depends: phase3, phase4, phase5 -->

- [ ] Task 1: Tailwind rebuild & lint pass
  - [ ] Rebuild Tailwind CSS output
  - [ ] Run `ruff check . && ruff format --check . && mypy src/`
  - [ ] Run `pytest --cov` — all existing tests green
  - [ ] Manual spot-check: dark mode on all pages

- [ ] Task 2: Commit & cleanup
  - [ ] Final commit with all changes
  - [ ] Update PLAN.md if needed

- [ ] Task: Conductor - User Manual Verification 'Phase 6' (Protocol in workflow.md)

**Exit Criteria:** Lints pass, tests green, dark mode consistent across all pages, Tailwind rebuilt.
