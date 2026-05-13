# Architecture Guide

> AI News & Trends Report — system design reference (v2, updated 2026-05-13).
>
> For the full development plan see [`../PLAN.md`](../PLAN.md).

---

## 1. System Overview

A **multi-agent pipeline** that gathers AI news from configurable sources (Tavily Search API), scrapes/filters/deduplicates articles, synthesizes summaries and trends via a self-hosted LLM, and produces Markdown + Excel reports. Runs entirely on a single Ubuntu server.

---

## 2. Component Diagram

```
                    ╭───────────────────────────────╮
                    │      Admin Web UI (HTMX)      │
                    │  Sites · Schedules · Reports  │
                    ╰───────────────┬───────────────╯
                                    │ HTTP + HTMX
                                    ▼
   ╭──────────────────────────────────────────────────────────╮
   │                   FastAPI Backend                        │
   │ /api/health  /api/trigger  /api/runs  /api/sites  ...   │
   ╰──────┬─────────────────────┬──────────────────────┬──────╯
          │ SQLAlchemy          │ enqueue              │ read
          ▼                     ▼                      ▼
   ╭──────────────╮     ╭──────────────╮       ╭──────────────╮
   │ SQLite (WAL) │◀────│   Valkey     │◀──────│ Reports FS   │
   │  + FTS5      │     │ broker+cache │       │  *.md *.xlsx │
   ╰──────┬───────╯     ╰──────┬───────╯       ╰──────────────╯
          │                    ▼
          │             ╭──────────────╮
          │             │ Celery Worker│──▶ LangGraph Pipeline
          │             ╰──────┬───────╯
          │                    │
          │         ┌──────────┴──────────┐
          │         ▼                     ▼
          │  ╭─────────────╮  ╭──────────────────────╮
          │  │ Tavily API  │  │ Self-hosted local LLM│
          │  ╰─────────────╯  ╰──────────────────────╯
          ▼
   ╭──────────────╮     ╭──────────────╮
   │ cron (Ubuntu)│────▶│ ainews CLI   │──▶ enqueue Celery
   ╰──────────────╯     ╰──────────────╯
```

### Runtime daemons

| Unit | Binary | Purpose |
|------|--------|---------|
| `ainews-api.service` | uvicorn | FastAPI server (port 1210) |
| `ainews-worker.service` | celery worker | Pipeline execution |
| `ainews-beat.service` | celery beat | Optional scheduler |

---

## 3. Repository Layout

```
├── pyproject.toml              # Project & tool config
├── Makefile                    # Dev shortcuts (lint, test, css)
├── alembic/                    # Database migrations
├── deploy/
│   ├── install.sh              # Idempotent local setup + systemd config
│   ├── update.sh               # Code upgrade (deps + migrate + restart)
│   ├── stop.sh                 # Graceful service shutdown
│   ├── cron/                   # Cron schedule snippets (manual install)
│   ├── logrotate/              # Log rotation config (manual install)
│   └── scripts/backup_db.sh   # SQLite backup script
├── docs/                       # ← You are here
├── tools/                      # Vendored binaries (Tailwind CSS CLI)
├── src/ainews/
│   ├── core/                   # Config, logging, database, run_caps
│   ├── models/                 # SQLAlchemy ORM
│   ├── schemas/                # Pydantic schemas
│   ├── llm/                    # Factory, config, connectivity, concurrency
│   ├── agents/                 # LangGraph nodes, tools, prompts, resilience
│   ├── services/               # Business logic (pipeline service, run logger)
│   ├── tasks/                  # Celery app, beat scheduler, pipeline task
│   ├── exporters/              # Markdown and Excel exporters
│   ├── tools/                  # Rate limiter, Tavily guard
│   ├── api/                    # FastAPI routes, templates, auth, middleware
│   └── cli.py                  # Typer CLI
└── tests/                      # Pytest suite
```

---

## 4. Tech Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Language | Python 3.12+ | PSF |
| Orchestration | LangGraph + LangChain | MIT |
| LLM client | langchain-openai (OpenAI-compatible) | MIT |
| Search | Tavily Search API | MIT |
| Web framework | FastAPI + Uvicorn | MIT/BSD |
| Task queue | Celery | BSD |
| Broker | Valkey | BSD-3 |
| Database | SQLite (WAL + FTS5) | Public domain |
| ORM | SQLAlchemy 2.0 | MIT |
| Migrations | Alembic | MIT |
| Admin UI | Jinja2 + HTMX + Tailwind + Alpine.js | BSD/MIT |
| Export | openpyxl, Jinja2 | MIT |
| CLI | Typer | MIT |

---

## 5. Database Schema

SQLite with WAL mode. Pragmas: `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`.

**Core tables:** `sites`, `schedules`, `runs`, `articles`, `reports`, `run_logs`, `users`, `settings_kv`.

**Special tables:**
- `langgraph_checkpoints` — managed by `langgraph-checkpoint-sqlite` for run resumption.
- `reports_fts` — FTS5 virtual table for full-text search in admin UI.

