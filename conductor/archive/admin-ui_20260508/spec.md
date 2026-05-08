# Spec: Admin UI

## Overview

Build the complete admin web interface for the AI News & Trends Report system using Jinja2 server-rendered templates with HTMX for interactivity, Tailwind CSS (standalone CLI) for styling, and Alpine.js for lightweight client-side reactivity. The UI connects to the existing FastAPI API routes (Phase 5) and provides full CRUD management, run monitoring, and system configuration.

## Functional Requirements

### FR-1: Base Layout & Navigation
- Jinja2 base template with sidebar navigation linking all pages
- Responsive layout: collapsible sidebar on mobile, full sidebar on desktop
- Dark mode toggle (Alpine.js + localStorage persistence + Tailwind `dark:` variants)
- Flash message system: cookie-based toasts for success/error/warning with auto-dismiss
- CSRF token injection on all state-changing forms
- HTMX `hx-indicator` loading spinners on all form submissions and data loads

### FR-2: Authentication
- `fastapi-users` integration with JWT stored in HttpOnly cookie
- Login page (`GET/POST /login`)
- `ainews seed-admin` CLI command to create initial admin user
- Protected routes: all pages except `/login` and `/health` require auth
- Logout endpoint clearing the JWT cookie

### FR-3: Dashboard (`GET /`)
- Last 10 runs with status badges (success/failed/running/pending)
- Success rate percentage (last 30 days)
- Next scheduled run (computed from enabled schedules via `croniter`)
- Quick links to latest report (Markdown preview + Excel download)
- System health summary strip (inline from /api/health)

### FR-4: Sites Management (`GET/POST /sites`)
- Table listing all sites: name, URL, category, priority, enabled toggle
- Alpine.js client-side search/filter on name, URL, category
- Server-side pagination (HTMX partial swap, 20 per page)
- Create/Edit form modal: name, URL, category, priority (1-5), crawl_depth, selectors (JSON), js_render (toggle), enabled (toggle)
- Pydantic form validation with inline error display
- Delete with confirmation dialog
- HTMX inline enable/disable toggle (PATCH without full reload)

### FR-5: Schedules Management (`GET/POST /schedules`)
- Table listing: name, cron expression (human-readable via `croniter`), timeframe, topics, enabled
- Create/Edit form: name, cron_expr (with `croniter` validation + "next 3 runs" preview), timeframe_days, topics (tag input), site_filter (multi-select from sites), model_override (optional), enabled
- Delete with confirmation
- "Run Now" button per schedule → `POST /api/trigger`

### FR-6: LLM Settings (`GET/POST /llm`)
- Form fields: base_url, api_key (write-only, masked `••••••` after save), model, temperature (slider 0-2), max_tokens (number), timeout (seconds), extra_headers (JSON textarea)
- **Test Connection** button: HTMX call to `POST /api/llm/test` → displays success/failure inline with latency and model info
- Values stored in `settings_kv` table; read by `llm_factory()` at runtime

### FR-7: Runs List & Detail (`GET /runs`)
- Paginated table: run_id (truncated), schedule name, triggered_by, status badge, started_at, duration, article count
- Click row → detail page (`GET /runs/{id}`)
- Detail page: node-by-node timeline (vertical stepper), per-node token usage, latency, errors
- Input parameters display (topics, sites, timeframe)
- Links to report preview and download

### FR-8: Report Preview & Download
- `GET /runs/{id}/report` → Rendered Markdown preview in-page (using a Markdown-to-HTML converter or Jinja2 filter)
- `GET /runs/{id}/download` → Direct file stream download
- Both accessible from run detail page

### FR-9: Manual Trigger (`POST /trigger`)
- Form: select an existing schedule as template OR specify one-off params (topics, timeframe, site filter)
- Submit enqueues Celery task via existing `POST /api/trigger`
- Redirect to the new run's detail page after enqueue

### FR-10: Live Logs (`GET /logs`)
- SSE endpoint `GET /api/runs/{id}/events` streaming `run_logs` rows via FastAPI `StreamingResponse`
- HTMX `hx-ext="sse"` for real-time log display
- Filter controls: run_id, node, log level (DEBUG/INFO/WARNING/ERROR)
- Auto-scroll to bottom with "pause scroll" toggle
- Color-coded log levels

### FR-11: Settings (`GET /settings`)
- Configurable defaults: retention days, max_total_tokens per run, max_wall_seconds, max_articles
- Stored in `settings_kv` table
- Form with save + flash message confirmation

### FR-12: Health Page (`GET /health`)
- Probe results for: SQLite DB, Valkey connection, Tavily API key validity, LLM endpoint reachability
- Status badges: green (ok), red (error), yellow (degraded)
- Auto-refresh every 30s via HTMX polling

## Non-Functional Requirements

- **NFR-1:** All pages render correctly on Chrome, Firefox, Safari (latest 2 versions)
- **NFR-2:** Mobile-responsive (≥ 375px viewport)
- **NFR-3:** Page load < 200ms for server-rendered pages (no heavy JS bundles)
- **NFR-4:** Tailwind CSS built via standalone CLI — no Node.js dependency
- **NFR-5:** All form inputs validated server-side via Pydantic; client-side validation is UX sugar only
- **NFR-6:** API key fields are write-only (masked after save, never returned in GET responses)

## Acceptance Criteria

1. Admin can log in, see dashboard with recent runs and system health
2. Admin can CRUD sites (add, edit, enable/disable, delete) with validation
3. Admin can CRUD schedules with cron validation and "next runs" preview
4. Admin can edit LLM settings and successfully **Test Connection** against the local LLM
5. Admin can trigger a manual run and watch logs update in real-time via SSE
6. Admin can view run history, click into a run detail, preview the Markdown report, and download the Excel file
7. Dark mode toggle persists across sessions
8. All pages are responsive on mobile viewports
9. Flash messages appear on successful/failed form submissions
10. CSRF protection on all POST/PUT/DELETE forms

## Out of Scope

- Multi-user role-based access (v2)
- Real-time WebSocket-based updates (SSE is sufficient)
- Client-side SPA routing (server-rendered pages with HTMX partials)
- Report editing in the UI
- Internationalization / multi-language support
