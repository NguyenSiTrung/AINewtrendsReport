# Operations Runbook

> Day-to-day operational procedures for the AI News & Trends Report system.

---

## Table of Contents

1. [Add a New Source Site](#1-add-a-new-source-site)
2. [Switch the Local LLM Endpoint or Model](#2-switch-the-local-llm-endpoint-or-model)
3. [Replay a Failed Run](#3-replay-a-failed-run)
4. [Rotate the Tavily API Key](#4-rotate-the-tavily-api-key)
5. [Restore from Backup](#5-restore-from-backup)
6. [Create or Edit a Schedule](#6-create-or-edit-a-schedule)
7. [Manual Pipeline Run](#7-manual-pipeline-run)
8. [Service Management](#8-service-management)
9. [Log Inspection](#9-log-inspection)
10. [Health Checks](#10-health-checks)
11. [Operational Guards Reference](#11-operational-guards-reference)

---

## 1. Add a New Source Site

### Via Admin UI

1. Open `http://<server>:1210/sites`
2. Click **Add Site**
3. Fill in:
   - **Name**: Human-readable label (e.g. "MIT Technology Review")
   - **URL**: Base domain (e.g. `https://www.technologyreview.com`)
   - **Category**: e.g. `research`, `industry`, `blog`
   - **Priority**: 1–10 (higher = preferred in dedup)
   - **Crawl depth**: default 1
   - **JS render**: enable for SPA sites
   - **Enabled**: toggle on/off
4. Click **Save**

### Via API

```bash
curl -X POST http://localhost:1210/api/sites \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MIT Technology Review",
    "url": "https://www.technologyreview.com",
    "category": "research",
    "priority": 8,
    "crawl_depth": 1,
    "js_render": false,
    "enabled": true
  }'
```

The new site will be included in the next pipeline run that doesn't have a specific site filter.

---

## 2. Switch the Local LLM Endpoint or Model

### Option A: Via Admin UI (runtime, no restart)

1. Open `http://<server>:1210/llm`
2. Update **Base URL**, **Model**, or other fields
3. Click **Test Connection** to verify
4. Click **Save**

Changes are stored in `settings_kv` and picked up by `llm_factory()` on the next worker tick — no service restart needed.

### Option B: Via environment (persistent, requires restart)

```bash
# Edit the environment file
sudo nano /etc/ainews/ainews.env

# Change these values:
AINEWS_LLM_BASE_URL=http://127.0.0.1:11434/v1   # e.g. Ollama
AINEWS_LLM_MODEL=qwen2.5-32b-instruct

# Restart services to pick up changes
sudo systemctl restart ainews-api ainews-worker ainews-beat
```

### Verify connectivity

```bash
# CLI test
/opt/ainews/venv/bin/ainews llm test

# API test
curl http://localhost:1210/api/health | python3 -m json.tool
```

### Supported LLM servers

Any server exposing the OpenAI `/v1/chat/completions` endpoint:
- **vLLM**: `http://host:8000/v1`
- **Ollama**: `http://host:11434/v1`
- **LM Studio**: `http://host:1234/v1`
- **llama-server**: `http://host:8080/v1`
- **TGI**: `http://host:8080/v1`

---

## 3. Replay a Failed Run

### Check run status

```bash
# List recent runs
curl http://localhost:1210/api/runs | python3 -m json.tool

# Get detail of a specific run
curl http://localhost:1210/api/runs/<run-id> | python3 -m json.tool
```

Or view in the Admin UI at `/runs`.

### Re-trigger from the same schedule

```bash
# Via CLI (same code path as the API)
/opt/ainews/venv/bin/ainews trigger-run --schedule weekly-ai-news

# Via API
curl -X POST http://localhost:1210/api/trigger \
  -H "Content-Type: application/json" \
  -d '{"schedule_name": "weekly-ai-news"}'
```

### Resume a checkpointed run

If a run was interrupted mid-pipeline, the LangGraph checkpoint enables resumption. The Celery task will automatically attempt to resume from the last checkpoint when re-enqueued with the same `checkpoint_id`.

### One-off run with custom parameters

```bash
/opt/ainews/venv/bin/ainews trigger-run --topics "AI,ML" --days 7
```

---

## 4. Rotate the Tavily API Key

### Step 1: Update the environment file

```bash
sudo nano /etc/ainews/ainews.env
# Update: AINEWS_TAVILY_API_KEY=tvly-new-key-here
```

### Step 2: Restart services

```bash
sudo systemctl restart ainews-api ainews-worker ainews-beat
```

### Step 3: Verify

```bash
curl http://localhost:1210/api/health | python3 -m json.tool
# Check that all components show "ok"
```

> **Note:** The Tavily key is never stored in the database. It lives only in the env file with `root:ainews 0640` permissions.

---

## 5. Restore from Backup

### Automated backups

Daily backups run at 2:00 AM via cron:
- Location: `/var/backups/ainews/ainews-YYYY-MM-DD.db`
- Retention: 30 days (auto-rotated)

### Restore procedure

```bash
# 1. Stop services
sudo systemctl stop ainews-api ainews-worker ainews-beat

# 2. List available backups
ls -la /var/backups/ainews/

# 3. Copy backup over the live database
sudo -u ainews cp /var/backups/ainews/ainews-2026-05-07.db \
                  /var/lib/ainews/ainews.db

# 4. Verify database integrity
sudo -u ainews sqlite3 /var/lib/ainews/ainews.db "PRAGMA integrity_check;"

# 5. Restart services
sudo systemctl start ainews-api ainews-worker ainews-beat

# 6. Verify
curl http://localhost:1210/api/health
```

### Manual backup (ad-hoc)

```bash
sudo -u ainews sqlite3 /var/lib/ainews/ainews.db \
  ".backup '/var/backups/ainews/ainews-manual-$(date +%F-%H%M).db'"
```

---

## 6. Create or Edit a Schedule

### Via Admin UI

1. Open `http://<server>:1210/schedules`
2. Click **Add Schedule** (or edit existing)
3. Configure:
   - **Name**: Unique identifier (e.g. `weekly-ai-news`)
   - **Cron expression**: e.g. `0 7 * * 1` (Mon 7 AM)
   - **Timeframe (days)**: How far back to search
   - **Topics**: JSON list (e.g. `["AI", "Machine Learning"]`)
   - **Site filter**: Optional JSON list of site IDs
   - **Model override**: Optional model name for this schedule
4. Click **Save**

### Default schedules (from seed)

| Name | Cron | Window | Description |
|------|------|--------|-------------|
| `weekly-ai-news` | `0 7 * * 1` | 7 days | Weekly AI news digest |
| `monthly-trends` | `0 8 1 * *` | 30 days | Monthly trends report |

### Cron integration

The cron entries in `/etc/cron.d/ainews` reference schedules by name:
```
0 7 * * 1 ainews /opt/ainews/venv/bin/ainews trigger-run --schedule weekly-ai-news
0 8 1 * * ainews /opt/ainews/venv/bin/ainews trigger-run --schedule monthly-trends
```

Modifying schedule parameters in the DB/UI takes effect immediately — no cron file edit needed.

---

## 7. Manual Pipeline Run

### From Admin UI

1. Open `http://<server>:1210/trigger`
2. Select a schedule template or enter custom parameters
3. Click **Trigger Run**
4. Monitor progress at `/runs`

### From CLI

```bash
# Named schedule
/opt/ainews/venv/bin/ainews trigger-run --schedule weekly-ai-news

# Custom one-off
/opt/ainews/venv/bin/ainews trigger-run --topics "AI,LLM,Agents" --days 14

# Direct pipeline (development, no Celery)
/opt/ainews/venv/bin/ainews run start --topic AI --topic LLM --days 7
```

---

## 8. Service Management

### Common commands

```bash
# Status
sudo systemctl status ainews-api
sudo systemctl status ainews-worker
sudo systemctl status ainews-beat

# Start / Stop / Restart
sudo systemctl start ainews-api ainews-worker ainews-beat
sudo systemctl stop ainews-api ainews-worker ainews-beat
sudo systemctl restart ainews-api ainews-worker ainews-beat

# Enable on boot
sudo systemctl enable ainews-api ainews-worker ainews-beat
```

### Checking Valkey

```bash
sudo systemctl status valkey-server
valkey-cli ping                       # → PONG
```

---

## 9. Log Inspection

### Real-time logs

```bash
# API server logs
sudo journalctl -u ainews-api -f

# Celery worker logs
sudo journalctl -u ainews-worker -f

# Celery scheduler logs
sudo journalctl -u ainews-beat -f

# Both combined
sudo journalctl -u 'ainews-*' -f

# Cron logs
tail -f /var/log/ainews/cron.log
```

### Admin UI log viewer

Open `http://<server>:1210/logs` — supports filtering by run ID, node, and log level with SSE auto-refresh.

### Log rotation

Managed by logrotate (`/etc/logrotate.d/ainews`): daily rotation, 14-day retention, compressed.

---

## 10. Health Checks

### API endpoint

```bash
curl http://localhost:1210/api/health | python3 -m json.tool
```

Response shows status for each component:
```json
{
  "status": "ok",
  "components": {
    "db": {"status": "ok"},
    "valkey": {"status": "ok"},
    "llm": {"status": "ok", "detail": "model=qwen2.5, latency=142ms"}
  }
}
```

Possible overall statuses: `ok`, `degraded` (partial), `down` (all failed).

### Admin UI health page

`http://<server>:1210/health` — visual grid of component statuses.

---

## 11. Operational Guards Reference

| Guard | Default | Configurable via |
|-------|---------|------------------|
| Scraper rate limit | 2 req/sec/domain | `settings_kv` |
| Tavily monthly cap | 1,000 calls/month | `settings_kv` |
| LLM concurrency | 2 concurrent | `settings_kv` |
| Run token cap | 500,000 tokens | `settings_kv` |
| Run wall time | 30 minutes | `settings_kv` |
| Run article cap | 200 articles | `settings_kv` |

All guard values can be changed via the Admin UI at `/settings` or directly in the `settings_kv` table.
