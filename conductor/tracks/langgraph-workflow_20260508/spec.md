# Spec: LangGraph Workflow

## Overview

Implement the core LangGraph multi-agent pipeline that orchestrates the full news-gathering and report-generation workflow. This phase wires together 8 specialized node functions (Planner, Retriever, Scraper, Filter, Dedup, Synthesizer, Trender, Writer) into a `StateGraph` with conditional edges, `Send()` parallelism, `SqliteSaver` checkpointing, and multi-layer error resilience. It produces a complete Markdown report from a set of input parameters (timeframe, topics, site list).

This phase builds on:
- **Phase 1 (Data Layer):** ORM models, DB session, Alembic migrations
- **Phase 2 (LLM Client & Tools):** `llm_factory()`, Tavily search wrapper, async scraper, dedup engine

## Functional Requirements

### FR-1: GraphState definition (`agents/state.py`)
- `TypedDict` with fields: `run_id`, `params`, `queries`, `raw_results`, `fetched_articles`, `filtered_articles`, `clusters`, `summaries`, `trends`, `report_md`, `errors`, `metrics`, `loop_count`
- All list fields default to empty lists; `metrics` defaults to empty dict

### FR-2: Node implementations (`agents/nodes/`)
Each node is a pure function `(state: GraphState) -> dict` returning a partial state update.

- **Planner** — LLM call via `llm_factory()` to convert `params` (timeframe, topics, sites) into a list of Tavily queries. Structured JSON output.
- **Retriever** — Fan-out via `Send()` per query; each sub-invocation calls the Tavily search wrapper (from Phase 2); results aggregated into `raw_results`.
- **Scraper** — Iterates `raw_results` with missing/short content; calls the async scraper (Phase 2 tool) to fill in `content_md`. Skips failures gracefully.
- **Filter** — LLM call per article to score `relevance ∈ [0,1]`; keeps articles ≥ threshold (configurable, default 0.5). Outputs `filtered_articles`.
- **Dedup** — Calls the dedup engine (from Phase 2) on `filtered_articles`. Outputs `clusters` with primary article + variants.
- **Synthesizer** — Fan-out via `Send()` per cluster; LLM call to produce `{headline, bullets, why_it_matters, sources[]}` per cluster. Results aggregated into `summaries`.
- **Trender** — Single LLM call across all summaries to identify 3–7 cross-cutting trends. Outputs `trends`.
- **Writer** — Jinja2 template assembly of final Markdown report (Executive Summary, Top Stories, Trends, Source Index, Methodology). LLM polish pass on Executive Summary only. Outputs `report_md`.

### FR-3: Prompt templates (`agents/prompts/`)
- One Jinja2 `.j2` file per LLM-calling node: `planner.j2`, `filter.j2`, `synthesizer.j2`, `trender.j2`, `writer_executive.j2`
- Templates receive context variables from node functions
- Version-controlled, diffable

### FR-4: Graph wiring (`agents/graph.py`)
- `StateGraph(GraphState)` with nodes registered and edges defined
- **Conditional edge:** Filter → Planner (retry) when `len(filtered) < min_kept` and `loop_count < 2`; otherwise Filter → Dedup
- **`Send()` parallelism:** Retriever (per-query fan-out) and Synthesizer (per-cluster fan-out)
- **Linear edges:** Planner → Retriever → Scraper → Filter, Dedup → Synthesizer → Trender → Writer → END
- `build_graph()` function returning a compiled graph

### FR-5: Checkpointing
- `SqliteSaver` (from `langgraph-checkpoint-sqlite`) wired into graph compilation
- Each run uses `thread_id = run_id` for resumability
- Failed runs can be resumed from last successful node transition

### FR-6: Error resilience (5 layers)
1. **Tenacity retries** — exponential backoff on LLM connection errors, 5xx, timeouts (3 attempts, 2s/4s/8s)
2. **Node-level try/except** — every node catches exceptions, appends `NodeError(node, message, traceback)` to `state.errors`, returns partial state
3. **Graceful skip** — if Send() sub-invocations fail partially, continue with successful results
4. **Degrade path** — conditional edge after Filter and Synthesizer: if `len(errors) > error_threshold`, route to Writer with available data + degradation notice in report
5. **Per-node metrics** — each node records `{node_name: {input_tokens, output_tokens, wall_seconds}}` in `state.metrics`

### FR-7: CLI integration
- Extend `ainews run` CLI command to invoke the graph: `ainews run --topic LLM --days 7 --limit 20`
- Hydrates params from CLI args, creates a `Run` DB row, invokes graph, persists report

## Non-Functional Requirements

- **NFR-1:** All LLM calls go through `llm_factory()` — no direct `ChatOpenAI` instantiation in nodes
- **NFR-2:** Nodes are stateless pure functions — all state flows through `GraphState`
- **NFR-3:** Token caps respected — `max_total_tokens` and `max_wall_seconds` checked between nodes
- **NFR-4:** Optional Langfuse callback wired through `llm_factory()` when `LANGFUSE_*` env vars are set

## Acceptance Criteria

- [ ] `GraphState` TypedDict defined with all required fields
- [ ] All 8 nodes implemented as pure functions in `agents/nodes/`
- [ ] 5 Jinja2 prompt templates in `agents/prompts/`
- [ ] `build_graph()` returns a compiled `StateGraph` with correct topology
- [ ] Conditional retry edge (Filter → Planner) works with `max_loops=2`
- [ ] `Send()` parallelism works for Retriever and Synthesizer
- [ ] `SqliteSaver` checkpointer enables run resumability
- [ ] All 5 error resilience layers functional
- [ ] Per-node metrics tracked in `state.metrics`
- [ ] `ainews run --topic LLM --days 7 --limit 20` produces a Markdown report
- [ ] Integration test passes with fixture data (3 sites, 3-day window) against a mock LLM
- [ ] Unit tests for each node with ≥ 80% coverage
- [ ] `make lint && make typecheck && make test` all green

## Out of Scope

- Exporter node (xlsx + file persistence) — deferred to Phase 4
- FastAPI endpoints — deferred to Phase 5
- Admin UI — deferred to Phase 6
- Langfuse tracing setup — wiring point only, configuration is Phase 8
- Embedding-based dedup — v2 upgrade path
