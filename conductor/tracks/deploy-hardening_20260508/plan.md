# Plan: Ubuntu Deployment + Hardening & QA

## Phase 1: Deployment Infrastructure (systemd + cron + install.sh)
<!-- execution: parallel -->
<!-- depends: -->

- [ ] Task 1: Create systemd unit files
  <!-- files: deploy/systemd/ainews-api.service, deploy/systemd/ainews-worker.service, deploy/systemd/ainews-beat.service, tests/deploy/test_systemd_units.py -->
  - [ ] Write `deploy/systemd/ainews-api.service` (Uvicorn, 2 workers, port 8000)
  - [ ] Write `deploy/systemd/ainews-worker.service` (Celery, queues default/scrape/llm, concurrency 4)
  - [ ] Write `deploy/systemd/ainews-beat.service` (optional Celery beat)
  - [ ] All units: User=ainews, EnvironmentFile=/etc/ainews/ainews.env, Restart=on-failure, ProtectSystem=strict, ReadWritePaths=/var/lib/ainews /var/log/ainews
  - [ ] Unit tests: validate unit file structure and key directives

- [ ] Task 2: Create cron schedule file
  <!-- files: deploy/cron/ainews -->
  - [ ] Write `deploy/cron/ainews` with weekly (Mon 7AM) and monthly (1st, 8AM) triggers
  - [ ] Cron lines invoke `ainews trigger-run --schedule <name>` as `ainews` user
  - [ ] Output redirected to `/var/log/ainews/cron.log`

- [ ] Task 3: Create daily backup cron script
  <!-- files: deploy/cron/ainews-backup -->
  - [ ] Write `deploy/cron/ainews-backup` — daily SQLite `.backup` to /var/backups/ainews/
  - [ ] Retention cleanup: `find /var/backups/ainews -name '*.db' -mtime +30 -delete`
  - [ ] Configurable retention days via env var

- [ ] Task 4: Create logrotate config
  <!-- files: deploy/logrotate/ainews -->
  - [ ] Write `deploy/logrotate/ainews` — daily rotation, 14-day retention, compress, delaycompress, notifempty
  - [ ] Target: `/var/log/ainews/*.log`

