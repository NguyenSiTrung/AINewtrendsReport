# Product Guide — AI News & Trends Report

> Last refreshed: 2026-05-08T23:38:00+07:00

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
2. **Intelligent Search & Scraping** — Tavily-powered search with httpx/trafilatura fallback scraping; Playwright for JS-heavy sites
3. **Deterministic Deduplication** — URL canonicalization + simhash + Jaccard similarity (no embeddings required in v1)
4. **LLM-Powered Analysis** — Relevance scoring, per-cluster summarization, cross-cutting trend extraction via a single self-hosted OpenAI-compatible endpoint
5. **Structured Report Generation** — Markdown + Excel (.xlsx) output with Executive Summary, Top Stories, Trends, Source Index, and Methodology sections
6. **Admin Web Interface** — Jinja2/HTMX dashboard for managing sites, schedules, LLM settings, triggering manual runs, real-time pipeline monitoring with node steppers and live logging, and report preview/download capabilities
7. **Scheduled Automation** — Ubuntu cron + Celery workers for weekly/monthly report generation with retry/backoff resilience

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
- Markdown + Excel report output
- Ubuntu 22.04/24.04 deployment via systemd
- Single-admin auth (JWT cookie)

### Out of Scope (v2+)
- Embedding-based semantic dedup (upgrade path documented)
- Multi-user role-based access
- PostgreSQL migration (documented as one-line URL change)
- Real-time streaming reports
- Mobile-optimized UI
- Multi-provider LLM routing

## Key Decisions (from PLAN.md §7)

| Decision | Status | Choice |
|----------|--------|--------|
| Frontend approach | Decided | HTMX + Jinja2 (server-rendered, no Node toolchain) |
| Scheduler | Decided | cron triggers Celery tasks |
| Cache/broker | Decided | Valkey (BSD-3) |
| Dedup strategy | Decided (v1) | URL + simhash + Jaccard (deterministic, no embeddings) |
| Local LLM server | Decided | Proxy endpoint (aresproxy.me) |
| Default model | Decided | gemini-3-flash-preview |
| Tracing | Decided | None |
