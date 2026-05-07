# Python Style Guide

## Tooling

- **Formatter/Linter:** ruff (replaces black + isort + flake8)
- **Type Checker:** mypy (strict mode)
- **Pre-commit:** Run ruff + mypy on every commit

## General Rules

- **Target:** Python 3.12+ (use modern syntax: `X | Y` unions, `match/case`, f-strings)
- **Line length:** 88 characters (ruff default)
- **Quotes:** Double quotes for strings
- **Imports:** Sorted by ruff (isort-compatible); stdlib → third-party → local

## Type Hints

- **All public functions** must have full type annotations (params + return)
- **Use `TypedDict`** for structured dicts (especially LangGraph state)
- **Use `Annotated[]`** for FastAPI dependency injection
- **Prefer `X | None`** over `Optional[X]`
- **Use `Self`** for class method return types

## Naming Conventions

| Item | Style | Example |
|------|-------|---------|
| Module | snake_case | `llm_factory.py` |
| Class | PascalCase | `ArticleFilter` |
| Function/Method | snake_case | `build_graph()` |
| Constant | UPPER_SNAKE | `MAX_RETRIES` |
| Type alias | PascalCase | `SearchHit` |
| Pydantic model | PascalCase | `SiteCreate` |
| SQLAlchemy model | PascalCase (singular) | `Article`, `Run` |
| Env var | UPPER_SNAKE with prefix | `AINEWS_LLM_BASE_URL` |

## Module Structure

```python
"""Module docstring — one-line summary.

Extended description if needed.
"""

from __future__ import annotations  # if needed for forward refs

# stdlib
import logging
from pathlib import Path

# third-party
from fastapi import APIRouter
from sqlalchemy.orm import Session

# local
from ainews.core.config import settings

logger = logging.getLogger(__name__)
```

## Function Design

- **Small functions** — each does one thing; max ~30 lines
- **Pure where possible** — LangGraph nodes are `(state) -> partial_state`
- **No mutable default arguments** — use `None` + conditional assignment
- **Docstrings:** Google style for public APIs; skip for trivial internal helpers

```python
def score_relevance(
    article: Article,
    topics: list[str],
    *,
    threshold: float = 0.5,
) -> RelevanceResult:
    """Score article relevance against target topics.

    Args:
        article: The article to score.
        topics: Target topic keywords.
        threshold: Minimum score to keep (default 0.5).

    Returns:
        RelevanceResult with score, keep flag, and reasoning.
    """
```

## Error Handling

- **Never bare `except:`** — always catch specific exceptions
- **LangGraph nodes:** Catch exceptions → append to `state["errors"]` → return partial state (never raise)
- **FastAPI routes:** Use `HTTPException` with appropriate status codes
- **Use `tenacity`** for retry/backoff on transient network errors

## Testing

- **Framework:** pytest
- **Structure:** Mirror `src/` layout under `tests/`
- **Naming:** `test_{module}.py` → `test_{function_name}()`
- **Fixtures:** Prefer function-scoped; use `conftest.py` for shared fixtures
- **Mocking:** `respx` for HTTP, `unittest.mock` for internal deps
- **Coverage target:** ≥ 80%

## Async Conventions

- **FastAPI routes:** `async def` by default
- **Scraper/HTTP calls:** `httpx.AsyncClient` with context manager
- **Celery tasks:** Synchronous (Celery doesn't natively support async workers)
- **LangGraph:** Sync nodes; async only if using `agraph.ainvoke()`
