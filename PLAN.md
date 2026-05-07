# AI News & Trends Reporting System — Development Plan (v3)

> **Revision notes (v3):**
> 1. Database is **SQLite** (public-domain, single-file, zero-admin). PostgreSQL retained only as an optional upgrade path. Both are royalty-free and unrestricted for commercial/enterprise use.
> 2. LLM layer is a **single OpenAI-compatible endpoint** pointed at the user's **self-hosted local LLM server** (e.g. vLLM, Ollama, LM Studio, llama.cpp `llama-server`, TGI in OpenAI-compat mode). No multi-provider registry, no third-party SaaS providers.
> 3. **Embeddings dropped from v1.** Dedup uses URL canonicalization + simhash + Jaccard on token shingles — fully deterministic, zero LLM cost, no vector DB, no embedding model server required. Embeddings remain a documented optional upgrade for v2 if dedup quality proves insufficient.

---

## 1. Recommended Tech Stack

### 1.1 Licensing summary (enterprise-safe)

| Component | License | Commercial use | Royalty |
|---|---|---|---|
| Python 3.12 | PSF License | ✅ | None |
| SQLite | **Public domain** | ✅ | None |
| PostgreSQL (optional) | PostgreSQL License (BSD-style) | ✅ | None |
| FastAPI / Uvicorn / Starlette | MIT | ✅ | None |
| SQLAlchemy / Alembic | MIT | ✅ | None |
| LangChain / LangGraph | MIT | ✅ | None |
| Celery | BSD-3 | ✅ | None |
| Redis (≤ 7.2.4) / Valkey | BSD-3 / BSD-3 | ✅ | None — **use Valkey** to avoid Redis 7.4+ RSAL/SSPL concerns |
| Tailwind CSS | MIT | ✅ | None |
| HTMX / Alpine.js | BSD / MIT | ✅ | None |
| openpyxl | MIT | ✅ | None |
| trafilatura | Apache-2.0 | ✅ | None |
| Playwright (optional) | Apache-2.0 | ✅ | None |
| nginx | BSD-2 | ✅ | None |

> All third-party runtime components are permissively licensed and clear for enterprise deployment with no royalties or copyleft obligations.

### 1.2 Primary stack

| Concern | Choice | Why |
|---|---|---|
| Agent orchestration | **LangGraph + LangChain** | Required; cyclic flows + persistent state |
| LLM access | **`langchain-openai.ChatOpenAI`** pointed at a **self-hosted local LLM** via OpenAI-compatible `base_url` | Single endpoint, no SaaS, full data sovereignty |
| Embeddings | **None in v1** | Dedup is fully deterministic (URL + simhash + Jaccard); no embedding server required |
| Search | **Tavily Search API** (`langchain-tavily`) | Required |
| Scraping | **httpx + trafilatura**, **Playwright** only for JS-heavy sites | Best-in-class article extraction |
| Backend API | **FastAPI + Uvicorn** | Lightweight, async, OpenAPI built-in |
| Admin frontend | **Jinja2 + HTMX + Tailwind + Alpine.js** | Single-repo, no Node toolchain, server-rendered |
| **Database** | **SQLite** (WAL mode) | Public-domain, zero-admin, single file, perfect fit for this workload |
| Cache / broker | **Valkey** (Redis fork, BSD-3) | Tavily cache + Celery broker; avoids Redis 7.4+ license change |
| Job execution | **cron** (schedules) + **Celery** (workers) | Cron per spec, Celery for retries/concurrency |
| LangGraph persistence | **`langgraph-checkpoint-sqlite`** | Native SQLite checkpointer; resumable runs |
| Excel export | **openpyxl** | Stable, no native deps |
| Process supervision | **systemd** | Native to Ubuntu |
| Observability | **structlog** JSON logs + optional **Langfuse** (self-host) | Per-node agent traces |
| Auth (admin) | **fastapi-users** (JWT cookie) | Single-admin scope |
| Secrets | `pydantic-settings` + systemd `EnvironmentFile=` | Standard for Ubuntu services |

### 1.3 Why SQLite for an enterprise deployment

- **Public domain** — no license, no royalties, no attribution required (`https://sqlite.org/copyright.html`).
- **Most-deployed DB on Earth** — shipped in iOS, Android, Windows, every browser, Notion, etc. Battle-tested in enterprise.
- **Zero admin** — single file at `/var/lib/ainews/ainews.db`; backup is `cp` or `sqlite3 .backup`.
- **Excellent fit for this workload:** one writer (the worker), several readers (the API). With WAL mode + proper indexing, SQLite handles thousands of writes/sec — far above what a weekly/monthly report pipeline needs.
- **FTS supported** via the built-in `FTS5` virtual table for searching archived reports.
- **Resumable agent state** via `langgraph-checkpoint-sqlite`.

