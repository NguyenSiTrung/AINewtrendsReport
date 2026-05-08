# Plan: Admin UI/UX Polish & Enhancement

## Phase 1: Design System Foundation & Critical Fixes
<!-- execution: parallel -->

- [ ] Task 1: Define accent color & fill surface palette gaps
  <!-- files: src/ainews/api/static/src/input.css -->
  - [ ] Add `--color-accent-*` scale (teal/emerald hue) to `@theme`
  - [ ] Add `surface-300` through `surface-600` steps
  - [ ] Rebuild Tailwind output: `npx @tailwindcss/cli -i ... -o ...`
  - [ ] Verify accent color renders in report card

- [ ] Task 2: Fix report dark mode & move inline styles
  <!-- files: src/ainews/api/templates/runs/report.html, src/ainews/api/static/src/input.css -->
  - [ ] Remove `@media (prefers-color-scheme: dark)` block from report.html
  - [ ] Migrate `.dark .report-content` styles to `input.css`
  - [ ] Remove inline `<style>` block from report.html
  - [ ] Verify dark mode renders consistently

- [ ] Task 3: Fix duration card & pin Alpine.js
  <!-- files: src/ainews/api/templates/runs/detail.html, src/ainews/api/templates/base.html, src/ainews/api/templates/login.html -->
  - [ ] Compute `finished_at - started_at` as human-readable duration
  - [ ] Replace `{{ run.finished_at[:19] }}` with computed value
  - [ ] Pin Alpine.js to specific version in base.html and login.html

- [ ] Task 4: Add favicon
  <!-- files: src/ainews/api/static/favicon.svg, src/ainews/api/templates/base.html, src/ainews/api/templates/login.html -->
  - [ ] Create lightning-bolt SVG favicon
  - [ ] Add `<link rel="icon">` to base.html and login.html

- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

**Exit Criteria:** Accent color visible in report card, dark mode consistent, duration shows "Xm Ys", Alpine pinned, favicon in browser tab.

---

## Phase 2: Reusable UI Components
<!-- execution: parallel -->

- [ ] Task 1: Pagination partial
  <!-- files: src/ainews/api/templates/partials/pagination.html -->
  - [ ] Create reusable pagination component accepting `page`, `total_pages`, `base_url`
  - [ ] Support query param preservation
  - [ ] Dark mode styling
  - [ ] HTMX `hx-get` integration with `hx-push-url`

- [ ] Task 2: Breadcrumb partial
  <!-- files: src/ainews/api/templates/partials/breadcrumbs.html, src/ainews/api/templates/base.html -->
  - [ ] Create breadcrumb component accepting `breadcrumbs` context list
  - [ ] Add to base.html main content area (above page content)
  - [ ] Style with muted separators and active item highlight

- [ ] Task 3: Form loading state pattern
  <!-- files: src/ainews/api/static/src/input.css, src/ainews/api/templates/login.html, src/ainews/api/templates/trigger.html, src/ainews/api/templates/llm.html, src/ainews/api/templates/sites/form.html, src/ainews/api/templates/schedules/form.html, src/ainews/api/templates/settings.html -->
  - [ ] Add `btn-loading` CSS utility with spinner animation
  - [ ] Add Alpine.js loading pattern to all form submit buttons
  - [ ] Disable button during submission

- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

**Exit Criteria:** Pagination, breadcrumbs, and loading states render correctly in isolation.

---

## Phase 3: Logs Page Overhaul
<!-- depends: phase2 -->

- [ ] Task 1: Server-side log filtering & pagination backend
  <!-- files: src/ainews/api/routes/views.py -->
  - [ ] Add query params: `level`, `search`, `run_id`, `page`, `per_page`
  - [ ] Build SQLAlchemy query with conditional `.where()` clauses
  - [ ] Compute level counts via `func.count` grouped by level
  - [ ] Return pagination metadata in template context
  - [ ] Write tests for filter combinations

- [ ] Task 2: Logs page template redesign
  <!-- files: src/ainews/api/templates/logs.html, src/ainews/api/templates/partials/logs_table.html -->
  - [ ] Create toolbar with level-filter pills, search input, run-id filter
  - [ ] Extract log entries into `partials/logs_table.html`
  - [ ] Add summary bar showing counts per level
  - [ ] Wire HTMX `hx-get` on filter changes with `hx-push-url`
  - [ ] Add auto-refresh toggle (Alpine + HTMX conditional polling)
  - [ ] Include pagination partial
  - [ ] Dark mode parity

- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

**Exit Criteria:** Logs page filters by level, searches text, paginates, shows summary counts, optional auto-refresh works.

---

## Phase 4: Dashboard Enhancement
<!-- depends: phase1 -->

- [ ] Task 1: SVG sparkline & ring chart helpers
  <!-- files: src/ainews/api/routes/views.py -->
  - [ ] Create `_sparkline_svg(data_points, width, height)` helper returning SVG string
  - [ ] Create `_ring_chart_svg(percentage, size)` helper returning SVG donut
  - [ ] Compute runs-per-day for last 7 days from DB
  - [ ] Pass SVG strings and chart data to dashboard template context

- [ ] Task 2: Dashboard template enhancements
  <!-- files: src/ainews/api/templates/dashboard.html -->
  - [ ] Add health ribbon at top (dot + label, HTMX-refreshed)
  - [ ] Embed sparkline SVG in "Total Runs" card
  - [ ] Embed ring chart SVG in "Success Rate" card
  - [ ] Add "Latest Report" quick-access card
  - [ ] Add personalized greeting with time-of-day context
  - [ ] Dark mode parity

- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)

**Exit Criteria:** Dashboard shows sparkline, ring chart, health ribbon, latest report card, and greeting.

---

## Phase 5: Navigation, Layout & Polish
<!-- execution: parallel -->
<!-- depends: phase2 -->

- [ ] Task 1: Sidebar navigation groups
  <!-- files: src/ainews/api/templates/base.html -->
  - [ ] Group nav items: Overview, Pipeline, System
  - [ ] Add muted uppercase section headers
  - [ ] Alpine.js collapsible groups with localStorage persistence

- [ ] Task 2: Wire pagination into list pages
  <!-- files: src/ainews/api/routes/views.py, src/ainews/api/templates/partials/runs_table.html, src/ainews/api/templates/sites/list.html, src/ainews/api/templates/schedules/list.html -->
  - [ ] Add `page`/`per_page` params to sites, schedules, runs routes
  - [ ] Include pagination partial in each list template
  - [ ] Write tests for pagination boundary cases

- [ ] Task 3: Wire breadcrumbs into sub-pages
  <!-- files: src/ainews/api/routes/views.py, src/ainews/api/templates/sites/form.html, src/ainews/api/templates/schedules/form.html, src/ainews/api/templates/runs/detail.html, src/ainews/api/templates/runs/report.html, src/ainews/api/templates/settings.html, src/ainews/api/templates/llm.html -->
  - [ ] Add `breadcrumbs` list to template context in each route
  - [ ] Include breadcrumb partial in base.html

- [ ] Task 4: Contextual empty states
  <!-- files: src/ainews/api/templates/sites/list.html, src/ainews/api/templates/schedules/list.html, src/ainews/api/templates/partials/runs_table.html, src/ainews/api/templates/logs.html -->
  - [ ] Per-page SVG icons and descriptive guidance copy
  - [ ] Dark mode parity

- [ ] Task 5: Mobile stepper responsiveness
  <!-- files: src/ainews/api/templates/partials/run_stepper.html, src/ainews/api/static/src/input.css -->
  - [ ] Vertical layout on small viewports
  - [ ] Fade-gradient scroll indicators for horizontal overflow
  - [ ] Test on narrow viewport

- [ ] Task 6: Server-side sites search
  <!-- files: src/ainews/api/routes/views.py, src/ainews/api/templates/sites/list.html -->
  - [ ] Replace Alpine `x-show` with HTMX `hx-get` search
  - [ ] Add "showing X of Y" counter
  - [ ] Debounce search input with `hx-trigger="keyup changed delay:300ms"`

- [ ] Task 7: Keyboard shortcuts
  <!-- files: src/ainews/api/templates/base.html -->
  - [ ] Add Alpine.js `@keydown.window` listener for Ctrl/Cmd+K
  - [ ] Focus search input or show command palette stub
  - [ ] Visual hint in sidebar footer

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
