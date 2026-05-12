# Product Guide — AI News & Trends Report

> Last refreshed: 2026-05-12T22:51:00+07:00

## Vision

An automated, self-hosted intelligence system that gathers, processes, and synthesizes AI industry news into structured, actionable reports — delivered on a configurable schedule with zero manual intervention after setup.

## Problem Statement

Keeping up with the rapidly evolving AI landscape requires monitoring dozens of sources daily. Manual curation is time-consuming, inconsistent, and prone to blind spots. Teams and decision-makers need a reliable, automated pipeline that surfaces what matters — deduplicated, summarized, and trend-analyzed — without relying on third-party SaaS platforms or surrendering data sovereignty.

## Target Users

| Persona | Role | Needs |
|---------|------|-------|
| **System Admin** | Technical operator who deploys and maintains the system | Simple Ubuntu deployment, clear runbooks, reliable cron-driven automation |
| **Report Consumer** | Analyst or team member reading weekly/monthly reports | Clean Markdown summaries, Excel exports, trend identification |
| **Executive Stakeholder** | Decision-maker reviewing high-level AI trends | Executive summaries, cross-cutting trend analysis, minimal noise |

## Core Capabilities

1. **Multi-Agent News Pipeline** — LangGraph orchestration of 9 specialized agents (Planner → Retriever → Scraper → Filter → Dedup → Synthesizer → Trender → Writer → Exporter) with checkpoint-based resumability
2. **Intelligent Search & Scraping** — Tavily-powered search with 3-tier content extraction fallback: Tavily raw_content → Tavily Extract API (cloud) → httpx/trafilatura direct scrape; Playwright for JS-heavy sites
3. **Deterministic Deduplication** — URL canonicalization + simhash + Jaccard similarity (no embeddings required in v1)
4. **LLM-Powered Analysis** — Relevance scoring, per-cluster summarization, cross-cutting trend extraction via a single self-hosted OpenAI-compatible endpoint
5. **Structured Report Generation** — Markdown + Excel (.xlsx) output with Executive Summary, Stories (with inline sources), Trends, and Methodology sections (3 sheets); configurable `report_max_sources` cap
6. **Admin Web Interface** — Jinja2/HTMX dashboard for managing sites, schedules (visual cron builder), LLM settings, admin users (CRUD), triggering manual runs, real-time pipeline monitoring with node steppers and live logging, raw Celery worker output tab, and report preview/download capabilities
7. **Dynamic Schedule Automation** — Celery Beat tick evaluates DB-stored schedules with per-schedule IANA timezone support, smart planner toggle, and automatic cron-matched run triggering
8. **Run Status Granularity** — Distinguishes `completed`, `completed_with_errors`, and `failed` states for accurate pipeline outcome reporting

## Non-Functional Requirements

- **Data Sovereignty** — All processing on self-hosted infrastructure; no data leaves the network (LLM is local, no third-party SaaS for inference)
- **Enterprise-Safe Licensing** — Every runtime component is permissively licensed (MIT/Apache-2.0/BSD/public domain); zero royalties or copyleft
- **Zero-Admin Database** — SQLite with WAL mode; single-file backup, no DBA required
- **Resumability** — LangGraph checkpointer enables failed runs to resume from last successful node
- **Observability** — Structured JSON logs (structlog) + optional Langfuse self-hosted tracing

## Success Metrics

- Reports generated on schedule without manual intervention
- Deduplication accuracy ≥ 95% (measured by manual spot-check of clusters)
- End-to-end pipeline completes within configurable token/time caps
- Admin can add sites, adjust LLM settings, and trigger runs without CLI access

## Scope Boundaries

### In Scope (v1)
- Single OpenAI-compatible local LLM endpoint
- SQLite database (WAL mode + FTS5)
- Deterministic dedup (URL + simhash + Jaccard)
- Markdown + Excel report output with configurable source cap (3-sheet XLSX: Summary, Stories+Sources, Trends)
- Ubuntu 22.04/24.04 deployment via systemd (3 units: ainews-api, ainews-worker, ainews-beat) + deploy scripts (install.sh, update.sh, stop.sh)
- Multi-admin auth (JWT cookie) with admin user CRUD (create/edit/delete) via web UI
- Dynamic Celery Beat scheduling with per-schedule timezone and smart planner toggle
- ANSI-stripped raw worker log viewer
- Worker startup diagnostics via Celery `worker_ready` signal

### Out of Scope (v2+)
- Embedding-based semantic dedup (upgrade path documented)
- Role-based access control (current: all admins are equal)
- PostgreSQL migration (documented as one-line URL change)
- Real-time streaming reports
- Mobile-optimized UI
- Multi-provider LLM routing

## Key Decisions (from PLAN.md §7)

| Decision | Status | Choice |
|----------|--------|--------|
| Frontend approach | Decided | HTMX + Jinja2 (server-rendered, no Node toolchain) |
| Scheduler | Decided | Celery Beat tick evaluates DB schedules (replaced static cron) |
| Cache/broker | Decided | Valkey (BSD-3) |
| Dedup strategy | Decided (v1) | URL + simhash + Jaccard (deterministic, no embeddings) |
| Local LLM server | Decided | Proxy endpoint (aresproxy.me) |
| Default model | Decided | gemini-3-flash-preview |
| Tracing | Decided | None |
