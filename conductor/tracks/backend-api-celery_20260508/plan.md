# Plan: Phase 5 — Backend API + Celery

## Phase 1: Pydantic Schemas
<!-- execution: sequential -->
<!-- depends: -->

- [x] Task 1: Create API request/response schemas <!-- 4078a88 -->
  - [x] `TriggerRequest` and `TriggerResponse` in `src/ainews/schemas/trigger.py`
  - [x] `RunListResponse`, `RunDetailResponse` in `src/ainews/schemas/run.py`
  - [x] `SiteCreate`, `SiteUpdate`, `SiteResponse` in `src/ainews/schemas/site.py`
  - [x] `ScheduleCreate`, `ScheduleUpdate`, `ScheduleResponse` in `src/ainews/schemas/schedule.py`
  - [x] `HealthResponse` with component-level status in `src/ainews/schemas/health.py`
  - [x] Tests for schema validation (required fields, cron format, URL format)

- [x] Task: Conductor - User Manual Verification 'Pydantic Schemas' (Protocol in workflow.md)

## Phase 2: Celery Infrastructure
<!-- execution: sequential -->
<!-- depends: -->

- [x] Task 1: Celery app configuration <!-- 4078a88 -->
  - [x] `src/ainews/tasks/celery_app.py` — Celery instance with Valkey broker URL from `Settings`
  - [x] Declare three queues: `default`, `scrape`, `llm`
  - [x] Serialization config (JSON), task result backend (Valkey)
  - [x] Tests for app instantiation and config resolution

- [x] Task 2: `run_pipeline` task implementation <!-- 4078a88 -->
  - [x] Task function in `src/ainews/tasks/pipeline.py`
  - [x] Load `Run` row from DB, update status `pending → running`
  - [x] Resolve schedule params (sites, topics, timeframe) from DB
  - [x] Build LangGraph with `SqliteSaver` checkpointer, invoke with `thread_id=run_id`
  - [x] On success: update `Run.status = "completed"`, populate `stats` and `finished_at`
  - [x] On failure: update `Run.status = "failed"`, populate `error` field
  - [x] Resumability: detect existing `checkpoint_id`, resume from last checkpoint
  - [x] Tests with mocked graph invocation

- [x] Task: Conductor - User Manual Verification 'Celery Infrastructure' (Protocol in workflow.md)

## Phase 3: Service Layer
<!-- execution: sequential -->
<!-- depends: phase1, phase2 -->

- [x] Task 1: Pipeline service <!-- 9656449 -->
  - [x] `src/ainews/services/pipeline.py` with `create_and_enqueue_run()`
  - [x] Accepts `schedule_name` (resolve from DB) or inline `params` (topics, sites, timeframe_days)
  - [x] Creates `Run` row with `status="pending"`, `triggered_by` field
  - [x] Calls `run_pipeline.delay(run_id)` to enqueue
  - [x] Returns `run_id` for caller
  - [x] Tests with mocked DB session and Celery task

- [x] Task: Conductor - User Manual Verification 'Service Layer' (Protocol in workflow.md)

## Phase 4: FastAPI Application & Routers
<!-- execution: sequential -->
<!-- depends: phase3 -->

- [x] Task 1: App factory and dependencies <!-- 9656449 -->
  - [x] `src/ainews/api/main.py` — `create_app()` with lifespan handler (engine init/dispose)
  - [x] `src/ainews/api/deps.py` — `get_db` dependency yielding SQLAlchemy sessions
  - [x] CORS middleware for localhost
  - [x] Global exception handlers (validation errors → 422, DB errors → 500)
  - [x] Tests for app startup/shutdown lifecycle

- [x] Task 2: Health router <!-- 9656449 -->
  - [x] `src/ainews/api/routes/health.py` — `GET /api/health`
  - [x] Probes: SQLite DB connectivity, Valkey ping
  - [x] Returns `{status, components: {db: ok/down, valkey: ok/down}}`
  - [x] Tests with healthy and degraded scenarios

- [x] Task 3: Trigger router <!-- 9656449 -->
  - [x] `src/ainews/api/routes/trigger.py` — `POST /api/trigger`
  - [x] Calls shared service `create_and_enqueue_run()`
  - [x] Returns `{run_id, status: "pending"}`
  - [x] Validates schedule exists (if `schedule_name` provided)
  - [x] Tests with mocked service layer

- [x] Task 4: Runs router <!-- 9656449 -->
  - [x] `src/ainews/api/routes/runs.py`
  - [x] `GET /api/runs` — paginated list (offset/limit), filterable by status
  - [x] `GET /api/runs/{run_id}` — detail with metrics, errors, timestamps
  - [x] 404 handling for unknown run_id
  - [x] Tests with seeded run data

- [x] Task 5: Sites CRUD router <!-- 9656449 -->
  - [x] `src/ainews/api/routes/sites.py`
  - [x] `GET`, `POST`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
  - [x] Pydantic validation on create/update
  - [x] Unique URL constraint handling (409 on duplicate)
  - [x] Tests for full CRUD lifecycle

- [x] Task 6: Schedules CRUD router <!-- 9656449 -->
  - [x] `src/ainews/api/routes/schedules.py`
  - [x] `GET`, `POST`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
  - [x] Cron expression validation via `croniter`
  - [x] Tests for full CRUD lifecycle

- [x] Task: Conductor - User Manual Verification 'FastAPI Application & Routers' (Protocol in workflow.md)

## Phase 5: CLI Integration
<!-- execution: sequential -->
<!-- depends: phase3 -->

- [x] Task 1: Update `trigger-run` CLI command <!-- 9656449 -->
  - [x] Implement `ainews trigger-run --schedule <name>` using shared service
  - [x] Implement `ainews trigger-run --topics "AI,ML" --days 7` for one-off runs
  - [x] Set `triggered_by = "cli"`
  - [x] Tests with mocked service function

- [x] Task: Conductor - User Manual Verification 'CLI Integration' (Protocol in workflow.md)

## Phase 6: End-to-End Verification
<!-- execution: sequential -->
<!-- depends: phase4, phase5 -->

- [x] Task 1: Integration tests <!-- a9f4c7a -->
  - [x] API → Service → Celery task chain test (with eager Celery mode)
  - [x] Full lifecycle: trigger → run transitions → query result
  - [x] Health endpoint with real SQLite, mocked Valkey
  - [x] CLI trigger-run end-to-end test

- [x] Task 2: Exit criteria validation <!-- a9f4c7a -->
  - [x] `uvicorn ainews.api.main:app` starts cleanly
  - [x] `celery -A ainews.tasks.celery_app worker` connects
  - [x] `curl -XPOST /api/trigger` produces run row
  - [x] `/api/runs/{id}` shows status transitions
  - [x] `ainews trigger-run --schedule weekly-ai-news` works
  - [x] `ruff check . && mypy src/ && pytest --cov` all green with ≥ 80%

- [x] Task: Conductor - User Manual Verification 'End-to-End Verification' (Protocol in workflow.md)