If the deployment ever grows to multi-writer high-concurrency (multiple workers writing constantly, multi-region replication), the migration to PostgreSQL is a one-time SQLAlchemy URL change plus an Alembic re-baseline; the application code does not change.

### 1.4 LLM configuration (single OpenAI-compatible local endpoint)

The system talks to **one** OpenAI-compatible HTTP endpoint that you operate yourself. Configuration lives in environment variables (overridable in the admin UI):

```
AINEWS_LLM_BASE_URL=http://llm.internal:8000/v1     # vLLM / Ollama / LM Studio / llama-server / TGI
AINEWS_LLM_API_KEY=sk-local-anything                # most local servers ignore this; still required by the client
AINEWS_LLM_MODEL=qwen2.5-32b-instruct               # default model name as exposed by your server
AINEWS_LLM_TEMPERATURE=0.2
AINEWS_LLM_MAX_TOKENS=2048
AINEWS_LLM_TIMEOUT=120
AINEWS_LLM_EXTRA_HEADERS={}                         # optional JSON, e.g. {"X-Tenant":"ainews"}
```

Resolution at runtime:

```diagram
  env / settings_kv / schedule.model_override
                 │
                 ▼
          ╭──────────────────╮
          │   llm_factory()  │
          ╰──────────────────╯
                 │
                 ▼
   ChatOpenAI(
     base_url   = AINEWS_LLM_BASE_URL,
     api_key    = AINEWS_LLM_API_KEY,
     model      = schedule.model_override or AINEWS_LLM_MODEL,
     default_headers = AINEWS_LLM_EXTRA_HEADERS,
     temperature = ..., max_tokens = ..., timeout = ...,
   )
```

Verified compatible local servers (any one is enough):

| Local server | `base_url` example | Notes |
|---|---|---|
| **vLLM** | `http://host:8000/v1` | High-throughput, OpenAI-compat by default |
| **Ollama** | `http://host:11434/v1` | Easiest to deploy, good for laptops/single GPU |
| **LM Studio** | `http://host:1234/v1` | Desktop UI, OpenAI-compat server |
| **llama.cpp `llama-server`** | `http://host:8080/v1` | Tiny footprint, CPU/GPU |
| **TGI** (HF Text Generation Inference) | `http://host:8080/v1` | OpenAI-compat mode |

Admin UI exposes a single **LLM Settings** page with a **Test connection** button that issues a 1-token completion to verify `base_url`, `api_key`, model name, and any custom headers. Per-schedule `model_override` lets you point a heavy weekly run at a larger model and a light hourly run at a smaller one — both still served by your same local stack.

> No third-party SaaS provider code, no embedding model server, no provider/profile tables.

### 1.5 Future v2 — local public embedding model (when/if needed)

If dedup quality after Phase 3 testing is insufficient, embeddings can be added without changing the architecture or introducing any third-party SaaS dependency. The same local-only, OpenAI-compatible pattern applies:

```
AINEWS_EMBED_BASE_URL=http://embed.internal:8001/v1   # second port on same host or separate service
AINEWS_EMBED_API_KEY=sk-local-anything
AINEWS_EMBED_MODEL=BAAI/bge-large-en-v1.5             # or whichever public model you load
AINEWS_EMBED_DIM=1024                                  # used by the SQL column / sqlite-vec table
```

Compatible local embedding servers (any one is enough):

| Local server | Notes |
|---|---|
| **HuggingFace TEI** (`text-embeddings-inference`) | Apache-2.0, OpenAI-compat `/v1/embeddings`, fastest single-purpose option, GPU or CPU |
| **vLLM** | Same binary as the chat LLM; supports embedding models via `--task embed` |
| **Ollama** | Apache-2.0, run `ollama pull nomic-embed-text` then `/v1/embeddings` works |
| **llama.cpp `llama-server`** | MIT, `--embeddings` flag, runs GGUF embedding models on CPU |
| **Infinity** (michaelfeil/infinity) | MIT, OpenAI-compat, optimized for embeddings + reranking |

Public embedding models with permissive licenses suitable for enterprise use:

