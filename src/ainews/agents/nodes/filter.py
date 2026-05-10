"""Filter node — LLM-based relevance scoring.

Calls the LLM per article to score relevance. Keeps articles above
a configurable threshold. Manages loop_count for retry logic.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog

from ainews.llm.concurrency import limited_invoke_sync
from ainews.agents.prompts.loader import load_prompt
from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import Article, GraphState

logger = structlog.get_logger(__name__)

_DEFAULT_THRESHOLD = 0.5
_DEFAULT_MIN_KEPT = 3


def _get_llm() -> Any:
    """Lazy-load LLM client from factory."""
    from ainews.core.config import get_settings
    from ainews.llm.factory import get_llm, get_llm_config

    settings = get_settings()
    config = get_llm_config(settings)
    return get_llm(config)


def _parse_filter_response(text: str) -> dict[str, Any] | None:
    """Parse LLM filter response JSON."""
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


@node_resilient("filter")
def filter_node(state: GraphState) -> dict[str, Any]:
    """Score and filter articles by relevance.

    Parameters
    ----------
    state
        Current graph state with ``fetched_articles``.

    Returns
    -------
    dict
        Partial state with ``filtered_articles`` and updated ``loop_count``.
    """
    start = time.time()
    articles = state.get("fetched_articles", [])
    topics = state["params"]["topics"]
    loop_count = state.get("loop_count", 0)

    # H5 fix: on retry, skip articles whose URLs we already kept
    # in a previous filter pass to avoid operator.add duplicates.
    already_filtered = state.get("filtered_articles", [])
    seen_urls: set[str] = {a["url"] for a in already_filtered}
    articles = [a for a in articles if a["url"] not in seen_urls]

    llm = _get_llm()
    kept: list[Article] = []

    for article in articles:
        prompt = load_prompt(
            "filter",
            title=article["title"],
            content=article["content_md"][:2000],  # Truncate for token limit
            topics=topics,
        )

        try:
            response = limited_invoke_sync(llm, prompt)
            parsed = _parse_filter_response(response.content)

            if parsed and parsed.get("keep", False):
                article_copy = dict(article)
                article_copy["relevance_score"] = float(
                    parsed.get("score", article["relevance_score"])
                )
                kept.append(Article(**article_copy))  # type: ignore[typeddict-item]
            elif parsed is None:
                # On parse failure, keep if original score is decent
                if article["relevance_score"] >= _DEFAULT_THRESHOLD:
                    kept.append(article)
        except Exception as exc:
            logger.warning(
                "filter_article_error",
                url=article["url"],
                error=str(exc),
            )
            # On error, keep the article (fail-open)
            kept.append(article)

    logger.info(
        "filter_complete",
        input_count=len(articles),
        kept_count=len(kept),
        loop_count=loop_count + 1,
        skipped_duplicates=len(seen_urls),
    )

    return {
        "filtered_articles": kept,
        "loop_count": loop_count + 1,
        "metrics": track_metrics("filter", state, start_time=start),
    }


def filter_router(state: GraphState) -> str:
    """Conditional edge router after Filter node.

    Returns ``"planner"`` if too few articles kept and retries remain,
    otherwise ``"dedup"``.
    """
    filtered = state.get("filtered_articles", [])
    loop_count = state.get("loop_count", 0)

    if len(filtered) < _DEFAULT_MIN_KEPT and loop_count < 2:
        logger.info(
            "filter_retry",
            kept=len(filtered),
            loop_count=loop_count,
        )
        return "planner"

    return "dedup"
