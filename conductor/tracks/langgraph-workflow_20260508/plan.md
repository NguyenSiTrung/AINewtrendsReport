# Plan: LangGraph Workflow

## Phase 1: State & Prompt Infrastructure

- [ ] Task 1: Define GraphState TypedDict and supporting types
  - [ ] Write tests for GraphState field defaults and type annotations
  - [ ] Create `agents/state.py` with `GraphState(TypedDict)` — all fields from spec (run_id, params, queries, raw_results, fetched_articles, filtered_articles, clusters, summaries, trends, report_md, errors, metrics, loop_count)
  - [ ] Create `NodeError` dataclass (node, message, traceback, timestamp)
  - [ ] Create supporting types: `SearchHit`, `Article`, `Cluster`, `Summary`, `Trend` as TypedDicts
  - [ ] Verify types pass mypy strict

- [ ] Task 2: Create prompt template loader and Jinja2 templates
  - [ ] Write tests for template loading (file not found, variable rendering, missing vars)
  - [ ] Create `agents/prompts/loader.py` with `load_prompt(template_name, **context) -> str`
  - [ ] Create `planner.j2` — query generation prompt with topics, sites, timeframe vars
  - [ ] Create `filter.j2` — relevance scoring prompt with article content, topics vars
  - [ ] Create `synthesizer.j2` — cluster summarization prompt with articles, source refs
  - [ ] Create `trender.j2` — trend extraction prompt with all summaries
  - [ ] Create `writer_executive.j2` — executive summary polish prompt

- [ ] Task 3: Create error resilience utilities
  - [ ] Write tests for retry decorator, metrics accumulator, degrade checker
  - [ ] Create `agents/resilience.py` with `@node_resilient` decorator (try/except → append NodeError to state.errors)
  - [ ] Add `with_retries()` wrapper using tenacity (3 attempts, exponential 2s/4s/8s, retry on ConnectionError/5xx/timeout)
  - [ ] Add `track_metrics(node_name, state, start_time, token_usage)` utility for per-node metrics accumulation
  - [ ] Add `should_degrade(state, error_threshold) -> bool` checker

- [ ] Task: Conductor - User Manual Verification 'State & Prompt Infrastructure' (Protocol in workflow.md)

## Phase 2: Node Implementations
<!-- execution: parallel -->

- [ ] Task 1: Implement Planner node
  <!-- files: src/ainews/agents/nodes/planner.py, tests/agents/nodes/test_planner.py -->
  - [ ] Write unit tests with mocked LLM (structured JSON output, error cases)
  - [ ] Create `agents/nodes/planner.py` — LLM call via `llm_factory()`, renders `planner.j2`, parses JSON output into `queries` list
  - [ ] Handle malformed LLM JSON output gracefully (retry parse, fallback)
  - [ ] Apply `@node_resilient` decorator + metrics tracking

- [ ] Task 2: Implement Retriever node with Send() fan-out
  <!-- files: src/ainews/agents/nodes/retriever.py, tests/agents/nodes/test_retriever.py -->
  <!-- depends: task1 -->
  - [ ] Write unit tests for fan-out logic, result aggregation, partial failure handling
  - [ ] Create `agents/nodes/retriever.py` — `retrieve_dispatch()` returns list of `Send("retrieve_one", query)` per query
  - [ ] Create `retrieve_one()` sub-node — calls Tavily search wrapper (Phase 2 tool), returns `raw_results` partial
  - [ ] Aggregation merges all `raw_results` from parallel sub-invocations

- [ ] Task 3: Implement Scraper node
  <!-- files: src/ainews/agents/nodes/scraper.py, tests/agents/nodes/test_scraper.py -->
  - [ ] Write unit tests with mocked httpx responses (content fill, skip on failure, js_render flag)
  - [ ] Create `agents/nodes/scraper.py` — iterates `raw_results`, calls async scraper (Phase 2 tool) for items with missing/short content
  - [ ] Graceful skip on individual scrape failures (append to errors, continue)
  - [ ] Apply `@node_resilient` decorator + metrics tracking

- [ ] Task 4: Implement Filter node
  <!-- files: src/ainews/agents/nodes/filter.py, tests/agents/nodes/test_filter.py -->
  - [ ] Write unit tests with mocked LLM (scoring, threshold filtering, retry loop trigger)
  - [ ] Create `agents/nodes/filter.py` — LLM call per article via `filter.j2`, structured output `{score, keep, reason}`
  - [ ] Apply configurable threshold (default 0.5), output `filtered_articles`
  - [ ] Increment `loop_count` in state; return routing signal for conditional edge

- [ ] Task 5: Implement Dedup node
  <!-- files: src/ainews/agents/nodes/dedup.py, tests/agents/nodes/test_dedup.py -->
  - [ ] Write unit tests with fixture articles (URL canon, simhash bucketing, Jaccard merge)
  - [ ] Create `agents/nodes/dedup.py` — wraps Phase 2 dedup engine, transforms `filtered_articles` into `clusters`
  - [ ] Each cluster has a primary article (highest priority × recency × length) + variants
  - [ ] Apply `@node_resilient` decorator + metrics tracking

- [ ] Task 6: Implement Synthesizer node with Send() fan-out
  <!-- files: src/ainews/agents/nodes/synthesizer.py, tests/agents/nodes/test_synthesizer.py -->
  <!-- depends: task1 -->
  - [ ] Write unit tests with mocked LLM (per-cluster summary, partial failure, aggregation)
  - [ ] Create `agents/nodes/synthesizer.py` — `synthesize_dispatch()` returns `Send("synthesize_one", cluster)` per cluster
  - [ ] Create `synthesize_one()` sub-node — LLM call via `synthesizer.j2`, returns summary with headline, bullets, why_it_matters, sources
  - [ ] Aggregation merges all summaries; graceful skip on failed clusters

- [ ] Task 7: Implement Trender node
  <!-- files: src/ainews/agents/nodes/trender.py, tests/agents/nodes/test_trender.py -->
  - [ ] Write unit tests with mocked LLM (trend extraction, edge case: few summaries)
  - [ ] Create `agents/nodes/trender.py` — single LLM call via `trender.j2` across all summaries
  - [ ] Output 3–7 `Trend` objects with name, description, evidence_cluster_ids
  - [ ] Apply `@node_resilient` decorator + metrics tracking

- [ ] Task 8: Implement Writer node
  <!-- files: src/ainews/agents/nodes/writer.py, tests/agents/nodes/test_writer.py -->
  - [ ] Write unit tests (template rendering, executive summary polish, degraded report)
  - [ ] Create `agents/nodes/writer.py` — Jinja2 template assembly for full Markdown report
  - [ ] LLM polish pass on Executive Summary only via `writer_executive.j2`
  - [ ] Include degradation notice in report header if `state.errors` is non-empty
  - [ ] Apply `@node_resilient` decorator + metrics tracking

- [ ] Task: Conductor - User Manual Verification 'Node Implementations' (Protocol in workflow.md)

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
