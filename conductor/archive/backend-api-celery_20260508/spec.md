# Spec: Phase 5 — Backend API + Celery

## Overview

Implement the FastAPI backend application and Celery task queue integration for the AI News & Trends Report system. This phase creates the HTTP API layer that exposes pipeline triggering, run monitoring, site/schedule management, and health checks — plus the Celery worker infrastructure that executes LangGraph pipeline runs asynchronously. A shared service layer ensures both the API and CLI trigger paths use identical logic without code duplication.

## Functional Requirements

### FR-1: FastAPI Application Shell
- FastAPI app factory (`create_app()`) in `src/ainews/api/main.py` with lifespan handler for DB engine setup/teardown.
- Dependency-injected DB session via `Depends(get_db)`.
- CORS middleware configured for localhost development.
- Exception handlers for structured JSON error responses.
- App mounts all routers under `/api/` prefix.

### FR-2: API Routers (5 endpoint groups)

**`/api/trigger` — Pipeline Triggering**
- `POST /api/trigger` — accepts schedule name or one-off params (topics, sites, timeframe_days), creates a `Run` row in DB with status `pending`, enqueues `run_pipeline` Celery task, returns `{run_id, status}`.
- Request body validated via Pydantic schema (`TriggerRequest`).

**`/api/runs` — Run Monitoring**
- `GET /api/runs` — paginated list of runs with status, timestamps, stats.
- `GET /api/runs/{run_id}` — detailed run info including node-level metrics, error list, status transitions.

**`/api/sites` — Site Management**
- Full CRUD: `GET /api/sites`, `POST /api/sites`, `GET /api/sites/{id}`, `PUT /api/sites/{id}`, `DELETE /api/sites/{id}`.
- Pydantic request/response schemas with validation (URL format, priority range, JSON selectors).

**`/api/schedules` — Schedule Management**
- Full CRUD: `GET /api/schedules`, `POST /api/schedules`, `GET /api/schedules/{id}`, `PUT /api/schedules/{id}`, `DELETE /api/schedules/{id}`.
- Cron expression validation via `croniter`.

**`/api/health` — Health Check**
- `GET /api/health` — probes DB connectivity, Valkey connectivity, returns component-level status with overall `ok`/`degraded`/`down`.

### FR-3: Celery Application & Task
- Celery app in `src/ainews/tasks/celery_app.py` with Valkey as broker and result backend.
- Three declared queues: `default`, `scrape`, `llm` (only `default` used in v1).
- `run_pipeline(run_id: str)` task: loads `Run` row from DB → resolves schedule params → builds LangGraph with `SqliteSaver` checkpointer → invokes graph with `thread_id=run_id` → updates `Run` row with status transitions (`pending` → `running` → `completed`/`failed`) and stats.
- On failure: captures exception, updates `Run.error` and `Run.status = "failed"`, logs structured error.
- Resumability: if a `Run` has `checkpoint_id` and status `failed`, re-invoking with same `thread_id` resumes from last checkpoint.

### FR-4: Shared Service Layer
- `src/ainews/services/pipeline.py` with `create_and_enqueue_run(schedule_name=None, params=None, triggered_by="api")` function.
- Creates `Run` row, enqueues Celery task, returns `run_id`.
- Used by both `POST /api/trigger` route handler and `ainews trigger-run` CLI command.

### FR-5: CLI `trigger-run` Command
- `ainews trigger-run --schedule <name>` — resolves schedule from DB, calls shared service function directly (no HTTP).
- `ainews trigger-run --topics "AI,ML" --days 7` — one-off run with inline params.
- Sets `triggered_by = "cli"` or `"cron"` based on context.

### FR-6: Pydantic Schemas
- Request/response schemas for all endpoints in `src/ainews/schemas/`.
- `TriggerRequest`, `TriggerResponse`, `RunListResponse`, `RunDetailResponse`, `SiteCreate`, `SiteUpdate`, `SiteResponse`, `ScheduleCreate`, `ScheduleUpdate`, `ScheduleResponse`, `HealthResponse`.

## Non-Functional Requirements

- **No authentication in this phase** — deferred to Phase 6. Routes include `# TODO: add auth dependency` comments.
- **API binds to `127.0.0.1:8000`** — no external exposure without nginx.
- **Structured logging** — all API requests and Celery task lifecycle logged via existing `structlog` setup.
- **Test coverage ≥ 80%** — per workflow.md requirement.

## Acceptance Criteria

1. `uvicorn ainews.api.main:app` starts without errors and serves `/api/health` returning `{"status": "ok"}`.
2. `celery -A ainews.tasks.celery_app worker` starts and connects to Valkey.
3. `curl -XPOST localhost:8000/api/trigger -d '{"schedule_name": "weekly-ai-news"}'` creates a `Run` row and returns `{run_id, status: "pending"}`.
4. The Celery worker picks up the task and transitions `Run.status` through `pending → running → completed` (or `failed` with error details).
5. `GET /api/runs/{run_id}` returns the run with current status, timestamps, and metrics.
6. CRUD operations on `/api/sites` and `/api/schedules` work correctly with validation.
7. `ainews trigger-run --schedule weekly-ai-news` enqueues a run identically to the API endpoint.
8. All tests pass with ≥ 80% coverage; `ruff check` and `mypy` clean.

## Out of Scope

- Authentication / authorization (Phase 6)
- Admin UI templates (Phase 6)
- SSE streaming for run logs (Phase 6)
- `reports`, `logs`, `llm`, `settings` routers (Phase 6)
- Multi-queue task routing — sub-tasks on `scrape`/`llm` queues (v2)
