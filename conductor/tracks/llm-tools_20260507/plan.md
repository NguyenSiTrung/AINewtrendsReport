# Plan: LLM Client & Tools

## Phase 1: LLM Client Foundation

- [ ] Task 1: Add Phase 2 runtime & dev dependencies
  - Add to `pyproject.toml` dependencies: `langchain-openai`, `langchain-tavily`, `httpx`,
    `trafilatura`, `cachetools`, `tenacity`
  - Add to dev deps: `respx`, `pytest-asyncio`
  - Add optional extras group `[playwright]`: `playwright`
  - Run `uv lock` to update lockfile
  - Update `.pre-commit-config.yaml` mypy `additional_dependencies`

- [ ] Task 2: LLMConfig pydantic model
  - Create `src/ainews/llm/config.py`
  - `LLMConfig(BaseModel, frozen=True)`: base_url, api_key, model, temperature,
    max_tokens, timeout, extra_headers
  - Tests in `tests/llm/test_config.py`: construction, immutability, defaults, serialization

- [ ] Task 3: Config resolution — `get_llm_config()`
  - Create `src/ainews/llm/factory.py`
  - `get_llm_config(settings, db_overrides=None, model_override=None) → LLMConfig`
  - Priority chain: model_override > db_overrides > Settings defaults
  - Tests in `tests/llm/test_factory.py`: env-only, db override, model override, full chain

- [ ] Task 4: LLM factory — `get_llm()`
  - Add `get_llm(config: LLMConfig) → ChatOpenAI` to `factory.py`
  - Construct ChatOpenAI with all config params (base_url, model, temperature, etc.)
  - Tests: verify constructed client attributes match config values

- [ ] Task 5: Connection test — `test_llm_connection()`
  - Create `src/ainews/llm/test_connection.py`
  - `TestResult(BaseModel)`: success, latency_ms, model_name, error
  - `test_llm_connection(config) → TestResult`: 1-token completion
  - Tests with `respx`: success case, connection error, timeout, invalid response

- [ ] Task 6: CLI `ainews llm test` command
  - Update `src/ainews/cli.py`: wire `llm` sub-app with `test` command
  - Displays resolved config (masked api_key), runs connection test, prints result
  - Tests in `tests/test_cli.py` via CliRunner + respx

- [ ] Task: Conductor - User Manual Verification 'LLM Client Foundation' (Protocol in workflow.md)

**Exit Criteria:** `ainews llm test` runs (mocked); `pytest tests/llm/` green; lints clean.

---

## Phase 2: Tavily Search Wrapper

- [ ] Task 1: SearchResult model & CacheBackend protocol
  - Create `src/ainews/agents/tools/tavily_search.py`
  - `SearchResult(BaseModel)`: url, title, content, raw_content, score
  - `CacheBackend(Protocol)`: get(key) → str|None, set(key, value, ttl) → None
  - Tests in `tests/tools/test_tavily_search.py`: model construction/validation

- [ ] Task 2: InMemoryCache implementation
  - Create `src/ainews/agents/tools/cache.py`
  - `InMemoryCache` backed by `cachetools.TTLCache`, implements `CacheBackend`
  - Configurable maxsize (default 256) and ttl (default 21600s / 6h)
  - Tests: cache hit, cache miss, TTL expiry, key hashing determinism

- [ ] Task 3: TavilySearchTool wrapper
  - Implement `TavilySearchTool` with `search()` method
  - Project defaults: `topic="news"`, `include_raw_content="markdown"`
  - Cache: `sha256(json(query+params))` → cached JSON response
  - Tests with `respx`: mock Tavily API, verify cache hit/miss, verify defaults applied

- [ ] Task: Conductor - User Manual Verification 'Tavily Search Wrapper' (Protocol in workflow.md)

**Exit Criteria:** `pytest tests/tools/test_tavily*.py` green; cache hits within TTL, misses after.

