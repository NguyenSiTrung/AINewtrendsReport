# Plan: Admin UI

## Phase 1: Foundation & Base Layout

- [x] Task 1: Install Tailwind CSS standalone CLI and configure build
  - [x] Download tailwindcss standalone binary to `tools/tailwindcss`
  - [x] Create `src/ainews/api/static/src/input.css` with Tailwind directives (@tailwind base/components/utilities)
  - [x] Create `tailwind.config.js` with template paths, dark mode 'class', custom color palette
  - [x] Add `make css` and `make css-watch` targets to Makefile
  - [x] Build initial `output.css` to `src/ainews/api/static/css/output.css`

- [x] Task 2: Configure Jinja2 templating and static file serving in FastAPI
  - [x] Add `Jinja2Templates` setup in `src/ainews/api/main.py`
  - [x] Mount `/static` directory via `StaticFiles`
  - [x] Add template globals (app_name, version, current_year)
  - [x] Create `src/ainews/api/templates/` directory structure

- [x] Task 3: Create base layout template with navigation
  - [x] `templates/base.html`: HTML5 skeleton, Tailwind CSS link, Alpine.js CDN, HTMX CDN
  - [x] Responsive sidebar navigation (collapsible on mobile via Alpine.js `x-data`)
  - [x] Dark mode toggle with localStorage persistence
  - [x] Flash message partial (`templates/partials/flash.html`) with auto-dismiss
  - [x] HTMX `hx-indicator` loading spinner partial
  - [x] CSRF meta tag injection

- [x] Task 4: Add CSRF protection middleware
  - [x] Create `src/ainews/api/middleware/csrf.py`: generate + validate CSRF tokens
  - [x] Token stored in signed cookie, injected as hidden field in all forms
  - [x] Validate on POST/PUT/DELETE requests to non-API routes

- [x] Task 5: Write tests for foundation
  - [x] Test static file serving (GET /static/css/output.css returns 200)
  - [x] Test Jinja2 template rendering with base layout
  - [x] Test CSRF token generation and validation
  - [x] Test flash message cookie set/clear cycle

- [x] Task: Conductor - User Manual Verification 'Foundation & Base Layout' (Protocol in workflow.md)

## Phase 2: Authentication System

- [x] Task 1: Implement JWT auth with bcrypt
  - [x] Add `pyjwt` and `bcrypt` to pyproject.toml dependencies
  - [x] Create `src/ainews/api/auth.py`: password hashing, JWT creation/validation, user auth
  - [x] Configure HttpOnly cookie transport with CSRF protection
  - [x] Create login/logout routes

- [x] Task 2: Create login page template
  - [x] `templates/login.html`: email + password form, error display, redirect after login
  - [x] Styled with Tailwind, centered card layout

- [x] Task 3: Add `seed-admin` CLI command
  - [x] Add `ainews seed admin --email --password` command in cli.py
  - [x] Creates user with admin role; skips if already exists

- [x] Task 4: Add auth dependency to all page routes
  - [x] Create `_require_auth` + `_get_current_user` helpers
  - [x] Apply to all view routes (except /login, /health API)
  - [x] Redirect unauthenticated users to /login

- [x] Task 5: Write tests for auth
  - [x] Test login flow (valid/invalid credentials)
  - [x] Test JWT cookie set/clear
  - [x] Test protected route redirect
  - [x] Test seed-admin CLI command

## Phase 3: Dashboard & Health Pages

- [x] Task 1: Build dashboard page with real data
  - [x] `templates/dashboard.html`: extends base.html
  - [x] Summary cards: total runs, success rate, active sites, schedule count
  - [x] Last 10 runs table with status badges (green=success, red=failed, blue=running, gray=pending)
  - [x] Empty state with CTA to trigger first run

- [x] Task 2: Build health page
  - [x] `templates/health.html`: probe results for DB, Valkey
  - [x] `templates/partials/health_grid.html`: HTMX partial
  - [x] Status badges: green/red/yellow
  - [x] Auto-refresh every 30s via `hx-trigger="every 30s"` on container

- [x] Task 3: Write tests for dashboard and health pages
  - [x] Test dashboard renders with run data
  - [x] Test dashboard shows correct success rate
  - [x] Test health page displays component statuses
  - [x] Test health auto-refresh returns HTMX partial

## Phase 4: Sites & Schedules CRUD Pages

- [x] Task 1: Build sites list and form pages
  - [x] `templates/sites/list.html`: table with URL, category, priority, enabled toggle
  - [x] Alpine.js client-side search/filter
  - [x] `templates/sites/form.html`: create/edit form
  - [x] Delete with HTMX confirmation

- [x] Task 2: Add view routes for sites
  - [x] GET/POST /sites/new → create + redirect with flash
  - [x] GET /sites/{id}/edit → render pre-filled form
  - [x] POST /sites/{id} → update + redirect with flash

- [x] Task 3: Build schedules list and form pages
  - [x] `templates/schedules/list.html`: table with name, cron, timeframe, enabled
  - [x] `templates/schedules/form.html`: create/edit with cron, timeframe

- [x] Task 4: Add view routes for schedules
  - [x] CRUD view routes mirroring sites pattern

- [x] Task 5: Write tests for sites and schedules pages
  - [x] Test CRUD flows (create, read, update) for sites
  - [x] Test CRUD flows for schedules
  - [x] Test auth gating

## Phase 5: LLM Settings & Trigger Pages

- [x] Task 1: Build LLM settings page
  - [x] `templates/llm.html`: form fields for base_url, api_key, model, temperature, max_tokens
  - [x] API key preservation: existing key kept if field submitted empty

- [x] Task 2: Add LLM settings view routes
  - [x] GET /llm → render settings form with current values from settings_kv
  - [x] POST /llm → save to settings_kv + redirect with flash

- [x] Task 3: Build manual trigger page
  - [x] `templates/trigger.html`: select schedule or fill one-off params (topics, timeframe)
  - [x] Submit creates run and redirects to runs list

- [x] Task 4: Write tests for LLM settings and trigger
  - [x] Test LLM settings read/write cycle
  - [x] Test API key preservation
  - [x] Test trigger form rendering

## Phase 6: Runs & Logs Pages

- [x] Task 1: Build runs list page
  - [x] `templates/runs/list.html`: table with run_id, status badge, triggered_by, schedule, created
  - [x] Empty state with CTA

- [x] Task 2: Build run detail page
  - [x] `templates/runs/detail.html`: metadata cards + log viewer
  - [x] Color-coded log levels
  - [x] Not found handling

- [x] Task 3: Build logs page
  - [x] `templates/logs.html`: system-wide log with level coloring
  - [x] Last 200 entries

- [x] Task 4: Write tests for runs and logs
  - [x] Test runs list renders
  - [x] Test run detail with logs
  - [x] Test run not found redirect
  - [x] Test logs page with data

## Phase 7: Settings Page

- [x] Task 1: Build settings page
  - [x] `templates/settings.html`: system info + seed action
  - [x] POST /settings/seed triggers seed_all

- [x] Task 2: Write tests
  - [x] Test settings page renders
  - [x] Test seed action
