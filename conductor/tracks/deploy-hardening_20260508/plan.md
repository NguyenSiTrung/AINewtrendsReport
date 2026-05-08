# Plan: Ubuntu Deployment + Hardening & QA

## Phase 1: Deployment Infrastructure (systemd + cron + install.sh)
<!-- execution: parallel -->
<!-- depends: -->

- [x] Task 1: Create systemd unit files _(commit: 2350864)_
  <!-- files: deploy/systemd/ainews-api.service, deploy/systemd/ainews-worker.service, deploy/systemd/ainews-beat.service, tests/deploy/test_systemd_units.py -->
  - [x] Write `deploy/systemd/ainews-api.service` (Uvicorn, 2 workers, port 8000)
  - [x] Write `deploy/systemd/ainews-worker.service` (Celery, queues default/scrape/llm, concurrency 4)
  - [x] Write `deploy/systemd/ainews-beat.service` (optional Celery beat)
  - [x] All units: User=ainews, EnvironmentFile=/etc/ainews/ainews.env, Restart=on-failure, ProtectSystem=strict, ReadWritePaths=/var/lib/ainews /var/log/ainews
  - [x] Unit tests: validate unit file structure and key directives

- [x] Task 2: Create cron schedule file _(commit: 2350864)_
  <!-- files: deploy/cron/ainews -->
  - [x] Write `deploy/cron/ainews` with weekly (Mon 7AM) and monthly (1st, 8AM) triggers
  - [x] Cron lines invoke `ainews trigger-run --schedule <name>` as `ainews` user
  - [x] Output redirected to `/var/log/ainews/cron.log`

- [x] Task 3: Create daily backup cron script _(commit: 2350864)_
  <!-- files: deploy/cron/ainews-backup -->
  - [x] Write `deploy/cron/ainews-backup` — daily SQLite `.backup` to /var/backups/ainews/
  - [x] Retention cleanup: `find /var/backups/ainews -name '*.db' -mtime +30 -delete`
  - [x] Configurable retention days via env var

- [x] Task 4: Create logrotate config _(commit: 2350864)_
  <!-- files: deploy/logrotate/ainews -->
  - [x] Write `deploy/logrotate/ainews` — daily rotation, 14-day retention, compress, delaycompress, notifempty
  - [x] Target: `/var/log/ainews/*.log`