---

## Phase 3: Web Scraper

- [ ] Task 1: ScrapedArticle model
  - Create `src/ainews/agents/tools/scraper.py`
  - `ScrapedArticle(BaseModel)`: url, title, content_md, fetched_at, word_count
  - Tests in `tests/tools/test_scraper.py`: model construction/validation

- [ ] Task 2: Robots.txt checker
  - Implement `RobotsTxtChecker`: async fetch + parse + in-memory cache per domain
  - `is_allowed(url, user_agent) → bool`
  - Tests with `respx`: mock robots.txt, verify allow/disallow/missing-file handling

- [ ] Task 3: Async scraper core
  - Implement `Scraper` class: async `scrape(url, js_render=False) → ScrapedArticle | None`
  - httpx client with configurable UA, timeout, redirect following
  - `trafilatura.extract()` for Markdown content extraction
  - Robots.txt check before fetching; per-domain `asyncio.Semaphore` rate limit
  - Tests with `respx`: mock HTML, verify extraction, verify robots.txt blocking,
    verify rate limiting behavior

- [ ] Task: Conductor - User Manual Verification 'Web Scraper' (Protocol in workflow.md)

**Exit Criteria:** `pytest tests/tools/test_scraper.py` green; respects robots.txt; extracts Markdown.

---

## Phase 4: Deduplication Engine

- [ ] Task 1: URL canonicalization
  - Create `src/ainews/agents/tools/dedup.py`
  - `canonicalize_url(url) → str`: strip UTM/ref/tracking params, normalize host,
    drop AMP suffixes, resolve Google News redirect patterns
  - Tests: comprehensive URL normalization cases

- [ ] Task 2: Simhash implementation
  - `simhash(text) → int` (64-bit token-level), `hamming_distance(a, b) → int`
  - `bucket_by_simhash(articles, threshold=3) → list[list[Article]]`
  - Tests: known text pairs, distance calculations, bucketing correctness

- [ ] Task 3: Jaccard shingle similarity
  - `shingles(text, n=3) → set[str]` (token 3-grams), `jaccard_similarity(a, b) → float`
  - Tests: known pairs, threshold behavior, empty/short text edge cases

- [ ] Task 4: Cluster & deduplicate orchestrator
  - `Cluster(BaseModel)`: primary, variants, similarity_score
  - `deduplicate(articles) → list[Cluster]`: canonicalize → simhash bucket →
    Jaccard merge → rank primaries by `priority × recency × content_length`
  - Tests: fixture corpus with known duplicates, verify cluster correctness,
    verify primary selection logic

- [ ] Task: Conductor - User Manual Verification 'Deduplication Engine' (Protocol in workflow.md)

**Exit Criteria:** `pytest tests/tools/test_dedup.py` green; fixture corpus clusters correctly.

---

## Phase 5: Integration & Final Verification

- [ ] Task 1: pytest integration marker & conftest
  - Register `integration` marker in `pyproject.toml`
  - Create/update `tests/conftest.py` with skip-when-unavailable fixtures
  - Configure `pytest-asyncio` mode

- [ ] Task 2: Integration tests (optional)
  - `tests/integration/test_llm_integration.py`: real LLM endpoint
  - `tests/integration/test_tavily_integration.py`: real Tavily API
  - `tests/integration/test_scraper_integration.py`: real URL scraping
  - All `@pytest.mark.integration`, skipped by default (`-m "not integration"`)

- [ ] Task 3: Final lint, typecheck, coverage verification
  - `ruff check . && ruff format --check .` — clean
  - `mypy src/` — clean
  - `pytest --cov` — ≥ 80% on all new modules
  - Fix any remaining issues

- [ ] Task: Conductor - User Manual Verification 'Integration & Final Verification' (Protocol in workflow.md)

**Exit Criteria:** `make lint && make typecheck && make test` all green; ≥ 80% coverage on new modules.
