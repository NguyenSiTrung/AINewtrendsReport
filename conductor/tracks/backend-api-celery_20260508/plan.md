# Plan: Phase 5 — Backend API + Celery

## Phase 1: Pydantic Schemas
<!-- execution: sequential -->
<!-- depends: -->

- [ ] Task 1: Create API request/response schemas
  - [ ] `TriggerRequest` and `TriggerResponse` in `src/ainews/schemas/trigger.py`
  - [ ] `RunListResponse`, `RunDetailResponse` in `src/ainews/schemas/run.py`
  - [ ] `SiteCreate`, `SiteUpdate`, `SiteResponse` in `src/ainews/schemas/site.py`
  - [ ] `ScheduleCreate`, `ScheduleUpdate`, `ScheduleResponse` in `src/ainews/schemas/schedule.py`
  - [ ] `HealthResponse` with component-level status in `src/ainews/schemas/health.py`
  - [ ] Tests for schema validation (required fields, cron format, URL format)

- [ ] Task: Conductor - User Manual Verification 'Pydantic Schemas' (Protocol in workflow.md)

## Phase 2: Celery Infrastructure
<!-- execution: sequential -->
<!-- depends: -->

- [ ] Task 1: Celery app configuration
  - [ ] `src/ainews/tasks/celery_app.py` — Celery instance with Valkey broker URL from `Settings`
  - [ ] Declare three queues: `default`, `scrape`, `llm`
  - [ ] Serialization config (JSON), task result backend (Valkey)
  - [ ] Tests for app instantiation and config resolution

- [ ] Task 2: `run_pipeline` task implementation
  - [ ] Task function in `src/ainews/tasks/pipeline.py`
  - [ ] Load `Run` row from DB, update status `pending → running`
  - [ ] Resolve schedule params (sites, topics, timeframe) from DB
  - [ ] Build LangGraph with `SqliteSaver` checkpointer, invoke with `thread_id=run_id`
  - [ ] On success: update `Run.status = "completed"`, populate `stats` and `finished_at`
  - [ ] On failure: update `Run.status = "failed"`, populate `error` field
  - [ ] Resumability: detect existing `checkpoint_id`, resume from last checkpoint
  - [ ] Tests with mocked graph invocation

- [ ] Task: Conductor - User Manual Verification 'Celery Infrastructure' (Protocol in workflow.md)

## Phase 3: Service Layer
<!-- execution: sequential -->
<!-- depends: phase1, phase2 -->

- [ ] Task 1: Pipeline service
  - [ ] `src/ainews/services/pipeline.py` with `create_and_enqueue_run()`
  - [ ] Accepts `schedule_name` (resolve from DB) or inline `params` (topics, sites, timeframe_days)
  - [ ] Creates `Run` row with `status="pending"`, `triggered_by` field
  - [ ] Calls `run_pipeline.delay(run_id)` to enqueue
  - [ ] Returns `run_id` for caller
  - [ ] Tests with mocked DB session and Celery task

- [ ] Task: Conductor - User Manual Verification 'Service Layer' (Protocol in workflow.md)

## Phase 4: FastAPI Application & Routers
<!-- execution: sequential -->
<!-- depends: phase3 -->

- [ ] Task 1: App factory and dependencies
  - [ ] `src/ainews/api/main.py` — `create_app()` with lifespan handler (engine init/dispose)
  - [ ] `src/ainews/api/deps.py` — `get_db` dependency yielding SQLAlchemy sessions
  - [ ] CORS middleware for localhost
  - [ ] Global exception handlers (validation errors → 422, DB errors → 500)
  - [ ] Tests for app startup/shutdown lifecycle

- [ ] Task 2: Health router
  - [ ] `src/ainews/api/routes/health.py` — `GET /api/health`
  - [ ] Probes: SQLite DB connectivity, Valkey ping
  - [ ] Returns `{status, components: {db: ok/down, valkey: ok/down}}`
  - [ ] Tests with healthy and degraded scenarios

- [ ] Task 3: Trigger router
  - [ ] `src/ainews/api/routes/trigger.py` — `POST /api/trigger`
  - [ ] Calls shared service `create_and_enqueue_run()`
  - [ ] Returns `{run_id, status: "pending"}`
  - [ ] Validates schedule exists (if `schedule_name` provided)
  - [ ] Tests with mocked service layer

- [ ] Task 4: Runs router
  - [ ] `src/ainews/api/routes/runs.py`
  - [ ] `GET /api/runs` — paginated list (offset/limit), filterable by status
  - [ ] `GET /api/runs/{run_id}` — detail with metrics, errors, timestamps
  - [ ] 404 handling for unknown run_id
  - [ ] Tests with seeded run data

- [ ] Task 5: Sites CRUD router
  - [ ] `src/ainews/api/routes/sites.py`
  - [ ] `GET`, `POST`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
  - [ ] Pydantic validation on create/update
  - [ ] Unique URL constraint handling (409 on duplicate)
  - [ ] Tests for full CRUD lifecycle

- [ ] Task 6: Schedules CRUD router
  - [ ] `src/ainews/api/routes/schedules.py`
  - [ ] `GET`, `POST`, `GET/{id}`, `PUT/{id}`, `DELETE/{id}`
  - [ ] Cron expression validation via `croniter`
  - [ ] Tests for full CRUD lifecycle

- [ ] Task: Conductor - User Manual Verification 'FastAPI Application & Routers' (Protocol in workflow.md)

## Phase 5: CLI Integration
<!-- execution: sequential -->
<!-- depends: phase3 -->

- [ ] Task 1: Update `trigger-run` CLI command
  - [ ] Implement `ainews trigger-run --schedule <name>` using shared service
  - [ ] Implement `ainews trigger-run --topics "AI,ML" --days 7` for one-off runs
  - [ ] Set `triggered_by = "cli"`
  - [ ] Tests with mocked service function

- [ ] Task: Conductor - User Manual Verification 'CLI Integration' (Protocol in workflow.md)

## Phase 6: End-to-End Verification
<!-- execution: sequential -->
<!-- depends: phase4, phase5 -->

- [ ] Task 1: Integration tests
  - [ ] API → Service → Celery task chain test (with eager Celery mode)
  - [ ] Full lifecycle: trigger → run transitions → query result
  - [ ] Health endpoint with real SQLite, mocked Valkey
  - [ ] CLI trigger-run end-to-end test

- [ ] Task 2: Exit criteria validation
  - [ ] `uvicorn ainews.api.main:app` starts cleanly
  - [ ] `celery -A ainews.tasks.celery_app worker` connects
  - [ ] `curl -XPOST /api/trigger` produces run row
  - [ ] `/api/runs/{id}` shows status transitions
  - [ ] `ainews trigger-run --schedule weekly-ai-news` works
  - [ ] `ruff check . && mypy src/ && pytest --cov` all green with ≥ 80%

- [ ] Task: Conductor - User Manual Verification 'End-to-End Verification' (Protocol in workflow.md)
