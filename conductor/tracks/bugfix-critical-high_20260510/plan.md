# Plan: Critical & High Issue Fixes

## Phase 1: Core Safety Fixes
<!-- execution: parallel -->

- [ ] Task 1: C3 — Fix CSRF middleware bypass
  <!-- files: src/ainews/api/middleware/__init__.py, tests/test_admin_auth.py -->
  - [ ] Update CSRFMiddleware.dispatch() to reject when header is missing
  - [ ] Remove the "cookie exists but no header → allow" bypass path
  - [ ] Add tests: mutating request without header → 403
  - [ ] Add tests: mutating request with valid header → pass
  - [ ] Verify existing HTMX/form tests still pass

- [ ] Task 2: C4 — Replace global logging engine with ContextVar
  <!-- files: src/ainews/agents/resilience.py, tests/agents/test_resilience.py -->
  - [ ] Replace `_logging_engine_cache` global with `contextvars.ContextVar`
  - [ ] Update `set_logging_engine()` to use ContextVar.set()
  - [ ] Update `_get_logging_engine()` to use ContextVar.get()
  - [ ] Add test: concurrent tasks get isolated engine references
  - [ ] Verify existing resilience tests pass

- [ ] Task 3: H4 — Cache Settings singleton
  <!-- files: src/ainews/core/config.py, tests/test_config.py -->
  - [ ] Add `get_settings()` cached function with `functools.lru_cache`
  - [ ] Replace `Settings()` calls across codebase with `get_settings()`
  - [ ] Add `clear_settings_cache()` for test isolation
  - [ ] Add test: multiple calls return same instance
  - [ ] Verify existing config tests pass

- [ ] Task 4: Conductor — User Manual Verification 'Core Safety Fixes' (Protocol in workflow.md)

## Phase 2: Pipeline Data Correctness
<!-- execution: parallel -->

- [ ] Task 1: C1 — Eliminate duplicate report export
  <!-- files: src/ainews/tasks/pipeline.py, tests/test_celery.py -->
  - [ ] Remove `export_markdown()`/`export_xlsx()` calls from `_persist_report()`
  - [ ] Construct file paths deterministically from `reports_dir / run_id`
  - [ ] Create `Report` DB row using constructed paths + result metadata
  - [ ] Add test: `_persist_report` does not call export functions
  - [ ] Verify pipeline integration tests pass

- [ ] Task 2: H6 — Fix key mismatch in logging summaries
  <!-- files: src/ainews/agents/resilience.py -->
  - [ ] Fix `_summarize_node_input()`: scraper → `raw_results`, filter → `fetched_articles`
  - [ ] Audit `_summarize_node_result()` for similar mismatches
  - [ ] Add tests for correct summary messages per node

- [ ] Task 3: H5 — Fix filter retry article accumulation
  <!-- files: src/ainews/agents/nodes/filter.py, src/ainews/agents/state.py, tests/agents/test_graph.py -->
  - [ ] Track processed URLs in filter node to skip duplicates on retry
  - [ ] Ensure `loop_count` replacement semantics are correct
  - [ ] Add test: retry loop does not produce duplicate filtered articles
  - [ ] Add test: loop_count increments correctly across retries

- [ ] Task 4: Conductor — User Manual Verification 'Pipeline Data Correctness' (Protocol in workflow.md)

## Phase 3: Pipeline Integration
<!-- execution: parallel -->

- [ ] Task 1: H1 — Fix asyncio.run() in scraper node
  <!-- files: src/ainews/agents/nodes/scraper.py, src/ainews/agents/tools/scraper.py, tests/agents/test_scraper_node.py -->
  - [ ] Replace `asyncio.run()` with sync-safe wrapper (try existing loop, fallback to new)
  - [ ] Add test: scraper works when no event loop exists
  - [ ] Add test: scraper works when event loop is already running

- [ ] Task 2: H2 — Wire RunCapChecker into pipeline
  <!-- files: src/ainews/core/run_caps.py, src/ainews/agents/resilience.py, src/ainews/tasks/pipeline.py, tests/core/test_run_caps.py -->
  - [ ] Fix token key mismatch: sum `input_tokens` + `output_tokens` instead of `tokens`
  - [ ] Instantiate `RunCapChecker` in `run_pipeline` task
  - [ ] Add cap check in `@node_resilient` decorator (post-execution)
  - [ ] On violation: append `NodeError` with cap details, trigger degradation
  - [ ] Add tests for each cap type (tokens, wall time, articles)

- [ ] Task 3: H3 — Wire LLM concurrency limiter into nodes
  <!-- files: src/ainews/agents/nodes/planner.py, src/ainews/agents/nodes/filter.py, src/ainews/agents/nodes/synthesizer.py, src/ainews/agents/nodes/trender.py, src/ainews/agents/nodes/writer.py, tests/agents/test_concurrency.py -->
  - [ ] Replace `llm.invoke(prompt)` with `limited_invoke_sync(llm, prompt)` in all 5 LLM nodes
  - [ ] Add test: concurrent calls are throttled by semaphore
  - [ ] Verify existing node tests still pass

- [ ] Task 4: Conductor — User Manual Verification 'Pipeline Integration' (Protocol in workflow.md)

## Phase 4: Final Verification
<!-- depends: phase1, phase2, phase3 -->

- [ ] Task 1: Full test suite + lint validation
  - [ ] Run `pytest --cov` — all tests pass
  - [ ] Run `ruff check . && ruff format --check .` — no issues
  - [ ] Verify no regressions in pipeline behavior
  - [ ] Confirm coverage ≥ 80%

- [ ] Task 2: Conductor — User Manual Verification 'Final Verification' (Protocol in workflow.md)