See `PLAN.md §2.3` for full column-level schema.

---

## 6. Pipeline Topology

Each node: `(state) → partial_state`. All LLM calls go through `llm_factory()`.

```
START → Planner → Retriever → Scraper → Filter → Dedup
        → Synthesizer → Trender → Writer → Exporter → END
```

- **Filter** has a conditional retry loop back to Planner (max N loops).
- **Retriever** and **Synthesizer** use `Send()` for parallel fan-out.

| Node | LLM? | Key tools |
|------|-------|-----------|
| Planner | Yes | DB read |
| Retriever | No | TavilySearch |
| Scraper | No | httpx, trafilatura |
| Filter | Yes | Structured output |
| Dedup | No | simhash, Jaccard |
| Synthesizer | Yes | Structured output |
| Trender | Yes | — |
| Writer | Yes* | Jinja2 templates |
| Exporter | No | openpyxl |

\* Writer uses LLM only for the Executive Summary polish pass.

### Cross-cutting policies

- **Error handling:** try/except per node → `state.errors`. Degrade path emits partial report.
- **Token tracking:** per-node `state.metrics` (input/output tokens, wall time).
- **LLM resilience:** `tenacity` retries with exponential backoff.
- **Run caps:** tokens (500k), wall time (30min), articles (200) via `core/run_caps.py`.

---

## 7. Configuration

### LLM

Single OpenAI-compatible endpoint. Config resolution: `model_override > db_overrides (settings_kv) > env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `AINEWS_LLM_BASE_URL` | `http://127.0.0.1:8080/v1` | LLM server URL |
| `AINEWS_LLM_API_KEY` | `not-needed` | API key |
| `AINEWS_LLM_MODEL` | `local-model` | Model name |
| `AINEWS_LLM_TEMPERATURE` | `0.0` | Sampling temp |
| `AINEWS_LLM_MAX_TOKENS` | `4096` | Max output tokens |
| `AINEWS_LLM_TIMEOUT` | `120` | Timeout (seconds) |

### Other environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AINEWS_DB_PATH` | `./var/ainews.db` | SQLite database file |
| `AINEWS_VALKEY_URL` | `redis://127.0.0.1:6379/0` | Valkey broker URL |
| `AINEWS_TAVILY_API_KEY` | *(empty)* | Tavily search API key |
| `AINEWS_REPORT_MAX_SOURCES` | `50` | Max sources per report |
| `AINEWS_TIMEZONE` | *(auto-detected)* | Display timezone via `tzlocal` |
| `AINEWS_LOG_LEVEL` | `INFO` | Logging level |
| `AINEWS_JWT_SECRET` | *(empty)* | JWT secret for admin sessions |

---

## 8. API Surface

### REST endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/health` | DB/Valkey/Celery probes |
| POST | `/api/trigger` | Enqueue pipeline run |
| GET | `/api/runs` | Paginated run history |
| GET | `/api/runs/{id}` | Run detail + metrics |
| GET | `/api/sites` | List all sites |
| POST | `/api/sites` | Create site |
| GET | `/api/sites/{id}` | Get site detail |
| PUT | `/api/sites/{id}` | Update site |
| DELETE | `/api/sites/{id}` | Delete site |
| GET | `/api/schedules` | List schedules |
| POST | `/api/schedules` | Create schedule |
| GET | `/api/schedules/{id}` | Get schedule detail |
| PUT | `/api/schedules/{id}` | Update schedule |
| DELETE | `/api/schedules/{id}` | Delete schedule |

### Admin UI (server-rendered)

Dashboard, Sites, Schedules, Users, LLM Settings, Runs (list + detail + stepper), Trigger, Logs (SSE), Settings (pipeline guards + purge/clear), Health, Report viewer (Markdown preview + MD/XLSX download).

Auth: JWT in HttpOnly cookie + CSRF tokens.

---

## 9. Deployment

- **Target:** Ubuntu 22.04/24.04 LTS, HTTP-only local network.
- **Installer:** `sudo bash deploy/install.sh` (idempotent, run from project directory).
- **File layout:** app runs from the git clone directory; data in `./var/`, config in `.env`, systemd units generated at `/etc/systemd/system/ainews-*.service`.
- **Update:** `bash deploy/update.sh` — syncs deps via `uv`, runs migrations, restarts services, health check.
- **Stop:** `bash deploy/stop.sh` — graceful shutdown with status verification.
- **Security:** CSP headers, CSRF tokens, SSL CA bundle env vars in systemd units, log masking.

---

## 10. Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Database | SQLite WAL | Zero-ops, public domain, single-server |
| Frontend | HTMX + Jinja2 | Lightest stack, minimal JS |
| Scheduler | Ubuntu cron | Simple, auditable |
| LLM | Single OpenAI-compatible endpoint | Server-agnostic |
| Broker | Valkey (BSD-3) | Message broker without licensing issues |
| Dedup | URL + simhash + Jaccard | No embeddings for v1 |
| Checkpoints | langgraph-checkpoint-sqlite | Same DB file, unified backup |
