# Spec: Pipeline Progress UI

## Overview

Add real-time pipeline progress visibility to the admin web interface so the
admin can monitor running pipelines (triggered manually or via cron) without
refreshing the page. The feature uses HTMX polling against existing RunLog
data, enhanced with a `log_to_db()` helper that each LangGraph node calls
at entry and exit.

## Functional Requirements

### FR-1: Node Progress Stepper (Run Detail Page)
- Display a horizontal pipeline visualization at the top of `/runs/{run_id}`
  showing all 9 stages: Planner → Retriever → Scraper → Filter → Dedup →
  Synthesizer → Trender → Writer → Exporter.
- Each stage derives its state from RunLog entries for that run:
  - **Pending** (grey) — no RunLog with this node name yet
  - **Running** (animated pulse, accent color) — has a "started" log but no
    "completed" log
  - **Completed** (green checkmark) — has a "completed" log
  - **Failed** (red X) — has an "error"-level log
- The stepper is an HTMX partial that polls every 2 seconds while the run
  status is `pending` or `running`. Polling stops when the run reaches a
  terminal state (`completed` / `failed`).

### FR-2: Live Log Stream (Run Detail Page)
- The existing log panel on the run detail page auto-updates via HTMX polling
  every 2 seconds.
- New RunLog entries appear at the bottom.
- Each log line shows: timestamp, node name, level badge, message.
- Polling stops automatically when the run reaches a terminal state.

### FR-3: Auto-Refresh Runs List
- The runs list table at `/runs` auto-refreshes via HTMX polling every 5
  seconds when any run is in `pending` or `running` status.
- Status badges update live (e.g., `pending → running → completed`).
- Polling stops when all visible runs are in terminal states.

### FR-4: `log_to_db()` Helper
- New function `ainews.services.run_logger.log_to_db(engine, run_id, node,
  level, message, payload=None)` that creates a RunLog row.
- Each LangGraph node calls this at entry ("Node started") and exit
  ("Node completed" or "Node failed").
- The helper uses its own short-lived DB session (independent of the graph
  state) to ensure logs persist even if a node fails.

### FR-5: Run Detail Header Enhancement
- Show elapsed time (live-updating while running).
- Show triggered_by and schedule info.
- Terminal state shows total duration.

## Non-Functional Requirements

- **No new dependencies** — uses HTMX polling (already in stack), no SSE or
  WebSocket infrastructure.
- **SQLite-safe** — short-lived read sessions for polling; no long-held
  connections.
- **Graceful degradation** — if JavaScript is disabled, the page still works
  as a static snapshot (current behavior).
- **Performance** — polling partials return minimal HTML fragments, not full
  pages. DB queries are indexed on `run_id`.

## Acceptance Criteria

1. Admin triggers a manual run → navigates to run detail → sees node stepper
   animate through stages in real time without page refresh.
2. Log entries appear in the live log panel within ~2 seconds of being written.
3. Runs list page shows status transitions live without manual refresh.
4. When a run completes or fails, all polling stops automatically.
5. Each LangGraph node (all 9) writes start/end RunLog entries via
   `log_to_db()`.
6. Unit tests for `log_to_db()`, the polling partials, and the stepper state
   derivation logic.

## Out of Scope

- SSE or WebSocket implementation (HTMX polling is sufficient for single-admin).
- Live metrics counters (tokens, articles) — can be layered on later.
- Progress percentage bar (misleading with unequal node durations).
- Dashboard page live updates (only runs list and run detail).
