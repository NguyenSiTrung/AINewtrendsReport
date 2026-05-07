# AI News & Trends Report

A multi-agent system that automatically gathers, processes, and synthesizes AI news and trends from a configurable list of sources.

## Status

🚧 **Planning phase** — implementation has not started.

The full architecture and phased development plan lives in [`PLAN.md`](./PLAN.md).

## Highlights

- **Orchestration:** LangGraph + LangChain (multi-agent: Planner → Retriever → Scraper → Filter → Dedup → Synthesizer → Trender → Writer → Exporter)
- **Search:** Tavily Search API
- **LLM:** single OpenAI-compatible endpoint pointed at a self-hosted local LLM server (vLLM / Ollama / LM Studio / llama.cpp / TGI)
- **Database:** SQLite (public domain) with WAL mode + FTS5
- **Backend:** FastAPI + Celery (Valkey broker)
- **Admin UI:** Jinja2 + HTMX + Tailwind + Alpine.js
- **Scheduling:** Ubuntu cron + manual triggers
- **Output:** Markdown reports + Excel (.xlsx) export
- **Deployment:** Ubuntu 22.04/24.04 via systemd + nginx

All runtime components are permissively licensed (MIT / Apache-2.0 / BSD / public domain) — royalty-free and enterprise-safe.

## Next steps

See [`PLAN.md`](./PLAN.md) §6 — Implementation Phases. Phase 0 (repo scaffolding, `pyproject.toml`, `llm_factory`, systemd/cron skeletons) starts after the open decisions in §7 are confirmed.
