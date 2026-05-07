# Spec: Phase 0 — Foundations

## Overview

Scaffold the complete project skeleton for the AI News & Trends Report system. This track establishes the repository structure, dependency management, development tooling, configuration system, and CLI entry point — everything needed so that subsequent tracks can immediately start writing application code without boilerplate setup.

## Functional Requirements

### FR-1: Repository & Packaging
- Initialize a Python project with `pyproject.toml` managed by **uv**
- `requires-python = ">=3.12"`
- Package name: `ainews` (importable as `src/ainews/`)
- Use `src/` layout per Python packaging best practices
- Define `[project.scripts]` entry point: `ainews = "ainews.cli:app"`

### FR-2: Project Directory Structure
Create the skeleton directory layout matching PLAN.md §2.2:
```
ainews/
├── pyproject.toml
├── Makefile
├── .env.example
├── alembic/                        # placeholder (populated in Phase 1)
├── deploy/
│   ├── systemd/
│   ├── cron/
│   ├── nginx/
│   └── install.sh                  # placeholder
├── src/ainews/
│   ├── __init__.py
│   ├── core/                       # config, logging
│   │   ├── __init__.py
│   │   ├── config.py               # pydantic-settings
│   │   └── logging.py              # structlog setup
│   ├── models/                     # placeholder
│   ├── schemas/                    # placeholder
│   ├── api/
│   │   ├── routes/
│   │   └── templates/
│   ├── agents/
│   │   ├── nodes/
│   │   ├── tools/
│   │   └── prompts/
│   ├── llm/                        # placeholder
│   ├── tasks/                      # placeholder
│   ├── exporters/                  # placeholder
│   └── cli.py                      # Typer app
├── tests/
│   ├── conftest.py
│   └── test_cli.py
└── var/                            # local dev data directory
```

### FR-3: Development Tooling
- **Pre-commit** config (`.pre-commit-config.yaml`) with:
  - `ruff` (linting + formatting)
  - `mypy` (static type checking)
- **Makefile** with targets: `install`, `dev`, `lint`, `format`, `typecheck`, `test`, `pre-commit`, `clean`
- **ruff** config in `pyproject.toml` (line-length=88, target py312, isort rules)
- **mypy** config in `pyproject.toml` (strict mode, src layout)

### FR-4: Configuration System
- `pydantic-settings` `BaseSettings` class in `src/ainews/core/config.py`
- Settings schema covering all `AINEWS_*` env vars from PLAN.md §1.4:
  - `AINEWS_LLM_BASE_URL`, `AINEWS_LLM_API_KEY`, `AINEWS_LLM_MODEL`, `AINEWS_LLM_TEMPERATURE`, `AINEWS_LLM_MAX_TOKENS`, `AINEWS_LLM_TIMEOUT`, `AINEWS_LLM_EXTRA_HEADERS`
  - `AINEWS_DB_PATH` (default: `./var/ainews.db`)
  - `AINEWS_VALKEY_URL` (default: `redis://127.0.0.1:6379/0`)
  - `AINEWS_TAVILY_API_KEY`
  - `AINEWS_LOG_LEVEL` (default: `INFO`)
- `.env.example` documenting all variables with comments
- Reads from `.env` file in local dev; systemd `EnvironmentFile` in production

### FR-5: CLI Entry Point (Typer)
- `ainews --help` displays app name, version, and available command groups
- `ainews version` prints the package version
- Stub command groups: `ainews llm`, `ainews run`, `ainews seed` (no implementation yet — just defined so `--help` shows the intended structure)

### FR-6: Structured Logging
- `structlog` JSON logger configured in `src/ainews/core/logging.py`
- Log level controlled by `AINEWS_LOG_LEVEL` env var
- Adds standard context: timestamp, level, logger name

## Non-Functional Requirements

### NFR-1: All lints pass
- `ruff check .` — zero errors
- `ruff format --check .` — zero diffs
- `mypy src/` — zero errors

### NFR-2: Local dev requires no Docker
- `uv sync` + `.env` file is sufficient to run

### NFR-3: CI-ready
- Makefile targets can be used directly in CI pipelines

## Acceptance Criteria

1. `uv sync` installs all dependencies without errors
2. `ainews --help` outputs a well-formatted help message with version and command groups
3. `ainews version` prints the current package version
4. `ruff check . && ruff format --check . && mypy src/` all pass cleanly
5. `pytest tests/test_cli.py` passes with ≥1 test verifying CLI entry point
6. `.env.example` documents all `AINEWS_*` environment variables
7. `pre-commit run --all-files` passes
8. Directory structure matches PLAN.md §2.2 layout

## Out of Scope

- Database models / migrations (Phase 1)
- LLM factory implementation (Phase 2)
- Any agent nodes or tools (Phase 2-3)
- FastAPI app or routes (Phase 5)
- Admin UI templates (Phase 6)
- Deployment scripts implementation (Phase 7)