- [ ] Task 5: Write idempotent `deploy/install.sh`
  <!-- files: deploy/install.sh -->
  <!-- depends: task1, task2, task3, task4 -->
  - [ ] Detect Ubuntu version (22.04 / 24.04), fail on unsupported
  - [ ] Install system packages (python3.12, sqlite3, build-essential, libssl-dev, curl, git, fonts-liberation)
  - [ ] Install Valkey from PPA; fallback to `redis-server` from Ubuntu repos
  - [ ] Create `ainews` system user + directory layout (/opt/ainews, /var/lib/ainews, /var/log/ainews, /etc/ainews, /var/backups/ainews)
  - [ ] Clone/update repo, create venv, pip install -e
  - [ ] Install .env.example → /etc/ainews/ainews.env (skip if exists), set root:ainews 0640
  - [ ] Run alembic upgrade head + ainews seed as ainews user
  - [ ] Copy systemd units → /etc/systemd/system/, daemon-reload, enable (don't start)
  - [ ] Copy cron file → /etc/cron.d/ainews, backup cron → /etc/cron.d/ainews-backup
  - [ ] Copy logrotate config → /etc/logrotate.d/ainews
  - [ ] File-mode audit: verify ownership/permissions on all sensitive paths
  - [ ] Print post-install instructions (configure env → start → verify)
  - [ ] Shellcheck lint pass on install.sh

- [ ] Task: Conductor - User Manual Verification 'Deployment Infrastructure' (Protocol in workflow.md)

## Phase 2: Operational Hardening (Rate Limits, Caps, Security)
<!-- execution: parallel -->
<!-- depends: -->

- [ ] Task 1: Per-domain scraper rate limiter
  <!-- files: src/ainews/tools/rate_limiter.py, tests/tools/test_rate_limiter.py, src/ainews/agents/nodes/scraper.py -->
  - [ ] Implement token-bucket rate limiter using Valkey (SETNX/INCR with TTL)
  - [ ] Default: 2 req/sec/domain, configurable via `settings_kv`
  - [ ] Integrate into Scraper node — check before each fetch, wait if throttled
  - [ ] Unit tests with mock Valkey

- [ ] Task 2: Tavily monthly-quota guard
  <!-- files: src/ainews/tools/tavily_guard.py, tests/tools/test_tavily_guard.py, src/ainews/agents/nodes/retriever.py -->
  - [ ] Track API call count in `settings_kv` (key: `tavily_calls_YYYY_MM`)
  - [ ] Configurable monthly cap (default: 1000), read from `settings_kv`
  - [ ] Guard in Retriever node: skip search if cap reached, log warning
  - [ ] Auto-reset on new month
  - [ ] Unit tests for counter increment, cap enforcement, monthly reset

- [ ] Task 3: LLM concurrency cap
  <!-- files: src/ainews/llm/concurrency.py, tests/llm/test_concurrency.py, src/ainews/llm/factory.py -->
  - [ ] Implement asyncio.Semaphore wrapper around LLM calls (default: 2)
  - [ ] Configurable via `settings_kv` key `llm_max_concurrency`
  - [ ] Integrate in `llm_factory()` or create `RateLimitedChatModel` wrapper
  - [ ] Unit tests verifying semaphore blocks when limit reached

- [ ] Task 4: Hard run caps
  <!-- files: src/ainews/core/run_caps.py, tests/core/test_run_caps.py, src/ainews/agents/graph.py -->
  - [ ] Add `max_total_tokens` (default: 500,000), `max_wall_seconds` (default: 1800), `max_articles` (default: 200) to settings_kv defaults
  - [ ] Create `RunCapChecker` utility: check caps at each node transition
  - [ ] On cap exceeded: set run status to `capped`, write partial report via degrade path
  - [ ] Unit tests for each cap type

- [ ] Task 5: Security hardening
  <!-- files: src/ainews/api/middleware/csp.py, src/ainews/core/logging.py, tests/api/test_csp.py, tests/core/test_log_masking.py -->
  - [ ] Add CSP middleware to FastAPI: `Content-Security-Policy` header on all responses
  - [ ] Implement structlog processor to mask sensitive keys (`api_key`, `AINEWS_LLM_API_KEY`, `TAVILY_API_KEY`) in log output
  - [ ] Add file-mode validation function to install.sh
  - [ ] Unit tests for CSP header presence and log masking

- [ ] Task: Conductor - User Manual Verification 'Operational Hardening' (Protocol in workflow.md)

## Phase 3: E2E Validation & Smoke Test
<!-- execution: sequential -->
<!-- depends: phase1, phase2 -->

- [ ] Task 1: Health endpoint enhancement
  - [ ] Ensure `/health` probes: DB connectivity, Valkey connectivity, LLM endpoint reachability
  - [ ] Return structured JSON: `{db: ok/error, valkey: ok/error, llm: ok/error}`
  - [ ] Tests for each probe in isolation

- [ ] Task 2: E2E smoke test script
  - [ ] Create `tests/e2e/test_smoke.py` (or `deploy/smoke_test.sh`)
  - [ ] Steps: verify services → hit /health → trigger run → poll completion → validate report files
  - [ ] Add `ainews e2e-test` CLI command wrapping the script
  - [ ] Timeout handling (default: 10 min for full pipeline)

- [ ] Task 3: Integration verification & documentation
  - [ ] Run full test suite: `make lint && make typecheck && make test`
  - [ ] Verify all hardening settings have defaults in `settings_kv` seed
  - [ ] Verify install.sh passes shellcheck
  - [ ] Update README.md with deployment quickstart section

- [ ] Task: Conductor - User Manual Verification 'E2E Validation' (Protocol in workflow.md)
