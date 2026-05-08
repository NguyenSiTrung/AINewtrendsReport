# Plan: Admin UI

## Phase 1: Foundation & Base Layout

- [ ] Task 1: Install Tailwind CSS standalone CLI and configure build
  - [ ] Download tailwindcss standalone binary to `tools/tailwindcss`
  - [ ] Create `src/ainews/api/static/src/input.css` with Tailwind directives (@tailwind base/components/utilities)
  - [ ] Create `tailwind.config.js` with template paths, dark mode 'class', custom color palette
  - [ ] Add `make css` and `make css-watch` targets to Makefile
  - [ ] Build initial `output.css` to `src/ainews/api/static/css/output.css`

- [ ] Task 2: Configure Jinja2 templating and static file serving in FastAPI
  - [ ] Add `Jinja2Templates` setup in `src/ainews/api/main.py`
  - [ ] Mount `/static` directory via `StaticFiles`
  - [ ] Add template globals (app_name, version, current_year)
  - [ ] Create `src/ainews/api/templates/` directory structure

- [ ] Task 3: Create base layout template with navigation
  - [ ] `templates/base.html`: HTML5 skeleton, Tailwind CSS link, Alpine.js CDN, HTMX CDN
  - [ ] Responsive sidebar navigation (collapsible on mobile via Alpine.js `x-data`)
  - [ ] Dark mode toggle with localStorage persistence
  - [ ] Flash message partial (`templates/partials/flash.html`) with auto-dismiss
  - [ ] HTMX `hx-indicator` loading spinner partial
  - [ ] CSRF meta tag injection

- [ ] Task 4: Add CSRF protection middleware
  - [ ] Create `src/ainews/api/middleware/csrf.py`: generate + validate CSRF tokens
  - [ ] Token stored in signed cookie, injected as hidden field in all forms
  - [ ] Validate on POST/PUT/DELETE requests to non-API routes

- [ ] Task 5: Write tests for foundation
  - [ ] Test static file serving (GET /static/css/output.css returns 200)
  - [ ] Test Jinja2 template rendering with base layout
  - [ ] Test CSRF token generation and validation
  - [ ] Test flash message cookie set/clear cycle

- [ ] Task: Conductor - User Manual Verification 'Foundation & Base Layout' (Protocol in workflow.md)

## Phase 2: Authentication System

- [ ] Task 1: Integrate fastapi-users for JWT auth
  - [ ] Add `fastapi-users[sqlalchemy]` to pyproject.toml dependencies
  - [ ] Create `src/ainews/api/auth.py`: UserManager, auth backend (JWT cookie), user schema
  - [ ] Configure HttpOnly cookie transport with CSRF protection
  - [ ] Create login/logout routes

- [ ] Task 2: Create login page template
  - [ ] `templates/login.html`: email + password form, error display, redirect after login
  - [ ] Styled with Tailwind, centered card layout

- [ ] Task 3: Add `seed-admin` CLI command
  - [ ] Add `ainews seed admin --email --password` command in cli.py
  - [ ] Creates user with admin role; skips if already exists

- [ ] Task 4: Add auth dependency to all page routes
  - [ ] Create `get_current_user` dependency
  - [ ] Apply to all view routes (except /login, /health API)
  - [ ] Redirect unauthenticated users to /login

- [ ] Task 5: Write tests for auth
  - [ ] Test login flow (valid/invalid credentials)
  - [ ] Test JWT cookie set/clear
  - [ ] Test protected route redirect
  - [ ] Test seed-admin CLI command

- [ ] Task: Conductor - User Manual Verification 'Authentication System' (Protocol in workflow.md)

## Phase 3: Dashboard & Health Pages

- [ ] Task 1: Create page view router
  - [ ] Create `src/ainews/api/routes/views.py` for HTML page routes (separate from API JSON routes)
  - [ ] Register with app, prefix="" (root-level HTML pages)