| Model | License | Dim | Notes |
|---|---|---|---|
| **BAAI/bge-large-en-v1.5** | MIT | 1024 | Strong English baseline, MTEB top-tier |
| **BAAI/bge-m3** | MIT | 1024 | Multilingual + multi-granularity (dense/sparse/colbert) |
| **nomic-ai/nomic-embed-text-v1.5** | Apache-2.0 | 768 | Long-context (8k), Matryoshka |
| **intfloat/e5-large-v2** | MIT | 1024 | Robust, widely used |
| **Alibaba-NLP/gte-large-en-v1.5** | Apache-2.0 | 1024 | Long-context, strong on retrieval |
| **mixedbread-ai/mxbai-embed-large-v1** | Apache-2.0 | 1024 | High MTEB scores, Matryoshka |

Code change required when adopting: add `OpenAIEmbeddings(base_url=..., api_key=..., model=...)` to `llm_factory`, add an `articles.embedding BLOB` column (or a `vec0` virtual table from `sqlite-vec`, MIT/Apache-2.0), and extend the `Dedup` node with a cosine step after the existing simhash bucket. No other node changes; no schema rewrite; no infrastructure change beyond running one more local container.

---

## 2. System Architecture

### 2.1 High-level component diagram

```diagram
                    ╭───────────────────────────────╮
                    │      Admin Web UI (HTMX)      │
                    │  Sites · Schedules · Reports  │
                    │  LLM Settings · Logs · Trig.  │
                    ╰───────────────┬───────────────╯
                                    │ HTTP/JSON + HTMX
                                    ▼
   ╭──────────────────────────────────────────────────────────╮
   │                   FastAPI Backend                        │
   │ /api/sites /api/schedules /api/llm /api/runs             │
   │ /api/reports /api/logs /api/trigger /api/health          │
   ╰──────┬─────────────────────┬──────────────────────┬──────╯
          │ SQLAlchemy          │ enqueue              │ read
          ▼                     ▼                      ▼
   ╭──────────────╮     ╭──────────────╮       ╭──────────────╮
   │ SQLite (WAL) │◀────│   Valkey     │◀──────│ Reports FS   │
   │  + FTS5      │     │ broker+cache │       │ /var/lib/... │
   │  + LG ckpt   │     ╰──────┬───────╯       │  *.md *.xlsx │
   ╰──────┬───────╯            │               ╰──────────────╯
          │                    ▼
          │             ╭──────────────╮
          │             │ Celery Worker│
          │             │  (LangGraph) │
          │             ╰──────┬───────╯
          │                    │
          │                    ▼
          │   ╭───────────────────────────────────╮
          │   │     LangGraph Multi-Agent App     │
          │   │  Planner → Retriever → Scraper →  │
          │   │  Filter → Dedup → Synthesizer →   │
          │   │  Trender → Writer → Exporter      │
          │   ╰────────┬────────────────┬─────────╯
          │            │ Tavily         │ OpenAI-compatible HTTP
          │            ▼                ▼
          │     ╭─────────────╮  ╭──────────────────────────╮
          │     │ Tavily API  │  │  Self-hosted local LLM   │
          │     ╰─────────────╯  │  (vLLM/Ollama/LM Studio/ │
          │                      │   llama-server / TGI)    │
          │                      ╰──────────────────────────╯
          ▼
   ╭──────────────╮          ╭──────────────╮
   │ cron (Ubuntu)│─────────▶│ trigger CLI  │──▶ enqueue Celery
   ╰──────────────╯          ╰──────────────╯
```

Three systemd units own the runtime: `ainews-api.service` (FastAPI), `ainews-worker.service` (Celery), and an optional `ainews-beat.service`. Cron lives in `/etc/cron.d/ainews`.

### 2.2 Repository layout

```
ainews/
├── pyproject.toml
├── alembic/                        # DB migrations
├── deploy/
│   ├── systemd/
│   │   ├── ainews-api.service
│   │   ├── ainews-worker.service
│   │   └── ainews-beat.service
│   ├── cron/ainews                 # /etc/cron.d snippet
│   ├── nginx/ainews.conf
│   └── install.sh                  # idempotent installer
├── src/ainews/
│   ├── core/                       # config, logging, db, security, llm_factory
│   ├── models/                     # SQLAlchemy ORM
│   ├── schemas/                    # Pydantic
│   ├── api/
│   │   ├── routes/
│   │   └── templates/              # Jinja2 admin UI
│   ├── agents/
│   │   ├── state.py                # GraphState TypedDict
│   │   ├── graph.py                # build_graph()
│   │   ├── nodes/
│   │   ├── tools/                  # tavily, scraper, dedup
│   │   └── prompts/                # versioned templates
│   ├── llm/                        # llm_factory() + connection test
│   ├── tasks/                      # Celery tasks
│   ├── exporters/                  # markdown.py, xlsx.py
│   └── cli.py                      # typer
└── tests/
```

