# Plan: LangGraph Workflow

## Phase 1: State & Prompt Infrastructure

- [x] Task 1: Define GraphState TypedDict and supporting types ✅ 93c957a
  - [x] Write tests for GraphState field defaults and type annotations
  - [x] Create `agents/state.py` with `GraphState(TypedDict)` — all fields from spec (run_id, params, queries, raw_results, fetched_articles, filtered_articles, clusters, summaries, trends, report_md, errors, metrics, loop_count)
  - [x] Create `NodeError` dataclass (node, message, traceback, timestamp)
  - [x] Create supporting types: `SearchHit`, `Article`, `Cluster`, `Summary`, `Trend` as TypedDicts
  - [x] Verify types pass mypy strict

- [x] Task 2: Create prompt template loader and Jinja2 templates ✅
  - [x] Write tests for template loading (file not found, variable rendering, missing vars)
  - [x] Create `agents/prompts/loader.py` with `load_prompt(template_name, **context) -> str`
  - [x] Create `planner.j2` — query generation prompt with topics, sites, timeframe vars
  - [x] Create `filter.j2` — relevance scoring prompt with article content, topics vars
  - [x] Create `synthesizer.j2` — cluster summarization prompt with articles, source refs
  - [x] Create `trender.j2` — trend extraction prompt with all summaries
  - [x] Create `writer_executive.j2` — executive summary polish prompt

- [x] Task 3: Create error resilience utilities ✅ 82c488f
  - [x] Write tests for retry decorator, metrics accumulator, degrade checker
  - [x] Create `agents/resilience.py` with `@node_resilient` decorator (try/except → append NodeError to state.errors)
  - [x] Add `with_retries()` wrapper using tenacity (3 attempts, exponential 2s/4s/8s, retry on ConnectionError/5xx/timeout)
  - [x] Add `track_metrics(node_name, state, start_time, token_usage)` utility for per-node metrics accumulation
  - [x] Add `should_degrade(state, error_threshold) -> bool` checker

- [x] Task: Conductor - User Manual Verification 'State & Prompt Infrastructure' ✅

## Phase 2: Node Implementations
<!-- execution: parallel -->

- [x] Task 1: Implement Planner node ✅ 31fa82d
  <!-- files: src/ainews/agents/nodes/planner.py, tests/agents/nodes/test_planner.py -->
  - [x] Write unit tests with mocked LLM (structured JSON output, error cases)
  - [x] Create `agents/nodes/planner.py` — LLM call via `llm_factory()`, renders `planner.j2`, parses JSON output into `queries` list
  - [x] Handle malformed LLM JSON output gracefully (retry parse, fallback)
  - [x] Apply `@node_resilient` decorator + metrics tracking

- [x] Task 2: Implement Retriever node with Send() fan-out ✅
  <!-- files: src/ainews/agents/nodes/retriever.py, tests/agents/nodes/test_retriever.py -->
  <!-- depends: task1 -->
  - [x] Write unit tests for fan-out logic, result aggregation, partial failure handling
  - [x] Create `agents/nodes/retriever.py` — `retrieve_dispatch()` returns list of `Send("retrieve_one", query)` per query
  - [x] Create `retrieve_one()` sub-node — calls Tavily search wrapper (Phase 2 tool), returns `raw_results` partial
  - [x] Aggregation merges all `raw_results` from parallel sub-invocations

- [x] Task 3: Implement Scraper node ✅
  <!-- files: src/ainews/agents/nodes/scraper.py, tests/agents/nodes/test_scraper.py -->
  - [x] Write unit tests with mocked httpx responses (content fill, skip on failure, js_render flag)
  - [x] Create `agents/nodes/scraper.py` — iterates `raw_results`, calls async scraper (Phase 2 tool) for items with missing/short content
  - [x] Graceful skip on individual scrape failures (append to errors, continue)
  - [x] Apply `@node_resilient` decorator + metrics tracking

- [x] Task 4: Implement Filter node ✅
  <!-- files: src/ainews/agents/nodes/filter.py, tests/agents/nodes/test_filter.py -->
  - [x] Write unit tests with mocked LLM (scoring, threshold filtering, retry loop trigger)
  - [x] Create `agents/nodes/filter.py` — LLM call per article via `filter.j2`, structured output `{score, keep, reason}`
  - [x] Apply configurable threshold (default 0.5), output `filtered_articles`
  - [x] Increment `loop_count` in state; return routing signal for conditional edge

- [x] Task 5: Implement Dedup node ✅
  <!-- files: src/ainews/agents/nodes/dedup.py, tests/agents/nodes/test_dedup.py -->
  - [x] Write unit tests with fixture articles (URL canon, simhash bucketing, Jaccard merge)
  - [x] Create `agents/nodes/dedup.py` — wraps Phase 2 dedup engine, transforms `filtered_articles` into `clusters`
  - [x] Each cluster has a primary article (highest priority × recency × length) + variants
  - [x] Apply `@node_resilient` decorator + metrics tracking

