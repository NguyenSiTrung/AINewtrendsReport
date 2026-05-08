# Spec: Ubuntu Deployment + Hardening & QA

## Overview

Combine PLAN.md Phase 7 (Ubuntu Deployment) and Phase 8 (Hardening & QA) into a
single track that takes the fully functional application (Phases 0–6 complete) and
makes it production-ready on a local Ubuntu server. This covers idempotent system
installation, systemd process supervision, cron scheduling, operational hardening
(rate limits, resource caps, backups, log rotation, security), and end-to-end
validation.

**Target environment:** Local Ubuntu server (22.04 or 24.04 LTS), HTTP-only
(port 8000), no public internet exposure, no Nginx/Certbot.

## Functional Requirements

### FR-1: Idempotent Installer (`deploy/install.sh`)

- Detect Ubuntu version (22.04 / 24.04) and adapt package names if needed.
- Install system packages: Python 3.12, SQLite3, Valkey (from official PPA with
  Redis ≤ 7.2 fallback from Ubuntu repos), build-essential, libssl-dev, curl, git,
  fonts-liberation.
- Create `ainews` system user with home `/opt/ainews`.
- Clone/update repo to `/opt/ainews/app`; create venv at `/opt/ainews/venv`;
  `pip install -e`.
- Create directories: `/var/lib/ainews`, `/var/lib/ainews/reports`,
  `/var/log/ainews`, `/etc/ainews`, `/var/backups/ainews`.
- Install `.env.example` → `/etc/ainews/ainews.env` (only if not already present;
  never overwrite existing config). Set ownership `root:ainews`, mode `0640`.
- Run `alembic upgrade head` and `ainews seed` as `ainews` user.
- Script is idempotent: safe to re-run on upgrades.

### FR-2: systemd Service Units

- `ainews-api.service` — Uvicorn with 2 workers on `0.0.0.0:8000`.
- `ainews-worker.service` — Celery worker with queues `default,scrape,llm`,
  concurrency 4.
- `ainews-beat.service` (optional) — Celery beat alternative to cron.
- All units: `User=ainews`, `EnvironmentFile=/etc/ainews/ainews.env`,
  `Restart=on-failure`, `ProtectSystem=strict`,
  `ReadWritePaths=/var/lib/ainews /var/log/ainews`.
- `install.sh` enables but does NOT start services (user configures env first).

### FR-3: Cron Schedule

- Install `/etc/cron.d/ainews` with weekly (Monday 7 AM) and monthly (1st, 8 AM)
  triggers via `ainews trigger-run --schedule <name>`.
- Cron output appended to `/var/log/ainews/cron.log`.

### FR-4: Per-Domain Scraper Rate Limits

- Token-bucket rate limiter per domain in Valkey.
- Default: 2 requests/second/domain, configurable via `settings_kv`.
- Scraper node checks rate limit before each fetch; waits if throttled.

### FR-5: Tavily Monthly-Quota Guard

- Track Tavily API call count in `settings_kv` (reset monthly).
- Configurable monthly cap (default: 1000 calls).
- When cap reached: skip Retriever node, log warning, produce degraded report
  from cached/scraped content only.

### FR-6: LLM Concurrency Cap

- Semaphore limiting concurrent LLM calls (default: 2, configurable).
- Prevents GPU saturation on local LLM server.
- Applied in `llm_factory()` or as a wrapper around `ChatOpenAI.invoke()`.

### FR-7: Hard Run Caps

- `max_total_tokens` (default: 500,000) — abort run if cumulative token usage
  exceeds cap.
- `max_wall_seconds` (default: 1800 = 30 min) — abort run if wall-clock time
  exceeds cap.
- `max_articles` (default: 200) — stop fetching after N articles per run.
- All configurable in `settings_kv`, checked at each node transition.

### FR-8: Backup Automation

- Daily SQLite `.backup` to `/var/backups/ainews/` via cron.
- Retention: 30 days (configurable), enforced by `find -mtime +N -delete`.
- Reports directory retention policy enforced by Celery housekeeping task.

### FR-9: Log Rotation

- `/etc/logrotate.d/ainews` config for `/var/log/ainews/*.log`.
- Daily rotation, 14-day retention, compress, delaycompress, notifempty.

### FR-10: Security Hardening

- CSP headers on all admin UI responses (restrictive: `default-src 'self'`,
  allow CDN for Tailwind/HTMX/Alpine only if loaded externally).
- File-mode audit in `install.sh`: verify `/etc/ainews/ainews.env` is `0640`,
  DB file is `0640`, reports dir is `0750`.
- API key masking in structlog: filter `api_key`, `AINEWS_LLM_API_KEY`,
  `TAVILY_API_KEY` values in log output.
- Ensure no secrets in database (v1 policy).

### FR-11: E2E Smoke Test

- Script or pytest fixture that:
  1. Verifies all services are running (`systemctl is-active`).
  2. Hits `/health` endpoint (DB, Valkey, LLM connectivity probes).
  3. Triggers a manual run via `POST /api/trigger`.
  4. Polls `/api/runs/{id}` until completion or timeout.
  5. Validates report files exist on disk.
- Can be run as `ainews e2e-test` CLI command or `pytest tests/e2e/`.

## Non-Functional Requirements

- **Idempotency:** `install.sh` can be run multiple times without side effects.
- **Zero-downtime upgrades:** Re-running install.sh on a running system should
  update code and restart services gracefully.
- **Minimal dependencies:** No Nginx, no Certbot, no Node.js toolchain.
- **Observability:** All hardening actions logged via structlog.

## Acceptance Criteria

1. `deploy/install.sh` completes on a fresh Ubuntu 22.04 and 24.04 system
   without errors.
2. After configuring `/etc/ainews/ainews.env` and starting services,
   `curl http://localhost:8000/health` returns 200 with all probes passing.
3. Weekly cron fires and enqueues a Celery task successfully.
4. Rate limits, quota guards, and run caps are enforced (verified by unit tests
   with mocked boundaries).
5. Daily backup cron produces `.backup` files in `/var/backups/ainews/`.
6. Log rotation config is valid (`logrotate -d /etc/logrotate.d/ainews`).
7. CSP headers present on admin UI responses.
8. API keys are masked in log output.
9. E2E smoke test passes on deployed system.
10. First scheduled cron run completes successfully without manual intervention.

## Out of Scope

- Nginx reverse proxy / HTTPS / TLS certificates.
- Multi-user auth / role-based access control.
- Docker containerization.
- CI/CD pipeline.
- PostgreSQL migration.
- Remote/cloud deployment.