- [ ] Task 2: Build dashboard page
  - [ ] `templates/dashboard.html`: extends base.html
  - [ ] Last 10 runs table with status badges (colored: green=success, red=failed, blue=running, gray=pending)
  - [ ] Success rate card (last 30 days, computed from runs table)
  - [ ] Next scheduled run card (croniter on enabled schedules)
  - [ ] Latest report quick-links (Markdown preview + Excel download)
  - [ ] System health summary strip (inline from /api/health)

- [ ] Task 3: Build health page
  - [ ] `templates/health.html`: probe results for DB, Valkey, Tavily, LLM
  - [ ] Status badges: green/red/yellow
  - [ ] Auto-refresh every 30s via `hx-trigger="every 30s"` on container
  - [ ] Add Tavily + LLM probes to existing health router

- [ ] Task 4: Write tests for dashboard and health pages
  - [ ] Test dashboard renders with run data
  - [ ] Test dashboard shows correct success rate
  - [ ] Test health page displays component statuses
  - [ ] Test health auto-refresh returns HTMX partial

- [ ] Task: Conductor - User Manual Verification 'Dashboard & Health Pages' (Protocol in workflow.md)

## Phase 4: Sites & Schedules CRUD Pages

- [ ] Task 1: Build sites list and form pages
  - [ ] `templates/sites/list.html`: table with name, URL, category, priority, enabled toggle
  - [ ] Alpine.js client-side search/filter (`x-model` on search input, `x-show` on rows)
  - [ ] Server-side pagination with HTMX (`hx-get="/sites?page=2"`, `hx-target="#site-table"`)
  - [ ] `templates/sites/form.html`: create/edit form (modal or separate page)
  - [ ] Inline enable/disable toggle via HTMX PATCH
  - [ ] Delete with Alpine.js confirmation dialog

- [ ] Task 2: Add view routes for sites
  - [ ] `GET /sites` → render sites list template
  - [ ] `GET /sites/new` → render empty form
  - [ ] `GET /sites/{id}/edit` → render pre-filled form
  - [ ] `POST /sites` → validate + create + redirect with flash
  - [ ] `POST /sites/{id}` → validate + update + redirect with flash
  - [ ] `POST /sites/{id}/delete` → delete + redirect with flash
  - [ ] `PATCH /sites/{id}/toggle` → HTMX partial response for enable/disable

- [ ] Task 3: Build schedules list and form pages
  - [ ] `templates/schedules/list.html`: table with name, cron (human-readable), timeframe, topics, enabled
  - [ ] `templates/schedules/form.html`: create/edit with cron validation + "next 3 runs" preview
  - [ ] "Run Now" button per schedule (HTMX POST to /api/trigger)
  - [ ] Client-side search/filter, pagination, delete with confirmation

- [ ] Task 4: Add view routes for schedules
  - [ ] CRUD view routes mirroring sites pattern
  - [ ] Cron validation endpoint for live "next 3 runs" preview via HTMX

- [ ] Task 5: Write tests for sites and schedules pages
  - [ ] Test CRUD flows (create, read, update, delete) for sites
  - [ ] Test CRUD flows for schedules
  - [ ] Test pagination parameters
  - [ ] Test inline toggle responds with HTMX partial
  - [ ] Test cron validation preview endpoint
  - [ ] Test form validation errors display correctly

- [ ] Task: Conductor - User Manual Verification 'Sites & Schedules CRUD Pages' (Protocol in workflow.md)

## Phase 5: LLM Settings & Trigger Pages

- [ ] Task 1: Build LLM settings page
  - [ ] `templates/llm.html`: form fields for base_url, api_key (masked), model, temperature (slider), max_tokens, timeout, extra_headers (JSON textarea)
  - [ ] Add `GET/POST /api/llm/settings` endpoints (read/write settings_kv)
  - [ ] API key field: write-only, display masked `••••••` after save
  - [ ] "Test Connection" button: HTMX POST to `/api/llm/test`, inline result display

- [ ] Task 2: Add LLM settings view routes
  - [ ] `GET /llm` → render settings form with current values from settings_kv
  - [ ] `POST /llm` → validate + save to settings_kv + redirect with flash
  - [ ] `POST /llm/test` → HTMX partial: success/failure + latency + model info

