"""Tavily search wrapper with project defaults and caching.

Wraps ``langchain-tavily.TavilySearch`` with:
- Project defaults (``topic="news"``, Markdown raw content).
- Pluggable cache via the :class:`CacheBackend` protocol (default: in-memory TTL).
- Structured :class:`SearchResult` output.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# ── Models ────────────────────────────────────────────────


class SearchResult(BaseModel):
    """A single search result from Tavily."""

    url: str
    title: str
    content: str
    raw_content: str | None = None
    score: float


# ── Cache Protocol ────────────────────────────────────────


@runtime_checkable
class CacheBackend(Protocol):
    """Pluggable cache interface.

    Phase 2 uses an in-memory ``TTLCache``; Phase 5 swaps to Valkey.
    """

    def get(self, key: str) -> str | None:
        """Retrieve a cached value by key, or ``None`` if missing/expired."""
        ...

    def set(self, key: str, value: str, ttl: int) -> None:
        """Store a value with a TTL (seconds)."""
        ...


# ── Constants ─────────────────────────────────────────────

_CACHE_TTL_SECONDS = 21600  # 6 hours


# ── Tool ──────────────────────────────────────────────────


class TavilySearchTool:
    """Tavily search with project defaults, caching, and structured output.

    Parameters
    ----------
    api_key
        Tavily API key.
    cache
        Pluggable cache backend (default: ``None`` for no caching).
    cache_ttl
        Cache TTL in seconds (default: 6 hours).
    """

    def __init__(
        self,
        api_key: str,
        cache: CacheBackend | None = None,
        cache_ttl: int = _CACHE_TTL_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._cache = cache
        self._cache_ttl = cache_ttl
        logger.info(
            "tavily_tool_init",
            api_key_length=len(api_key),
            api_key_prefix=api_key[:8] + "..." if len(api_key) > 8 else "(empty/short)",
        )
        self._tool: Any = self._build_tool()

    def _build_tool(self) -> object:
        """Lazily construct the underlying TavilySearch tool."""
        from langchain_tavily import TavilySearch
        from langchain_tavily._utilities import TavilySearchAPIWrapper

        return TavilySearch(
            max_results=10,
            topic="news",
            include_raw_content=True,
            api_wrapper=TavilySearchAPIWrapper(tavily_api_key=self._api_key),
        )

    @staticmethod
    def _cache_key(
        query: str,
        include_domains: list[str] | None,
        time_range: str | None,
        max_results: int,
    ) -> str:
        """Compute a deterministic SHA-256 cache key."""
        payload = {
            "query": query,
            "include_domains": sorted(include_domains) if include_domains else None,
            "time_range": time_range,
            "max_results": max_results,
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def search(
        self,
        query: str,
        *,
        include_domains: list[str] | None = None,
        time_range: str | None = None,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """Run a Tavily search with caching.

        Parameters
        ----------
        query
            Search query string.
        include_domains
            Optional list of domains to restrict search to.
        time_range
            Optional time range filter (e.g. ``"day"``, ``"week"``).
        max_results
            Maximum number of results (default 10).

        Returns
        -------
        list[SearchResult]
            Structured search results.
        """
        cache_key = self._cache_key(query, include_domains, time_range, max_results)

        # Check cache
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.info("tavily_cache_hit", query=query, key=cache_key[:8])
                return [SearchResult.model_validate(r) for r in json.loads(cached)]

        # Execute search
        logger.info("tavily_search", query=query, max_results=max_results)
        invoke_args = {
            "query": query,
            **({"include_domains": include_domains} if include_domains else {}),
            **({"time_range": time_range} if time_range else {}),
            **({"max_results": max_results} if max_results != 10 else {}),
        }
        try:
            raw_results = self._tool.invoke(invoke_args)
        except Exception as exc:
            logger.error(
                "tavily_search_error",
                query=query,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            return []

        # Parse results
        results = self._parse_results(raw_results)

        # Store in cache
        if self._cache is not None and results:
            serialized = json.dumps([r.model_dump() for r in results], default=str)
            self._cache.set(cache_key, serialized, self._cache_ttl)
            logger.info("tavily_cache_set", query=query, key=cache_key[:8])

        return results

    def extract(self, url: str) -> str | None:
        """Extract full content from a URL via Tavily Extract API.

        Uses Tavily's cloud infrastructure to fetch and parse the page,
        avoiding the need for direct outbound HTTP from this server.
        Useful when firewalls block direct access to arbitrary domains.

        Parameters
        ----------
        url
            The URL to extract content from.

        Returns
        -------
        str | None
            Extracted text content, or ``None`` on failure.
        """
        try:
            from langchain_tavily import TavilyExtract
            from langchain_tavily._utilities import TavilyExtractAPIWrapper

            tool = TavilyExtract(
                extract_depth="basic",
                apiwrapper=TavilyExtractAPIWrapper(
                    tavily_api_key=self._api_key,
                ),
            )

            raw = tool.invoke({"urls": [url]})

            # Parse the response — can be dict, list, or str
            if isinstance(raw, dict):
                results = raw.get("results", [])
                if results and isinstance(results, list):
                    return results[0].get("raw_content") or results[0].get("text", "")
            elif isinstance(raw, list) and raw:
                item = raw[0]
                if isinstance(item, dict):
                    return item.get("raw_content") or item.get("text", "")
                return str(item) if item else None
            elif isinstance(raw, str) and raw.strip():
                return raw

            logger.info("tavily_extract_empty", url=url)
            return None

        except Exception as exc:
            logger.warning("tavily_extract_error", url=url, error=str(exc))
            return None

    @staticmethod
    def _parse_results(raw: object) -> list[SearchResult]:
        """Convert Tavily raw output to SearchResult list."""
        if isinstance(raw, dict) and "results" in raw:
            items = raw["results"]
        elif isinstance(raw, list):
            items = raw
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "results" in parsed:
                    items = parsed["results"]
                else:
                    items = parsed
            except json.JSONDecodeError:
                return []
        else:
            return []

        results: list[SearchResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    raw_content=item.get("raw_content"),
                    score=float(item.get("score", 0.0)),
                )
            )
        return results
