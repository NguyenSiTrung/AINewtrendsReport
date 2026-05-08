# Spec: Admin UI/UX Polish & Enhancement

## Overview

Comprehensive UI/UX improvement pass on the admin web interface based on a
17-item audit covering critical bugs, major gaps, and polish items.  All
changes are additive — no structural backend refactoring, no new Python
dependencies.  The front-end stack remains Jinja2 + HTMX + Alpine.js +
Tailwind v4.

## Functional Requirements

### FR-1  Fix Critical Bugs (P0)
1. Define `--color-accent` in `input.css` `@theme` block (teal/emerald hue for
   report-related UI).
2. Remove the `@media (prefers-color-scheme: dark)` block from `report.html`;
   keep only `.dark` class selectors; move inline styles into `input.css`.
3. Compute real duration (`finished_at − started_at`) on the run detail page
   instead of displaying the raw `finished_at` timestamp.

### FR-2  Redesign Logs Page (P1)
1. Server-side filtering via HTMX: level pills (ERROR / WARNING / INFO /
   DEBUG toggle), free-text search input, run-id filter.
2. HTMX-based pagination (`?page=N&per_page=50`).
3. Summary bar showing counts per level.
4. Optional auto-refresh toggle (HTMX polling every 5 s).
5. Extract logs table into a partial for independent refresh.

### FR-3  Add Pagination to All List Pages (P1)
1. Reusable `partials/pagination.html` component.
2. Wire pagination into runs, sites, and schedules list views.
3. Preserve query params across page navigation.

### FR-4  Enhance Dashboard (P1)
1. Inline SVG sparkline on the "Total Runs" card (runs-per-day, last 7 days).
2. SVG ring chart on the "Success Rate" card.
3. Compact system health ribbon (green/yellow/red dot + label) at top.
4. "Latest Report" quick-access card when a completed run with report exists.
5. Personalized greeting ("Good evening, admin@…").

### FR-5  Add Breadcrumbs (P2)
1. Reusable breadcrumb partial driven by a `breadcrumbs` context list.
2. Wire into all sub-pages (forms, detail views, report).

### FR-6  Group Sidebar Navigation (P2)
1. Three groups: Overview, Pipeline, System — with muted uppercase headers.
2. Collapsible groups persisted via `localStorage`.

### FR-7  Form Loading States (P2)
1. Alpine.js `x-data` spinner pattern on all submit buttons.
2. Disable button + swap label to spinner on submit.

### FR-8  Complete Surface Palette (P2)
1. Add `surface-300` through `surface-600` steps in `input.css`.

### FR-9  Pin Alpine.js CDN Version (P2)
1. Replace `@3.x.x` with a pinned version in `base.html` and `login.html`.

### FR-10  Contextual Empty States (P3)
1. Per-page illustrations (SVG icons) and descriptive copy for sites,
   schedules, runs, and logs empty states.

### FR-11  Mobile Stepper Responsiveness (P3)
1. Vertical layout on `sm:` breakpoint, horizontal on `lg:+`.
2. Fade-gradient scroll indicators when horizontal.

### FR-12  Server-Side Sites Search (P3)
1. Replace Alpine.js `x-show` filter with HTMX `hx-get` search.
2. Add "showing X of Y" counter.

### FR-13  Add Favicon (P3)
1. Generate a ⚡ lightning-bolt SVG favicon.
2. Add `<link rel="icon">` to `base.html` and `login.html`.

### FR-14  Keyboard Shortcuts (P3)
1. `Ctrl/Cmd+K` → focus search / command palette stub.
2. `n` → new (context-dependent).

## Non-Functional Requirements

- No new Python dependencies.
- No Node.js toolchain.  Tailwind v4 standalone CLI only.
- All changes must pass `ruff check . && ruff format --check . && mypy src/`.
- Existing tests must remain green.
- Dark mode parity for every change.

## Acceptance Criteria

- [ ] All 3 P0 bugs verified fixed (accent color renders, report dark mode
      consistent, duration shows human-readable format).
- [ ] Logs page has working level filter, search, pagination, summary bar.
- [ ] Pagination works on runs, sites, schedules lists.
- [ ] Dashboard displays SVG sparkline and ring chart with real data.
- [ ] Breadcrumbs visible on all sub-pages.
- [ ] Sidebar groups render with headers.
- [ ] All form buttons show spinner on submit.
- [ ] Surface palette has full 50–950 steps.
- [ ] Alpine.js version pinned.
- [ ] Contextual empty states with per-page copy.
- [ ] Stepper is usable on mobile viewports.
- [ ] Sites search is server-side.
- [ ] Favicon visible in browser tab.
- [ ] Lints + existing tests pass.

## Out of Scope

- Backend structural refactoring.
- New Python dependencies.
- Full command palette implementation (only stub for keyboard shortcut).
- Chart.js or other JS charting libraries.
- Embedding-based log search.
