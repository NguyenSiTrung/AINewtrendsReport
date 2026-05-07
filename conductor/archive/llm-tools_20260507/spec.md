# Spec: LLM Client & Tools

## Overview

Implement the core tooling layer for the AI News & Trends pipeline: an LLM client factory
with config resolution, a Tavily search wrapper with in-memory caching, an async web scraper
with robots.txt compliance, and a deterministic deduplication engine. These tools are consumed
by LangGraph agent nodes in Phase 3.

## Functional Requirements

### FR-1: LLM Factory (`src/ainews/llm/`)

- **`llm/config.py`** — `LLMConfig` pydantic model (frozen) holding resolved LLM parameters:
  `base_url`, `api_key`, `model`, `temperature`, `max_tokens`, `timeout`, `extra_headers`.
- **`llm/factory.py`** — Two-layer design:
  1. `get_llm_config(settings: Settings, db_overrides: dict | None = None, model_override: str | None = None) → LLMConfig`
     — Resolves config from env (`Settings`) → `settings_kv` DB overrides → per-run `model_override`.
     Priority: `model_override > db_overrides > env/Settings`.
  2. `get_llm(config: LLMConfig) → ChatOpenAI`
     — Pure construction from resolved config. Returns a `langchain-openai.ChatOpenAI` instance.
- **`llm/test_connection.py`** — `test_llm_connection(config: LLMConfig) → TestResult`
  — Issues a 1-token completion to verify connectivity. Returns structured result
  (success/failure, latency_ms, model_name, error message).
- **CLI integration** — `ainews llm test` command: resolves config, displays it, runs test,
  prints result.

### FR-2: Tavily Search Wrapper (`src/ainews/agents/tools/tavily_search.py`)

- Wrap `langchain-tavily.TavilySearch` with project defaults:
  `topic="news"`, `include_raw_content="markdown"`, `max_results` from params.
- **In-memory cache** via `cachetools.TTLCache`:
  Key = `hashlib.sha256(json.dumps(query+params, sort_keys=True))`, TTL = 6 hours.
  Cache is injectable (accepts `CacheBackend` protocol) for Phase 5 Valkey swap.
- `search(query: str, *, include_domains: list[str] | None, time_range: str | None, max_results: int = 10) → list[SearchResult]`
- `SearchResult` pydantic model: `url`, `title`, `content`, `raw_content`, `score`.

### FR-3: Web Scraper (`src/ainews/agents/tools/scraper.py`)

- **Async httpx client** with configurable User-Agent, timeout, redirect following.
- **robots.txt compliance**: fetch + cache `robots.txt` per domain; respect `Disallow` rules.
- **Content extraction** via `trafilatura.extract()` (Markdown output).
- **Optional Playwright** fallback when `js_render=True` (site-level flag).
- `scrape(url: str, *, js_render: bool = False) → ScrapedArticle | None`
- `ScrapedArticle` pydantic model: `url`, `title`, `content_md`, `fetched_at`, `word_count`.
- Guards: per-domain rate limiting via `asyncio.Semaphore` (defer Valkey-based token bucket to Phase 5).

### FR-4: Deduplication Engine (`src/ainews/agents/tools/dedup.py`)

- **URL canonicalization**: strip UTM/ref/tracking params, normalize host case, drop AMP
  suffixes, resolve known redirect patterns (e.g., Google News URLs).
- **Simhash** (64-bit) on `title + first 500 chars of content` using token-level hashing.
  Bucket by Hamming distance ≤ 3.
- **Jaccard similarity** on 3-gram token shingles of `title + lead paragraph`.
  Merge articles within a bucket if Jaccard ≥ 0.6.
- **Cluster ranking**: within each cluster, select primary article by
  `priority × recency × content_length` score.
- `deduplicate(articles: list[Article]) → list[Cluster]`
- `Cluster` model: `primary: Article`, `variants: list[Article]`, `similarity_score: float`.
- No embeddings. No LLM calls. Fully deterministic.

## Non-Functional Requirements

- **Testing**: `respx` for all HTTP mocking (LLM + Tavily + scraper). Unit tests target ≥ 80%
  coverage. Optional `@pytest.mark.integration` tests for real endpoints (skipped by default).
- **Type safety**: Full `mypy --strict` compliance on all new modules.
- **Error handling**: All tools return structured errors (never raise to callers); follows
  the node pattern of "catch → record → return partial result."
- **Logging**: `structlog` for all tool operations with bound context (url, query, latency).
- **Dependencies**: `langchain-openai`, `langchain-tavily`, `httpx`, `trafilatura`,
  `cachetools`, `respx` (dev). Playwright is optional (extras group).

## Acceptance Criteria

1. `ainews llm test` succeeds against a running local LLM server, displaying resolved config
   and latency.
2. `pytest tests/llm/` passes — config resolution, factory construction, connection test
   (all mocked via respx).
3. `pytest tests/tools/` passes — Tavily search (with cache hit/miss), scraper
   (with robots.txt compliance), dedup (clustering correctness on fixture corpus).
4. Tavily cache correctly returns cached results within TTL and misses after expiry.
5. Scraper respects robots.txt `Disallow` rules and extracts Markdown content via trafilatura.
6. Dedup correctly clusters near-duplicate articles and selects the best primary.
7. All lints pass: `ruff check . && ruff format --check . && mypy src/`.
8. Coverage ≥ 80% on all new modules.

## Out of Scope

- Valkey-backed cache (Phase 5)
- LangGraph node wiring (Phase 3)
- Per-domain Valkey token bucket rate limiting (Phase 5/8)
- Embedding-based semantic dedup (v2)
- Admin UI for LLM settings (Phase 6)
- Celery task integration (Phase 5)
