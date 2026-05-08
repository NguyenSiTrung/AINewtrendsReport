# Tech Stack — AI News & Trends Report

## Language & Runtime

| Component | Version | License |
|-----------|---------|---------|
| Python | 3.12 | PSF License |

## Agent Orchestration

| Component | Purpose | License |
|-----------|---------|---------|
| LangGraph | Multi-agent workflow engine with cyclic flows + persistent state | MIT |
| LangChain | Agent primitives, tool wrappers, prompt templates | MIT |
| langgraph-checkpoint-sqlite | Durable state checkpointing in SQLite | MIT |

## LLM Access

| Component | Purpose | License |
|-----------|---------|---------|
| langchain-openai (`ChatOpenAI`) | Single OpenAI-compatible client | MIT |
| Self-hosted local LLM server | vLLM / Ollama / LM Studio / llama-server / TGI | Varies (all permissive) |

> **Configuration:** Single endpoint via `AINEWS_LLM_BASE_URL` env var. No third-party SaaS. Full data sovereignty.

## Search & Scraping

| Component | Purpose | License |
|-----------|---------|---------|
| Tavily Search API | Web search with `include_raw_content` | Commercial API (key required) |
| langchain-tavily | Tavily integration for LangChain | MIT |
| httpx | Async HTTP client for scraping fallback | BSD-3 |
| trafilatura | Article content extraction from HTML | Apache-2.0 |
| Playwright | JS-heavy site rendering (optional, per-site flag) | Apache-2.0 |

## Backend & API

| Component | Purpose | License |
|-----------|---------|---------|
| FastAPI | REST API framework | MIT |
| Uvicorn | ASGI server | BSD-3 |
| Starlette | ASGI toolkit (FastAPI dependency) | BSD-3 |
| pyjwt | JSON Web Token generation/validation | MIT |
| bcrypt | Password hashing | Apache-2.0 |

## Task Queue & Caching

| Component | Purpose | License |
|-----------|---------|---------|
| Celery | Distributed task queue (workers for scrape/llm/default queues) | BSD-3 |
| Valkey | Message broker + Tavily response cache | BSD-3 |

## Database

| Component | Purpose | License |
|-----------|---------|---------|
| SQLite | Primary database (WAL mode, FTS5, JSON1) | **Public domain** |
| SQLAlchemy | ORM | MIT |
| Alembic | Schema migrations | MIT |

> **Configuration:** Single file at `/var/lib/ainews/ainews.db`. Pragmas: `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`.

## Admin Frontend

| Component | Purpose | License |
|-----------|---------|---------|
| Jinja2 | Server-side HTML templating | BSD-3 |
| HTMX | Declarative AJAX/SSE (no JS framework) | BSD-2 |
| Tailwind CSS | Utility-first CSS (standalone CLI, no Node) | MIT |
| Alpine.js | Lightweight reactivity for interactive UI elements | MIT |

> **No Node.js toolchain required.** Tailwind runs via standalone CLI binary.

## Export & Reporting

| Component | Purpose | License |
|-----------|---------|---------|
| openpyxl | Excel (.xlsx) workbook generation | MIT |
| Jinja2 | Markdown report templating | BSD-3 |

## Observability & Logging

| Component | Purpose | License |
|-----------|---------|---------|
| structlog | Structured JSON logging | MIT |
| Langfuse (optional) | LLM trace observability (self-hosted) | MIT |

## Infrastructure & Deployment

| Component | Purpose | License |
|-----------|---------|---------|
| Ubuntu 22.04 / 24.04 | Target OS | GPL (OS level) |
| systemd | Process supervision (3 units: api, worker, beat) | LGPL |
| cron | Schedule-based run triggering | OS built-in |

## Dev Tooling

| Component | Purpose | License |
|-----------|---------|---------|
| ruff | Linter + formatter | MIT |
| mypy | Static type checking | MIT |
| pytest | Test framework | MIT |
| pre-commit | Git hook management | MIT |
| tenacity | Retry/backoff for LLM + API calls | Apache-2.0 |

## Deduplication (v1 — Deterministic, No Embeddings)

| Technique | Purpose |
|-----------|---------|
| URL canonicalization | Strip UTM/ref params, normalize hosts, resolve redirects |
| Simhash (64-bit) | Bucket articles by Hamming distance ≤ 3 |
| Jaccard similarity | Token 3-gram shingle comparison within buckets (threshold ≥ 0.6) |

> **v2 upgrade path:** Add local embedding model via `OpenAIEmbeddings(base_url=...)` + `sqlite-vec` cosine similarity if deterministic dedup proves insufficient.

## Licensing Summary

All runtime components are **permissively licensed** (MIT / Apache-2.0 / BSD / public domain). Zero royalties, zero copyleft obligations. Enterprise-safe for commercial deployment.