### 2.3 Database schema (SQLite, SQLAlchemy)

> SQLite-specific notes: enable `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`. JSON columns use SQLite's native JSON1.

```diagram
sites                          schedules                      runs
─────                          ─────────                      ────
id           PK                id              PK             id              PK (uuid text)
url          UNIQUE            name            TEXT           schedule_id     FK→schedules NULL
name         TEXT              cron_expr       TEXT           triggered_by    TEXT
category     TEXT              timeframe_days  INTEGER        status          TEXT
priority     INTEGER           site_filter     JSON           started_at      TEXT (ISO8601)
crawl_depth  INTEGER           topics          JSON           finished_at     TEXT
selectors    JSON              enabled         INTEGER        input_params    JSON
js_render    INTEGER (bool)    model_override  TEXT NULL      stats           JSON
enabled      INTEGER           created_at      TEXT           error           TEXT
created_at   TEXT                                             checkpoint_id   TEXT

articles                       reports                        run_logs
────────                       ───────                        ────────
id          PK                 id            PK               id          PK
run_id      FK→runs            run_id        FK→runs          run_id      FK→runs
url                            title         TEXT             node        TEXT
source      TEXT               summary_md    TEXT             level       TEXT
title       TEXT               full_md_path  TEXT             message     TEXT
published   TEXT               xlsx_path     TEXT             payload     JSON
fetched_at  TEXT               trends        JSON             ts          TEXT
content_md  TEXT               token_usage   JSON
relevance   REAL               created_at    TEXT
hash        TEXT (simhash)
shingles    JSON  (token-set for Jaccard)
status      TEXT
UNIQUE(run_id, url)

users                          settings_kv
─────                          ───────────
id, email, hashed_pw,          key PK, value JSON, updated_at
role, created_at               (LLM base_url/model overrides, retention, cost caps)
```

The `langgraph_checkpoints` table is created and managed by `langgraph-checkpoint-sqlite` in the same database file — gives a unified backup story.

Reports archive search: `CREATE VIRTUAL TABLE reports_fts USING fts5(title, summary_md, content=reports)` with sync triggers, enabling instant full-text search in the admin UI.

> No `providers`, `llm_profiles`, `article_vec`, or `secrets` tables. The single LLM endpoint and Tavily key live in `/etc/ainews/ainews.env` (root-owned, `0640`). If runtime override of the LLM URL/model is needed without a redeploy, those values can be stored as plain rows in `settings_kv` and picked up by `llm_factory()` on next worker tick.

### 2.4 LangGraph state & topology

`GraphState` (TypedDict):

```
run_id, params (timeframe, topics, sites, model_override)
raw_results: list[SearchHit]
fetched_articles: list[Article]
filtered_articles: list[Article]
clusters: list[Cluster]
summaries: list[Summary]
trends: list[Trend]
report_md: str
xlsx_path: str
errors: list[NodeError]
metrics: dict   # tokens, latency, cost_usd per node
```

Graph topology:

```diagram
              ╭─────────╮
              │  START  │
              ╰────┬────╯
                   ▼
              ╭─────────╮
              │ Planner │  ── decides queries + per-site plan
              ╰────┬────╯
                   ▼
            ╭──────────────╮
            │  Retriever   │ (Tavily fan-out, parallel via Send())
            ╰──────┬───────╯
                   ▼
            ╭──────────────╮
            │   Scraper    │ (fallback for low-content hits)
            ╰──────┬───────╯
                   ▼
            ╭──────────────╮       ⟲ conditional retry
            │  Filter/Rel. │ ──────── if kept < threshold ──▶ back to Planner
            ╰──────┬───────╯           (max N loops)
                   ▼
            ╭──────────────╮
            │   Dedup      │  (URL canon + simhash + sqlite-vec cosine)
            ╰──────┬───────╯
                   ▼
            ╭──────────────╮
            │ Synthesizer  │  (per-cluster summaries, parallel Send())
            ╰──────┬───────╯
                   ▼
            ╭──────────────╮
            │   Trender    │  (cross-cluster trend extraction)
            ╰──────┬───────╯
                   ▼
            ╭──────────────╮
            │   Writer     │  (assemble final Markdown report)
            ╰──────┬───────╯
                   ▼
            ╭──────────────╮
            │  Exporter    │  (xlsx + persist files + DB row)
            ╰──────┬───────╯
                   ▼
              ╭─────────╮
              │   END   │
              ╰─────────╯
```

`SqliteSaver` checkpointer makes every transition durable; failed runs are resumable via `graph.invoke(..., config={"configurable": {"thread_id": run.checkpoint_id}})`.

