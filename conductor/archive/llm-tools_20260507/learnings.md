# Track Learnings: llm-tools_20260507

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Build backend:** Use `hatchling.build` (not `hatchling.backends`) with `packages = ["src/ainews"]` for src/ layout
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings` `SettingsConfigDict(env_prefix="AINEWS_")`
- **Makefile commands:** All commands use `uv run` prefix (e.g., `uv run ruff check .`, `uv run pytest --cov`)
- **SQLAlchemy engine factory:** Use a custom `create_engine(url)` wrapping `event.listen(engine, "connect", handler)` to apply SQLite pragmas
- **ORM shared Base:** All models import from `ainews.models.base.Base`
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`
- **pre-commit mypy deps:** When adding new runtime packages, also add them to `additional_dependencies` in the `mirrors-mypy` hook
- **Ruff SIM117:** Flatten nested `with` statements — `with pytest.raises(...), ctx_mgr as x:` pattern
- **CliRunner env injection:** `CliRunner` from `typer.testing` supports `env={"KEY": "value"}` to inject env vars
- **Typer sub-app invoke:** Use `invoke_without_command=True` + `@app.callback(invoke_without_command=True)` for direct sub-app commands

---

<!-- Learnings from implementation will be appended below -->

## [2026-05-08 00:14] - Phase 1: LLM Client Foundation

- **Implemented:** LLMConfig frozen model, get_llm_config 3-layer resolver, get_llm ChatOpenAI factory, check_llm_connection httpx probe, `ainews llm test` CLI command
- **Files changed:** `src/ainews/llm/config.py`, `src/ainews/llm/factory.py`, `src/ainews/llm/connectivity.py`, `src/ainews/cli.py`, `tests/llm/test_config.py`, `tests/llm/test_factory.py`, `tests/llm/test_connection.py`, `tests/test_cli.py`, `pyproject.toml`, `.pre-commit-config.yaml`
- **Commits:** d1153e1, b6cfb0b, 10a1b00, c70524b, dc1589c, 5a94ca7
- **Learnings:**
  - Patterns: Naming source modules `test_*.py` in `src/` causes pytest to collect them — rename to avoid (e.g. `connectivity.py` instead of `test_connection.py`)
  - Patterns: Similarly, classes named `Test*` in production code (like `TestResult`) get collected by pytest — use `ConnectionTestResult` to avoid collision
  - Patterns: Use `TYPE_CHECKING` + lazy import for heavy deps like `langchain_openai.ChatOpenAI` — keeps module load fast and allows mypy type checking
  - Patterns: `respx.mock` decorator works cleanly for httpx-based connection tests; for CliRunner tests use `with respx.mock:` context manager
  - Gotchas: ruff format auto-fixes on commit can cause first commit to fail — always re-add and retry
  - Context: `ChatOpenAI` attributes: `openai_api_base`, `model_name`, `temperature`, `max_tokens`, `request_timeout`, `default_headers`
---