- [x] Task 6: Implement Synthesizer node with Send() fan-out ✅
  <!-- files: src/ainews/agents/nodes/synthesizer.py, tests/agents/nodes/test_synthesizer.py -->
  <!-- depends: task1 -->
  - [x] Write unit tests with mocked LLM (per-cluster summary, partial failure, aggregation)
  - [x] Create `agents/nodes/synthesizer.py` — `synthesize_dispatch()` returns `Send("synthesize_one", cluster)` per cluster
  - [x] Create `synthesize_one()` sub-node — LLM call via `synthesizer.j2`, returns summary with headline, bullets, why_it_matters, sources
  - [x] Aggregation merges all summaries; graceful skip on failed clusters

- [x] Task 7: Implement Trender node ✅
  <!-- files: src/ainews/agents/nodes/trender.py, tests/agents/nodes/test_trender.py -->
  - [x] Write unit tests with mocked LLM (trend extraction, edge case: few summaries)
  - [x] Create `agents/nodes/trender.py` — single LLM call via `trender.j2` across all summaries
  - [x] Output 3-7 `Trend` objects with name, description, evidence_cluster_ids
  - [x] Apply `@node_resilient` decorator + metrics tracking

- [x] Task 8: Implement Writer node ✅
  <!-- files: src/ainews/agents/nodes/writer.py, tests/agents/nodes/test_writer.py -->
  - [x] Write unit tests (template rendering, executive summary polish, degraded report)
  - [x] Create `agents/nodes/writer.py` — Jinja2 template assembly for full Markdown report
  - [x] LLM polish pass on Executive Summary only via `writer_executive.j2`
  - [x] Include degradation notice in report header if `state.errors` is non-empty
  - [x] Apply `@node_resilient` decorator + metrics tracking

- [x] Task: Conductor - User Manual Verification 'Node Implementations' ✅

## Phase 3: Graph Assembly & Checkpointing

- [ ] Task 1: Wire StateGraph with all nodes and edges
  - [ ] Write tests for graph compilation (node registration, edge connectivity)
  - [ ] Create `agents/graph.py` with `build_graph(checkpointer=None) -> CompiledStateGraph`
  - [ ] Register all 8 nodes + 2 Send() sub-nodes
  - [ ] Define linear edges: START → Planner → Retriever → Scraper → Filter, Dedup → Synthesizer → Trender → Writer → END

- [ ] Task 2: Implement conditional edges
  - [ ] Write tests for retry routing (below threshold + loop_count < 2 → Planner; otherwise → Dedup)
  - [ ] Write tests for degrade routing (error_threshold exceeded → Writer)
  - [ ] Implement `filter_router(state) -> str` — returns "planner" or "dedup"
  - [ ] Implement `post_synthesizer_router(state) -> str` — returns "trender" or "writer" (degrade)
  - [ ] Wire conditional edges into graph

- [ ] Task 3: Integrate SqliteSaver checkpointer
  - [ ] Write tests for checkpoint persistence and run resumability
  - [ ] Wire `SqliteSaver` from `langgraph-checkpoint-sqlite` into `build_graph()`
  - [ ] Verify graph invocation with `thread_id = run_id` persists state between nodes
  - [ ] Verify failed runs can resume from last checkpoint

- [ ] Task: Conductor - User Manual Verification 'Graph Assembly & Checkpointing' (Protocol in workflow.md)

## Phase 4: CLI Integration & End-to-End Testing

- [ ] Task 1: Extend `ainews run` CLI command
  - [ ] Write tests for CLI argument parsing (--topic, --days, --limit, --model-override)
  - [ ] Implement `ainews run` — hydrates params from CLI args, creates `Run` DB row, invokes compiled graph
  - [ ] Persist `report_md` to `var/reports/{run_id}/report.md`
  - [ ] Update `Run` row with status, stats, timing on completion
  - [ ] Handle graph errors gracefully (update Run.error, set status=failed)

- [ ] Task 2: Integration test with mock LLM
  - [ ] Create fixture data: 3 sites, 3-day window, mock Tavily responses, mock LLM responses
  - [ ] Write integration test: full graph execution from Planner through Writer
  - [ ] Assert: report_md is non-empty, contains expected sections, metrics populated, no unhandled errors
  - [ ] Assert: checkpoint data exists in SQLite after run

- [ ] Task 3: End-to-end verification and coverage
  - [ ] Run `make lint && make typecheck && make test` — all green
  - [ ] Verify ≥ 80% line coverage on all new modules
  - [ ] Verify `ainews run --topic LLM --days 7 --limit 20` produces a Markdown file (requires local LLM)
  - [ ] Document any known limitations or edge cases in learnings.md

- [ ] Task: Conductor - User Manual Verification 'CLI Integration & End-to-End Testing' (Protocol in workflow.md)
