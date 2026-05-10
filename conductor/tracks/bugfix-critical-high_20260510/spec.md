# Spec: Critical & High Issue Fixes

## Overview

Address 10 issues (4 Critical + 6 High) identified during deep codebase analysis.
These span security, concurrency, data correctness, performance, and dead-code
integration across the pipeline, API middleware, and LLM subsystems.

## Functional Requirements

### Critical Fixes

1. **C1 — Eliminate duplicate report export**
   - Remove `export_markdown()`/`export_xlsx()` calls from `_persist_report()` in `tasks/pipeline.py`
   - `_persist_report()` constructs file paths deterministically and creates only the DB `Report` row
   - `exporter_node` remains the single export site

2. **C2 — Mitigate SQLite locking under concurrent writes**
   - Cache the `sessionmaker` factory per engine (avoid re-creating on every `log_to_db` call)
   - Add SQLite `busy_timeout` awareness documentation
   - Batch or serialize log writes where feasible

3. **C3 — Fix CSRF middleware bypass**
   - Require `X-CSRF-Token` header on ALL mutating requests (POST/PUT/PATCH/DELETE)
   - Remove the "cookie-exists-but-no-header → allow" bypass path
   - Reject with 403 if header is missing or mismatched

4. **C4 — Replace global logging engine with ContextVar**
   - Replace `_logging_engine_cache` module global with `contextvars.ContextVar`
   - Update `set_logging_engine()` and `_get_logging_engine()` to use ContextVar
   - Each concurrent pipeline task gets isolated engine reference

### High Fixes

5. **H1 — Fix `asyncio.run()` in scraper node**
   - Replace `asyncio.run(scraper.scrape(url))` with a sync-safe wrapper
   - Handle case where an event loop is already running

6. **H2 — Wire RunCapChecker into the pipeline**
   - Integrate `RunCapChecker` into graph node transitions
   - Fix token key mismatch (`tokens` → `input_tokens` + `output_tokens`)
   - Add cap violation → early termination path

7. **H3 — Wire LLM concurrency limiter into nodes**
   - Replace direct `llm.invoke()` calls with `limited_invoke_sync()` in all LLM-using nodes
   - Ensures GPU/endpoint saturation protection during Send() fan-out

8. **H4 — Cache Settings singleton**
   - Create a cached `get_settings()` function to avoid re-parsing `.env` on every call
   - Replace all `Settings()` calls across codebase with `get_settings()`

9. **H5 — Fix filter retry loop article accumulation**
   - Track processed URLs in filter node to skip duplicates on retry by emitting
     replacement values (not appends) or tracking seen URLs
   - Ensure `loop_count` semantics work correctly with the non-additive reducer

10. **H6 — Fix `raw_articles` key mismatch in logging**
    - Update `_summarize_node_input()` to use correct state keys:
      `raw_results` for scraper, `fetched_articles` for filter
    - Update `_summarize_node_result()` for any similar mismatches

## Non-Functional Requirements

- All fixes must have corresponding unit tests
- Existing test suite must remain green
- `ruff check . && ruff format --check .` must pass
- No behavioral regressions in pipeline output

## Acceptance Criteria

- [ ] No duplicate file writes during pipeline execution
- [ ] `log_to_db` uses cached session factory per engine
- [ ] CSRF middleware rejects mutating requests without `X-CSRF-Token` header
- [ ] Concurrent pipeline tasks use isolated engine references via ContextVar
- [ ] Scraper node works in both sync and async contexts
- [ ] RunCapChecker is invoked at node transitions with correct token counting
- [ ] All LLM-calling nodes use `limited_invoke_sync()`
- [ ] `Settings()` is instantiated once per process via cache
- [ ] Filter retry does not produce duplicate articles
- [ ] Node logging summaries display correct article/result counts
- [ ] All existing tests pass + new tests for each fix

## Out of Scope

- PostgreSQL migration (documented as v2)
- Login rate limiting (Medium severity — separate track)
- Checkpoint DB cleanup (Medium — separate track)
- Flash message multi-support (Medium — separate track)
- Health probe label fix (trivial — can be a quick commit)