- [x] Task 5: Write idempotent `deploy/install.sh` _(commit: 2350864)_
  <!-- files: deploy/install.sh -->
  <!-- depends: task1, task2, task3, task4 -->
  - [x] Detect Ubuntu version (22.04 / 24.04), fail on unsupported
  - [x] Install system packages (python3.12, sqlite3, build-essential, libssl-dev, curl, git, fonts-liberation)
  - [x] Install Valkey from PPA; fallback to `redis-server` from Ubuntu repos
  - [x] Create `ainews` system user + directory layout (/opt/ainews, /var/lib/ainews, /var/log/ainews, /etc/ainews, /var/backups/ainews)
  - [x] Clone/update repo, create venv, pip install -e
  - [x] Install .env.example → /etc/ainews/ainews.env (skip if exists), set root:ainews 0640
  - [x] Run alembic upgrade head + ainews seed as ainews user
  - [x] Copy systemd units → /etc/systemd/system/, daemon-reload, enable (don't start)
  - [x] Copy cron file → /etc/cron.d/ainews, backup cron → /etc/cron.d/ainews-backup
  - [x] Copy logrotate config → /etc/logrotate.d/ainews
  - [x] File-mode audit: verify ownership/permissions on all sensitive paths
  - [x] Print post-install instructions (configure env → start → verify)
  - [x] Shellcheck lint pass on install.sh

- [x] Task: Conductor - User Manual Verification 'Deployment Infrastructure' _(48 tests passing)_

## Phase 2: Operational Hardening (Rate Limits, Caps, Security)
<!-- execution: parallel -->
<!-- depends: -->

- [x] Task 1: Per-domain scraper rate limiter _(commit: 168e752)_
  <!-- files: src/ainews/tools/rate_limiter.py, tests/tools/test_rate_limiter.py, src/ainews/agents/nodes/scraper.py -->
  - [x] Implement token-bucket rate limiter using Valkey (SETNX/INCR with TTL)
  - [x] Default: 2 req/sec/domain, configurable via `settings_kv`
  - [x] Integrate into Scraper node — check before each fetch, wait if throttled
  - [x] Unit tests with mock Valkey

- [x] Task 2: Tavily monthly-quota guard _(commit: 168e752)_
  <!-- files: src/ainews/tools/tavily_guard.py, tests/tools/test_tavily_guard.py, src/ainews/agents/nodes/retriever.py -->
  - [x] Track API call count in `settings_kv` (key: `tavily_calls_YYYY_MM`)
  - [x] Configurable monthly cap (default: 1000), read from `settings_kv`
  - [x] Guard in Retriever node: skip search if cap reached, log warning
  - [x] Auto-reset on new month
  - [x] Unit tests for counter increment, cap enforcement, monthly reset

- [x] Task 3: LLM concurrency cap _(commit: 168e752)_
  <!-- files: src/ainews/llm/concurrency.py, tests/llm/test_concurrency.py, src/ainews/llm/factory.py -->
  - [x] Implement asyncio.Semaphore wrapper around LLM calls (default: 2)
  - [x] Configurable via `settings_kv` key `llm_max_concurrency`
  - [x] Integrate in `llm_factory()` or create `RateLimitedChatModel` wrapper
  - [x] Unit tests verifying semaphore blocks when limit reached

- [x] Task 4: Hard run caps _(commit: 168e752)_
  <!-- files: src/ainews/core/run_caps.py, tests/core/test_run_caps.py, src/ainews/agents/graph.py -->
  - [x] Add `max_total_tokens` (default: 500,000), `max_wall_seconds` (default: 1800), `max_articles` (default: 200) to settings_kv defaults
  - [x] Create `RunCapChecker` utility: check caps at each node transition
  - [x] On cap exceeded: set run status to `capped`, write partial report via degrade path
  - [x] Unit tests for each cap type

- [x] Task 5: Security hardening _(commit: 168e752)_
  <!-- files: src/ainews/api/middleware/csp.py, src/ainews/core/logging.py, tests/api/test_csp.py, tests/core/test_log_masking.py -->
  - [x] Add CSP middleware to FastAPI: `Content-Security-Policy` header on all responses
  - [x] Implement structlog processor to mask sensitive keys (`api_key`, `AINEWS_LLM_API_KEY`, `TAVILY_API_KEY`) in log output
  - [x] Add file-mode validation function to install.sh
  - [x] Unit tests for CSP header presence and log masking

- [x] Task: Conductor - User Manual Verification 'Operational Hardening' _(51 tests passing)_

## Phase 3: E2E Validation & Smoke Test
<!-- execution: sequential -->
<!-- depends: phase1, phase2 -->

- [x] Task 1: Health endpoint enhancement _(commit: 915bba7)_
  - [x] Ensure `/health` probes: DB connectivity, Valkey connectivity, LLM endpoint reachability
  - [x] Return structured JSON: `{db: ok/error, valkey: ok/error, llm: ok/error}`
  - [x] Tests for each probe in isolation

- [x] Task 2: E2E smoke test script _(commit: 915bba7)_
  - [x] Create `tests/e2e/test_smoke.py` (or `deploy/smoke_test.sh`)
  - [x] Steps: verify services → hit /health → trigger run → poll completion → validate report files
  - [x] Add `ainews e2e-test` CLI command wrapping the script
  - [x] Timeout handling (default: 10 min for full pipeline)

- [x] Task 3: Integration verification & documentation _(commit: 915bba7)_
  - [x] Run full test suite: `make lint && make typecheck && make test`
  - [x] Verify all hardening settings have defaults in `settings_kv` seed
  - [x] Verify install.sh passes shellcheck
  - [x] Update README.md with deployment quickstart section

- [x] Task: Conductor - User Manual Verification 'E2E Validation' _(538 tests passing, 0 failures)_