- [ ] Task 3: Build manual trigger page
  - [ ] `templates/trigger.html`: select existing schedule OR fill one-off params (topics, timeframe, site filter)
  - [ ] Submit enqueues via existing POST /api/trigger
  - [ ] Redirect to new run detail page after enqueue
  - [ ] Schedule selector populated from DB

- [ ] Task 4: Write tests for LLM settings and trigger
  - [ ] Test LLM settings read/write cycle
  - [ ] Test API key masking (never returned in GET)
  - [ ] Test connection test endpoint
  - [ ] Test trigger form submission creates run

- [ ] Task: Conductor - User Manual Verification 'LLM Settings & Trigger Pages' (Protocol in workflow.md)

## Phase 6: Runs, Reports & Live Logs

- [ ] Task 1: Build runs list page
  - [ ] `templates/runs/list.html`: paginated table with run_id (truncated), schedule, triggered_by, status badge, started_at, duration, article count
  - [ ] HTMX pagination, status filter dropdown
  - [ ] Click row → navigate to run detail

- [ ] Task 2: Build run detail page
  - [ ] `templates/runs/detail.html`: node-by-node vertical timeline/stepper
  - [ ] Per-node metrics: token usage, latency, errors
  - [ ] Input parameters display (topics, sites, timeframe)
  - [ ] Links to report preview and Excel download

- [ ] Task 3: Build report preview and download
  - [ ] `GET /runs/{id}/report` → render Markdown as HTML (using `markdown` library or Jinja2 filter)
  - [ ] `GET /runs/{id}/download` → stream .xlsx file via FileResponse
  - [ ] Accessible from run detail page

- [ ] Task 4: Build live logs page with SSE
  - [ ] Create SSE endpoint: `GET /api/runs/{id}/events` → FastAPI StreamingResponse polling run_logs table
  - [ ] `templates/logs.html`: log display with HTMX `hx-ext="sse"`, `sse-connect`
  - [ ] Filter controls: run_id selector, node filter, log level filter
  - [ ] Auto-scroll to bottom with "pause scroll" toggle (Alpine.js)
  - [ ] Color-coded log levels (ERROR=red, WARNING=yellow, INFO=blue, DEBUG=gray)

- [ ] Task 5: Write tests for runs, reports, and logs
  - [ ] Test runs list pagination and filtering
  - [ ] Test run detail page renders timeline
  - [ ] Test report Markdown preview renders HTML
  - [ ] Test Excel download returns valid file
  - [ ] Test SSE endpoint streams log events

- [ ] Task: Conductor - User Manual Verification 'Runs, Reports & Live Logs' (Protocol in workflow.md)

## Phase 7: Settings Page & Final Polish

- [ ] Task 1: Build settings page
  - [ ] `templates/settings.html`: form for retention_days, max_total_tokens, max_wall_seconds, max_articles
  - [ ] Read/write from settings_kv table
  - [ ] Save with flash confirmation

- [ ] Task 2: Add settings view routes and API
  - [ ] `GET /settings` → render settings form
  - [ ] `POST /settings` → validate + save + flash
  - [ ] `GET/PUT /api/settings` endpoints for settings_kv CRUD

- [ ] Task 3: UI polish and consistency pass
  - [ ] Verify dark mode works on all pages
  - [ ] Verify responsive layout on all pages (mobile 375px+)
  - [ ] Verify flash messages on all form submissions
  - [ ] Verify loading indicators on all HTMX requests
  - [ ] Check all navigation links are active-state highlighted
  - [ ] Ensure consistent table styling, button styling, form styling across pages

- [ ] Task 4: Final integration tests
  - [ ] E2E: login → dashboard → add site → edit LLM settings → test connection → trigger run → view logs
  - [ ] Test all pages render without errors
  - [ ] Test CSRF protection on all POST forms
  - [ ] Verify auth redirect on all protected pages
  - [ ] Run `make lint && make typecheck && make test` — all green

- [ ] Task: Conductor - User Manual Verification 'Settings Page & Final Polish' (Protocol in workflow.md)
