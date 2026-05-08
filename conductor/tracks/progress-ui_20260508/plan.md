# Plan: Pipeline Progress UI

## Phase 1: Backend — Run Logger Service

- [x] Task 1: Create `log_to_db()` helper
  - [x] Create `src/ainews/services/run_logger.py` with `log_to_db(engine, run_id, node, level, message, payload=None)`
  - [x] Uses its own short-lived session via `get_db_session(engine)`
  - [x] Auto-sets `ts` to `datetime.now(UTC).isoformat()`
  - [x] Catches and suppresses DB errors (logging must not crash nodes)

- [x] Task 2: Write unit tests for `log_to_db()`
  - [x] Test: creates RunLog row with correct fields
  - [x] Test: handles missing run_id gracefully (FK constraint)
  - [x] Test: suppresses DB exceptions without raising

- [x] Task 3: Integrate `log_to_db()` into LangGraph nodes
  - [x] Add start/end log calls to all 9 nodes: planner, retriever, scraper, filter, dedup, synthesizer, trender, writer, exporter
  - [x] On node entry: `log_to_db(engine, run_id, node_name, "INFO", "Node started")`
  - [x] On node success: `log_to_db(engine, run_id, node_name, "INFO", "Node completed", payload={summary_metrics})`
  - [x] On node error: `log_to_db(engine, run_id, node_name, "ERROR", "Node failed: {error}")`
  - [x] Pass `engine` through graph config or resolve from Settings inside the task

- [x] Task 4: Write integration test for node logging
  - [x] Test: run a mocked graph invocation and verify RunLog rows are created for each node start/end

- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: HTMX Polling Partials

- [x] Task 1: Create node stepper partial template
  - [x] Create `src/ainews/api/templates/partials/run_stepper.html`
  - [x] 9-stage horizontal pipeline visualization
  - [x] Each stage styled by state: pending (grey), running (pulse animation), completed (green check), failed (red X)
  - [x] Include `hx-get` + `hx-trigger="every 2s"` when run is active; omit trigger when terminal

- [x] Task 2: Create live logs partial template
  - [x] Create `src/ainews/api/templates/partials/run_logs.html`
  - [x] Renders RunLog entries with timestamp, node badge, level badge, message
  - [x] Include `hx-get` + `hx-trigger="every 2s"` when run is active
  - [x] Auto-scrolls to bottom on new entries (Alpine.js `x-init`)

- [x] Task 3: Create runs table partial template
  - [x] Create `src/ainews/api/templates/partials/runs_table.html`
  - [x] Extract the table body from `runs/list.html` into this partial
  - [x] Include `hx-get` + `hx-trigger="every 5s"` when any run is active

- [x] Task 4: Add partial endpoints to views.py
  - [x] `GET /runs/{run_id}/stepper` — returns stepper partial with node states derived from RunLog
  - [x] `GET /runs/{run_id}/logs-partial` — returns logs partial with latest RunLog entries
  - [x] `GET /runs/table` — returns runs table partial

- [x] Task 5: Write tests for partial endpoints
  - [x] Test: stepper partial returns correct node states based on RunLog data
  - [x] Test: logs partial returns RunLog entries ordered by timestamp
  - [x] Test: runs table partial includes polling trigger only when active runs exist
  - [x] Test: all partials require auth

- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: UI Integration & Styling

- [x] Task 1: Redesign run detail page
  - [x] Update `runs/detail.html` to include stepper partial via `hx-get="/runs/{id}/stepper"`
  - [x] Replace static logs section with live logs partial via `hx-get="/runs/{id}/logs-partial"`
  - [x] Add elapsed time display (Alpine.js `x-data` with interval timer while running)
  - [x] Show run metadata (triggered_by, schedule, timestamps) in header cards

- [x] Task 2: Update runs list page
  - [x] Update `runs/list.html` to load table body from the runs table partial
  - [x] Add `hx-get="/runs/table"` with conditional polling

- [x] Task 3: Add CSS for stepper and status animations
  - [x] Node stepper styles: flex layout, connector lines between nodes, state-based colors
  - [x] Pulse animation for "running" state (`@keyframes pulse`)
  - [x] Log level color coding (error=red, warning=amber, info=blue, debug=grey)
  - [x] Responsive: stepper wraps on mobile

- [x] Task 4: End-to-end manual test
  - [x] Trigger a run from admin UI
  - [x] Verify stepper animates through stages
  - [x] Verify logs appear in real-time
  - [x] Verify runs list updates status
  - [x] Verify polling stops on completion

- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