---

## 3. Agent Design

Each node is a small pure function `(state) -> partial_state`. All LLM calls go through `llm_factory(model_override=None)` which returns a `ChatOpenAI` bound to the single configured local endpoint, optionally swapping the model name for this run.

### Planner
- **Role:** Convert params (timeframe, topics, site list) into an executable retrieval plan.
- **Tools:** none (LLM + DB read).
- **Output:** `queries: list[{query, site, time_range, max_results}]`.
- **Prompt sketch:** "Given these target sites and topics, produce 1–3 Tavily queries per site optimized for the timeframe `{from}`–`{to}`. Prefer site-scoped queries (`site:domain`). Return JSON matching the schema."

### Retriever
- **Role:** Execute Tavily searches in parallel.
- **Tools:** `TavilySearch` with `include_domains`, `time_range`, `topic="news"`, `max_results`, `include_raw_content="markdown"`.
- **Parallelism:** `Send()` API, then aggregate.
- **No LLM calls.**

### Scraper
- **Role:** Fallback for hits whose `raw_content` is empty/short.
- **Tools:** async `httpx` (UA + robots check), `trafilatura.extract()`, `Playwright` only when site flagged `js_render=true`.
- **Guards:** per-domain token bucket in Valkey, robots.txt cache.

### Filter / Relevance
- **Role:** Score each article on `relevance ∈ [0,1]` and keep ≥ threshold.
- **Tools:** small LLM call with structured output via `llm_factory()`.
- **Prompt sketch:** "Score the relevance of this article to topics `{topics}` and timeframe `{from}`–`{to}`. Drop sponsored/listicle/tutorial-only content or items outside the window. Return `{score, keep, reason}`."
- **Conditional edge:** if kept < `min_kept` and loop_count < 2 → back to Planner with a "broaden queries" hint.

### Dedup
- **Role:** Cluster near-duplicates so each story appears once.
- **Tools (deterministic, no LLM, no embeddings):**
  1. **URL canonicalization** — strip UTM/ref params, normalize host case, drop AMP suffixes, resolve known redirect chains (e.g. `news.google.com/...`).
  2. **Simhash** (64-bit) on `title + first 500 chars` → bucket by Hamming distance ≤ 3.
  3. **Jaccard** on token shingles of title + lead (3-grams) within each bucket → merge if ≥ 0.6.
  4. Within each cluster, the article with the highest `priority * recency * content_length` score is the "primary".
- **Output:** `clusters` with a chosen "primary" article + variants.

### Synthesizer
- **Role:** Per-cluster `{headline, 2–4 bullet summary, why_it_matters, sources[]}`.
- **Parallelism:** `Send()` per cluster.
- **Prompt sketch:** "You are an AI industry analyst. Summarize this story cluster (multiple articles about the same event). Cite sources by index. Neutral tone, no fluff. Return JSON."

