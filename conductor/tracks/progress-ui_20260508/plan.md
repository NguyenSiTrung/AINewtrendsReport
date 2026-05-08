# Plan: Pipeline Progress UI

## Phase 1: Backend — Run Logger Service

- [ ] Task 1: Create `log_to_db()` helper
  - [ ] Create `src/ainews/services/run_logger.py` with `log_to_db(engine, run_id, node, level, message, payload=None)`
  - [ ] Uses its own short-lived session via `get_db_session(engine)`
  - [ ] Auto-sets `ts` to `datetime.now(UTC).isoformat()`
  - [ ] Catches and suppresses DB errors (logging must not crash nodes)

- [ ] Task 2: Write unit tests for `log_to_db()`
  - [ ] Test: creates RunLog row with correct fields
  - [ ] Test: handles missing run_id gracefully (FK constraint)
  - [ ] Test: suppresses DB exceptions without raising

- [ ] Task 3: Integrate `log_to_db()` into LangGraph nodes
  - [ ] Add start/end log calls to all 9 nodes: planner, retriever, scraper, filter, dedup, synthesizer, trender, writer, exporter
  - [ ] On node entry: `log_to_db(engine, run_id, node_name, "INFO", "Node started")`
  - [ ] On node success: `log_to_db(engine, run_id, node_name, "INFO", "Node completed", payload={summary_metrics})`
  - [ ] On node error: `log_to_db(engine, run_id, node_name, "ERROR", "Node failed: {error}")`
  - [ ] Pass `engine` through graph config or resolve from Settings inside the task

- [ ] Task 4: Write integration test for node logging
  - [ ] Test: run a mocked graph invocation and verify RunLog rows are created for each node start/end

- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: HTMX Polling Partials

- [ ] Task 1: Create node stepper partial template
  - [ ] Create `src/ainews/api/templates/partials/run_stepper.html`
  - [ ] 9-stage horizontal pipeline visualization
  - [ ] Each stage styled by state: pending (grey), running (pulse animation), completed (green check), failed (red X)
  - [ ] Include `hx-get` + `hx-trigger="every 2s"` when run is active; omit trigger when terminal

- [ ] Task 2: Create live logs partial template
  - [ ] Create `src/ainews/api/templates/partials/run_logs.html`
  - [ ] Renders RunLog entries with timestamp, node badge, level badge, message
  - [ ] Include `hx-get` + `hx-trigger="every 2s"` when run is active
  - [ ] Auto-scrolls to bottom on new entries (Alpine.js `x-init`)

- [ ] Task 3: Create runs table partial template
  - [ ] Create `src/ainews/api/templates/partials/runs_table.html`
  - [ ] Extract the table body from `runs/list.html` into this partial
  - [ ] Include `hx-get` + `hx-trigger="every 5s"` when any run is active

- [ ] Task 4: Add partial endpoints to views.py
  - [ ] `GET /runs/{run_id}/stepper` — returns stepper partial with node states derived from RunLog
  - [ ] `GET /runs/{run_id}/logs-partial` — returns logs partial with latest RunLog entries
  - [ ] `GET /runs/table` — returns runs table partial

- [ ] Task 5: Write tests for partial endpoints
  - [ ] Test: stepper partial returns correct node states based on RunLog data
  - [ ] Test: logs partial returns RunLog entries ordered by timestamp
  - [ ] Test: runs table partial includes polling trigger only when active runs exist
  - [ ] Test: all partials require auth

- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: UI Integration & Styling

- [ ] Task 1: Redesign run detail page
  - [ ] Update `runs/detail.html` to include stepper partial via `hx-get="/runs/{id}/stepper"`
  - [ ] Replace static logs section with live logs partial via `hx-get="/runs/{id}/logs-partial"`
  - [ ] Add elapsed time display (Alpine.js `x-data` with interval timer while running)
  - [ ] Show run metadata (triggered_by, schedule, timestamps) in header cards

- [ ] Task 2: Update runs list page
  - [ ] Update `runs/list.html` to load table body from the runs table partial
  - [ ] Add `hx-get="/runs/table"` with conditional polling

- [ ] Task 3: Add CSS for stepper and status animations
  - [ ] Node stepper styles: flex layout, connector lines between nodes, state-based colors
  - [ ] Pulse animation for "running" state (`@keyframes pulse`)
  - [ ] Log level color coding (error=red, warning=amber, info=blue, debug=grey)
  - [ ] Responsive: stepper wraps on mobile

- [ ] Task 4: End-to-end manual test
  - [ ] Trigger a run from admin UI
  - [ ] Verify stepper animates through stages
  - [ ] Verify logs appear in real-time
  - [ ] Verify runs list updates status
  - [ ] Verify polling stops on completion

- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)
