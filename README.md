# AI News & Trends Report

A multi-agent system that automatically gathers, processes, and synthesizes AI news and trends from a configurable list of sources.

## Status

✅ **All phases complete (0–9)** — fully implemented with deployment hardening and documentation.

The full architecture and phased development plan lives in [`PLAN.md`](./PLAN.md).

## Highlights

- **Orchestration:** LangGraph + LangChain (multi-agent: Planner → Retriever → Scraper → Filter → Dedup → Synthesizer → Trender → Writer → Exporter)
- **Search:** Tavily Search API with monthly quota guard
- **LLM:** single OpenAI-compatible endpoint pointed at a self-hosted local LLM server (vLLM / Ollama / LM Studio / llama.cpp / TGI) with concurrency caps
- **Database:** SQLite (public domain) with WAL mode + FTS5
- **Backend:** FastAPI + Celery (Valkey broker)
- **Admin UI:** Jinja2 + HTMX + Tailwind + Alpine.js
- **Scheduling:** Ubuntu cron + manual triggers
- **Output:** Markdown reports + Excel (.xlsx) export
- **Deployment:** Ubuntu 22.04/24.04 via systemd (HTTP-only, local server)
- **Security:** CSP headers, CSRF protection, log masking, systemd hardening

All runtime components are permissively licensed (MIT / Apache-2.0 / BSD / public domain) — royalty-free and enterprise-safe.

## Quick Start (Development)

```bash
# Clone and install
git clone https://github.com/NguyenSiTrung/AINewtrendsReport.git
cd AINewtrendsReport
cp .env.example .env  # Edit with your API keys
uv sync

# Run migrations + seed
uv run alembic upgrade head
uv run ainews seed

# Ensure Valkey is running locally (required for Celery)
# Valkey is the 100% open-source, commercial-safe fork of Redis.
sudo apt-get install -y lsb-release curl gpg
curl -fsSL https://serverless.industries/public.key | sudo gpg --dearmor -o /usr/share/keyrings/valkey.gpg
echo "deb [signed-by=/usr/share/keyrings/valkey.gpg] https://serverless.industries/valkey/apt $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/valkey.list
sudo apt-get update
sudo apt-get install -y valkey-server
sudo systemctl start valkey-server

# Open Terminal 1: Start development server
uv run uvicorn ainews.api.main:app --reload --port 8000

# Open Terminal 2: Start background worker
uv run celery -A ainews.tasks.celery_app worker --loglevel=info

# Open Terminal 3: Start beat scheduler
uv run celery -A ainews.tasks.celery_app beat --loglevel=info

# Run tests
uv run pytest
```

## Deployment (Ubuntu Server)

### Prerequisites

- Ubuntu 22.04 or 24.04 LTS
- Root access (`sudo`)
- Valkey or Redis server
- Local LLM server (vLLM / Ollama / LM Studio)

### Install

```bash
# One-line idempotent installer
sudo bash deploy/install.sh
```

This will:
1. Install system packages (Python 3.12, SQLite, etc.)
2. Install Valkey (or Redis fallback)
3. Create `ainews` system user and directory layout
4. Set up virtualenv and install dependencies
5. Copy environment template to `/etc/ainews/ainews.env`
6. Run database migrations and seed
7. Install systemd units, cron schedules, and logrotate config

### Configure

```bash
# Edit environment configuration
sudo nano /etc/ainews/ainews.env

# Required settings:
#   AINEWS_LLM_BASE_URL  — Your local LLM server endpoint
#   AINEWS_TAVILY_API_KEY — Tavily API key for news search
```

### Start Services

```bash
# Start API, worker, and scheduler
sudo systemctl start ainews-api ainews-worker ainews-beat

# Verify
curl http://localhost:8000/api/health

# View logs
sudo journalctl -u ainews-api -f
```

### Service Management

| Command | Description |
|---------|-------------|
| `systemctl status ainews-api` | API server status |
| `systemctl status ainews-worker` | Celery worker status |
| `systemctl status ainews-beat` | Celery scheduler status |
| `systemctl restart ainews-api ainews-worker ainews-beat` | Restart services |
| `journalctl -u ainews-api -f` | Follow API logs |

### Automated Schedules

| Schedule | Trigger | Description |
|----------|---------|-------------|
| Weekly | Mon 7:00 AM | AI news digest |
| Monthly | 1st of month 8:00 AM | AI trends report |
| Daily | 2:00 AM | SQLite database backup |

### File Layout

```
/opt/ainews/app/         Application code
/opt/ainews/venv/        Python virtualenv
/etc/ainews/ainews.env   Configuration (0640, root:ainews)
/var/lib/ainews/         Data (DB, reports)
/var/log/ainews/         Log files
/var/backups/ainews/     Database backups (30-day retention)
```

### Operational Guards

| Guard | Default | Configurable via |
|-------|---------|------------------|
| Scraper rate limit | 2 req/sec/domain | `settings_kv` |
| Tavily monthly cap | 1,000 calls/month | `settings_kv` |
| LLM concurrency | 2 concurrent | `settings_kv` |
| Run token cap | 500,000 tokens | `settings_kv` |
| Run wall time | 30 minutes | `settings_kv` |
| Run article cap | 200 articles | `settings_kv` |

## Documentation

| Document | Description |
|----------|-------------|
| [`PLAN.md`](./PLAN.md) | Full development plan and design spec |
| [`docs/architecture.md`](./docs/architecture.md) | System architecture reference |
| [`docs/operations.md`](./docs/operations.md) | Operational runbook (add sites, switch LLM, restore backups, etc.) |

## License

All runtime components are permissively licensed. See individual package licenses for details.