### Trender
- **Role:** Identify 3–7 cross-cutting trends across all summaries.
- **Tools:** single LLM call (or map-reduce if over the active model's context).
- **Output:** `trends: [{name, description, evidence_cluster_ids[]}]`.

### Writer
- **Role:** Assemble final Markdown: Executive Summary, Top Stories, Trends, By-Source Index, Methodology footer.
- **Tools:** Jinja2 (deterministic) + a final LLM polish pass for the Executive Summary only.

### Exporter
- **Role:** Write `.md` and `.xlsx` to `/var/lib/ainews/reports/{run_id}/`, register paths in `reports`.
- **Tools:** `openpyxl`. Sheets: `Summary`, `Stories`, `Sources`, `Trends`. No LLM.

### Cross-cutting policies
- **Errors:** every node wraps work in try/except → appends to `state.errors`, never raises. Conditional `degrade` path emits a partial report rather than failing.
- **Token & latency tracking:** per-node accumulation into `state.metrics` (input/output tokens, wall time). No `cost_usd` since the local LLM has no per-token billing; instead we cap `total_tokens` and `total_wall_seconds` per run.
- **LLM resilience:** `tenacity` retries with exponential backoff on connection errors, 5xx, and timeouts against the single local endpoint; after N failed attempts the node records the error and the `degrade` path takes over.

---

## 4. Admin Web Interface

| Route | Purpose |
|---|---|
| `GET /` | Dashboard: last 10 runs, success rate, next scheduled run, latest report links |
| `GET/POST /sites` | CRUD target sites (name, URL, category, priority, crawl_depth, js_render, enabled) |
| `GET/POST /schedules` | CRUD schedules (cron expr, timeframe, topics, site filter, optional `model_override`). "Validate cron" via `croniter`. |
| `GET/POST /llm` | Single **LLM Settings** page: view/override `base_url`, `api_key`, default `model`, `temperature`, `max_tokens`, `timeout`, `extra_headers`. **Test connection** button. |
| `GET /runs` | Paginated runs; click → timeline of node transitions, token usage, latency, errors |
| `GET /runs/{id}/report.md` | Render Markdown preview |
| `GET /runs/{id}/download.xlsx` | Stream xlsx |
| `POST /trigger` | Manual run form (schedule template or one-off params) → enqueues Celery task |
| `GET /logs` | Tail `run_logs` with filters; auto-refresh via HTMX SSE |
| `GET /settings` | Defaults, retention policy, cost caps |
| `GET /health` | DB / Valkey / Tavily / local LLM endpoint probes |

Auth: single admin seeded by `cli.py seed-admin`, JWT in HttpOnly cookie. CSRF tokens on state-changing forms.

---

## 5. Infrastructure Setup (Ubuntu 22.04 / 24.04)

### 5.1 System packages
```
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip \
                    sqlite3 \
                    valkey-server \
                    nginx build-essential libssl-dev curl git \
                    fonts-liberation
```
> If `valkey-server` is unavailable on your Ubuntu version, install Redis ≤ 7.2.4 from the Ubuntu LTS repo (still BSD-licensed) or build Valkey from source.

### 5.2 Application user & layout
```
sudo useradd -r -m -d /opt/ainews -s /bin/bash ainews
sudo -u ainews git clone <repo> /opt/ainews/app
sudo -u ainews python3.12 -m venv /opt/ainews/venv
/opt/ainews/venv/bin/pip install -e /opt/ainews/app
sudo install -d -o ainews -g ainews \
     /var/lib/ainews /var/lib/ainews/reports /var/log/ainews /etc/ainews
```

### 5.3 SQLite setup
- Single file: `/var/lib/ainews/ainews.db`, owned by `ainews:ainews`, mode `0640`.
- On first boot the app applies pragmas (`WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`, `temp_store=MEMORY`, `mmap_size=268435456`).
- Loads `sqlite-vec` extension at connection time.
- Backups: `sqlite3 /var/lib/ainews/ainews.db ".backup '/var/backups/ainews/ainews-$(date +%F).db'"` via daily cron; rotate with `find -mtime +30 -delete`.
- Optional: `litestream replicate` to S3/MinIO for point-in-time recovery (Apache-2.0 licensed, royalty-free).

### 5.4 Valkey
Bound to `127.0.0.1`, no password if local-only; set `requirepass` if exposed.

### 5.5 systemd units
- `ainews-api.service` → `ExecStart=/opt/ainews/venv/bin/uvicorn ainews.api.main:app --host 127.0.0.1 --port 8000 --workers 2`
- `ainews-worker.service` → `ExecStart=/opt/ainews/venv/bin/celery -A ainews.tasks.app worker -l info -Q default,scrape,llm --concurrency=4`
- `ainews-beat.service` (optional, alternative to cron)
- All units: `User=ainews`, `EnvironmentFile=/etc/ainews/ainews.env`, `Restart=on-failure`, `StandardOutput=journal`, `ProtectSystem=strict`, `ReadWritePaths=/var/lib/ainews /var/log/ainews`.

### 5.6 Cron (per spec)
`/etc/cron.d/ainews`:
```
# m h dom mon dow user command
0 7 * * 1 ainews /opt/ainews/venv/bin/ainews trigger-run --schedule weekly-ai-news >> /var/log/ainews/cron.log 2>&1
0 8 1 * * ainews /opt/ainews/venv/bin/ainews trigger-run --schedule monthly-trends >> /var/log/ainews/cron.log 2>&1
```
`ainews trigger-run` is a Typer command that resolves the schedule by name in the DB and enqueues a Celery task — keeps cron lines stable while config lives in the DB (admin-editable).

### 5.7 Nginx
TLS via certbot, reverse proxy `https://admin.example.com → 127.0.0.1:8000`, basic IP allowlist on `/api/`.

### 5.8 Backups & retention
- Daily SQLite `.backup` to `/var/backups/ainews/`, retained 30 days.
- Optional Litestream for continuous WAL replication.
- `reports/` retention policy (configurable in `settings_kv`), enforced by a Celery housekeeping task.

### 5.9 Observability
- Logs to journald (`journalctl -u ainews-worker`).
- Optional Langfuse self-hosted for agent traces; set `LANGFUSE_*` env vars and wrap LangChain with its callback handler.

### 5.10 Secrets
- The Tavily API key and the local LLM `api_key` (when set) live in `/etc/ainews/ainews.env`, owned `root:ainews 0640`, loaded by systemd via `EnvironmentFile=`.
- No secrets are written to the database in v1.
- The LLM Settings admin page can override the in-DB defaults (`settings_kv`) but the API key field is write-only — once saved it is masked (`••••••`) in the UI; rotation replaces the value.

---

## 6. Implementation Phases (Roadmap)

### Phase 0 — Foundations ✅ (completed 2026-05-07)
- `pyproject.toml` (uv + hatchling, src/ layout), `uv.lock`, pre-commit (ruff + mypy), `Makefile` with 8 targets.
- 13-package `src/ainews/` directory tree, `deploy/` skeleton (systemd/cron/nginx/install.sh), `alembic/` placeholder, `var/.gitkeep`.
- `pydantic-settings` `Settings` class with all `AINEWS_*` env vars; `.env.example` documenting every variable.
- `structlog` JSON logging via `setup_logging()`.
- Typer CLI: `ainews version`, stub sub-apps `llm`, `run`, `seed`.
- 27 tests, 100% coverage on implemented modules, all lints pass (ruff + mypy strict).
- **Exit:** `ainews --help` runs ✅ | `make lint && make typecheck && make test` all green ✅

### Phase 1 — Data layer ✅ (completed 2026-05-07)
- SQLAlchemy 2.0 ORM models for all 8 tables (Site, Schedule, Run, Article, Report, RunLog, User, SettingsKV) with JSON columns, indexes, and FK constraints. Shared `DeclarativeBase` in `ainews.models.base`.
- SQLite pragma event listener: WAL, synchronous=NORMAL, foreign_keys=ON, busy_timeout=5000, temp_store=MEMORY, mmap_size=256 MiB applied on every new DBAPI connection.
- `get_db_session()` context manager with commit/rollback/close lifecycle; `StaticPool` for in-memory SQLite.
- Alembic `env.py` configured with `Base.metadata` and pragma-aware engine factory; `render_as_batch=True` for SQLite ALTER TABLE compatibility.
- Baseline migration (`dc09fc4f2f6d`): all 8 tables + indexes + `reports_fts` FTS5 virtual table + INSERT/UPDATE/DELETE sync triggers.
- Idempotent `ainews seed` command: 10 starter sites + 1 weekly schedule (`weekly-ai-news`, cron `0 7 * * 1`); upserts by URL/name.
- 124 tests, 99% line coverage on all new modules.
- **Exit:** `alembic upgrade head` + `ainews seed` work end-to-end ✅ | `make lint && make typecheck && make test` all green ✅

### Phase 2 — LLM client & tools ✅ (completed 2026-05-08)
- `llm/factory.py`: build `ChatOpenAI(base_url, api_key, model, default_headers, temperature, max_tokens, timeout)` from env + `settings_kv` overrides + optional per-run `model_override`.
- `llm/test.py`: 1-token completion against the configured local endpoint; surfaced as `ainews llm test` and the admin "Test connection" button.
- Wrap `TavilySearch` with project defaults and a Valkey cache (`hashlib(query+params) → JSON`, TTL 6h).
- `scraper.py`: async httpx, robots check, trafilatura, optional Playwright.
- `dedup.py`: URL canonicalize, 64-bit simhash, Jaccard on 3-gram shingles. No embeddings.
- Tests with VCR cassettes for Tavily + recorded HTML for scraper + a fake OpenAI-compatible chat server (`respx` or a local Ollama in CI) for LLM.
- **Exit:** `pytest tests/tools/` green; `ainews llm test` succeeds against your local server; `ainews fetch --site openai.com --days 7` prints clean articles; `ainews dedup --run-id ...` clusters a fixture corpus correctly.

### Phase 3 — LangGraph workflow (2–3 days)
- `state.py`, each node in `agents/nodes/`, prompts as Jinja templates in `agents/prompts/`.
- Wire `StateGraph`, conditional edges, `Send()` parallelism, `SqliteSaver` checkpointer.
- Optional Langfuse callback wired through.
- Integration test: full graph on a tiny fixture (3 sites, 3-day window) using your local LLM endpoint (Ollama or LM Studio is enough for CI).
- **Exit:** `ainews run --topic LLM --days 7 --limit 20` produces a Markdown file locally.

### Phase 4 — Exporters & report templates (½–1 day)
- Jinja2 Markdown template (Executive Summary, Top Stories, Trends, Sources, Methodology).
- `openpyxl` workbook builder; freeze panes, autosize, hyperlinks back to source URLs.
- **Exit:** outputs validated against a schema; xlsx opens in Excel/LibreOffice.

### Phase 5 — Backend API + Celery (1–2 days)
- FastAPI app, routers per resource, dependency-injected DB session.
- Celery app with queues (`scrape`, `llm`, `default`); task `run_pipeline(run_id)` hydrates params and invokes the graph with the run's `thread_id` for resumability.
- `POST /api/trigger` enqueues; `cli.py trigger-run` shares the same path.
- **Exit:** `curl -XPOST /api/trigger` produces a run row that completes via the worker; `/api/runs/{id}` shows status transitions.

### Phase 6 — Admin UI (2–3 days)
- Jinja2 base + Tailwind (standalone CLI, no Node) + HTMX + Alpine.
- Pages per §4. Pydantic form validation; flash messages via cookie.
- LLM Settings page: form for `base_url`, `api_key`, `model`, `temperature`, `max_tokens`, `timeout`, `extra_headers`, **Test connection**.
- SSE endpoint `/api/runs/{id}/events` streaming `run_logs` (polling fallback since SQLite has no LISTEN/NOTIFY; trade-off accepted).
- Auth via fastapi-users JWT cookie; `seed-admin` CLI.
- **Exit:** Admin can add a site, edit LLM settings + Test connection, schedule a run, trigger manually, and watch logs live.

### Phase 7 — Ubuntu deployment (1 day)
- systemd units, cron file, nginx config, certbot.
- Idempotent `deploy/install.sh` covering §5.1–§5.10.
- Smoke test on a fresh Ubuntu VM (Multipass / EC2 t3.small).
- **Exit:** Cold-boot install completes; weekly cron fires; admin UI reachable over HTTPS.

### Phase 8 — Hardening & QA (1–2 days)
- Per-domain scraper rate limits; Tavily monthly-quota guard; concurrency cap on calls into the local LLM (avoid saturating your GPU).
- Hard caps per run: `max_total_tokens`, `max_wall_seconds`, `max_articles`. Configurable in `settings_kv`.
- Retry/backoff with `tenacity` for transient LLM and Tavily errors against the single local endpoint.
- Backup cron + Litestream (optional); log rotation `/etc/logrotate.d/ainews`.
- Security: CSP, HSTS, file modes audit, env-file ownership audit, masking of API key in logs.
- E2E test: full nightly run on a staging schedule, diff against a golden report.
- **Exit:** Full week of cron in staging without manual intervention.

### Phase 9 — Docs & handover (½ day)
- `README.md` quickstart, `docs/architecture.md` (this plan), `docs/operations.md` (runbook: add a site, switch the local LLM endpoint or model, replay a failed run, rotate the API key, restore from backup).
- Short demo recording of the admin UI.

**Total v1 estimate:** ~10–14 focused engineering days.

---

## 7. Key Decisions Worth Confirming Before Build

1. **Frontend:** HTMX + Jinja2 (recommended, lightest) vs. Next.js (richer SPA UX).
2. **Scheduler:** **cron** (per spec) vs. Celery beat. Recommended: cron triggers a Typer command that enqueues Celery tasks.
3. **Local LLM server:** which one will host your model in production? (vLLM / Ollama / LM Studio / llama.cpp / TGI). This is purely operational — the application code is identical for all of them — but it tells us which one to use in CI integration tests and which model name to seed as the default.
4. **Default model name** to seed (e.g. `qwen2.5-32b-instruct`, `llama3.1-70b-instruct`, `mistral-small-3.1`). Affects prompt token budgets and the `max_tokens` default.
5. **Tracing:** Langfuse self-hosted (recommended for enterprise — no data leaves your network) vs. none.
6. **Cache/broker:** **Valkey** (recommended, BSD-3) vs. Redis ≤ 7.2.4 (also BSD-3) vs. Redis 7.4+ (RSAL/SSPL — avoid for enterprise).
7. **Dedup quality bar:** confirm "URL + simhash + Jaccard" is acceptable for v1. If during Phase 3 testing you observe paraphrased duplicates leaking through (different outlets writing very different prose about the same event), we add an embeddings step in v2 — same single-endpoint pattern, just call `/v1/embeddings` on your local server, no schema migration needed beyond an optional `articles.embedding` blob column.

Once you confirm #1, #3, #4, #5, #6, I will start Phase 0: scaffold the repo, `pyproject.toml`, Alembic baseline against SQLite, the `llm_factory` + `ainews llm test` CLI against your local endpoint, and the systemd/cron skeletons — then move into Phase 1.
