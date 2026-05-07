# Plan: Phase 0 — Foundations

## Phase 1: Project Packaging & Tooling
<!-- execution: sequential -->

- [ ] Task 1: Initialize `pyproject.toml` with uv
  <!-- files: pyproject.toml, uv.lock -->
  - [ ] Create `pyproject.toml` with package metadata (name=ainews, version=0.1.0, requires-python>=3.12)
  - [ ] Define `[project.scripts]` entry point: `ainews = "ainews.cli:app"`
  - [ ] Add core dependencies: typer, pydantic-settings, structlog
  - [ ] Add dev dependencies: ruff, mypy, pytest, pytest-cov, pre-commit
  - [ ] Run `uv sync` to verify lock + install

- [ ] Task 2: Configure linting, formatting, and type checking
  <!-- files: pyproject.toml -->
  <!-- depends: task1 -->
  - [ ] Add `[tool.ruff]` config: line-length=88, target-version=py312, isort rules, select rules
  - [ ] Add `[tool.mypy]` config: strict=true, packages=ainews
  - [ ] Add `[tool.pytest.ini_options]` config: testpaths, cov settings

- [ ] Task 3: Create pre-commit configuration
  <!-- files: .pre-commit-config.yaml -->
  <!-- depends: task2 -->
  - [ ] Create `.pre-commit-config.yaml` with ruff (lint + format) and mypy hooks
  - [ ] Verify `pre-commit run --all-files` passes

- [ ] Task 4: Create Makefile
  <!-- files: Makefile -->
  <!-- depends: task2 -->
  - [ ] Targets: `install`, `dev`, `lint`, `format`, `typecheck`, `test`, `pre-commit`, `clean`
  - [ ] Verify `make lint`, `make typecheck`, `make test` run correctly

## Phase 2: Directory Structure & Skeleton Modules
<!-- execution: parallel -->
<!-- depends: phase1 -->

- [ ] Task 1: Create source directory tree
  <!-- files: src/ainews/__init__.py, src/ainews/core/__init__.py, src/ainews/models/__init__.py, src/ainews/schemas/__init__.py, src/ainews/api/__init__.py, src/ainews/api/routes/__init__.py, src/ainews/agents/__init__.py, src/ainews/agents/nodes/__init__.py, src/ainews/agents/tools/__init__.py, src/ainews/agents/prompts/__init__.py, src/ainews/llm/__init__.py, src/ainews/tasks/__init__.py, src/ainews/exporters/__init__.py -->

- [ ] Task 2: Create deployment skeleton
  <!-- files: deploy/systemd/, deploy/cron/, deploy/nginx/, deploy/install.sh, alembic/ -->

- [ ] Task 3: Create local dev data directory
  <!-- files: var/.gitkeep, .gitignore -->

## Phase 3: Configuration System
<!-- execution: sequential -->
<!-- depends: phase2 -->

- [ ] Task 1: Implement pydantic-settings config (TDD)
  <!-- files: src/ainews/core/config.py, tests/test_config.py -->
  - [ ] Write tests for `Settings` class: default values, env var override, .env file loading
  - [ ] Implement `src/ainews/core/config.py` with `Settings(BaseSettings)`:
    - LLM settings: `llm_base_url`, `llm_api_key`, `llm_model`, `llm_temperature`, `llm_max_tokens`, `llm_timeout`, `llm_extra_headers`
    - DB: `db_path` (default `./var/ainews.db`)
    - Valkey: `valkey_url` (default `redis://127.0.0.1:6379/0`)
    - Tavily: `tavily_api_key`
    - Logging: `log_level` (default `INFO`)
  - [ ] All tests pass

- [ ] Task 2: Create `.env.example`
  <!-- files: .env.example -->
  <!-- depends: task1 -->
  - [ ] Document all `AINEWS_*` variables with descriptive comments
  - [ ] Include sensible defaults where applicable
  - [ ] Add section headers for grouping (LLM, Database, Cache, Search, Logging)

## Phase 4: Structured Logging
<!-- execution: sequential -->
<!-- depends: phase3 -->

- [ ] Task 1: Implement structlog configuration (TDD)
  <!-- files: src/ainews/core/logging.py, tests/test_logging.py -->
  - [ ] Write tests: logger outputs JSON, respects log level, includes standard context (timestamp, level, logger)
  - [ ] Implement `src/ainews/core/logging.py` with `setup_logging(level: str)` function
  - [ ] Integrate with Settings to read `AINEWS_LOG_LEVEL`
  - [ ] All tests pass

## Phase 5: CLI Entry Point & Finishing Touches
<!-- execution: parallel -->
<!-- depends: phase4 -->

- [ ] Task 1: Implement Typer CLI app (TDD)
  <!-- files: src/ainews/cli.py, tests/test_cli.py -->
  - [ ] Write tests: `ainews --help` exits 0 with expected output, `ainews version` prints version
  - [ ] Implement `src/ainews/cli.py` with Typer app:
    - Root app with `ainews --help` showing app name + version
    - `ainews version` command
    - Stub sub-apps: `llm`, `run`, `seed` (empty groups with help text)
  - [ ] All tests pass

- [ ] Task 2: Create `.gitignore`
  <!-- files: .gitignore -->
  - [ ] Python ignores: `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`
  - [ ] Env: `.env`, `*.env` (but not `.env.example`)
  - [ ] IDE: `.vscode/`, `.idea/`
  - [ ] Data: `var/` contents (except `.gitkeep`), `*.db`
  - [ ] Build: `dist/`, `*.egg-info/`

## Phase 6: Verification & Exit Criteria
<!-- execution: sequential -->
<!-- depends: phase5 -->

- [ ] Task 1: Full integration verification
  - [ ] `uv sync` completes without errors
  - [ ] `ainews --help` displays formatted help with version and command groups
  - [ ] `ainews version` prints correct version
  - [ ] `make lint` passes (ruff check + format check)
  - [ ] `make typecheck` passes (mypy)
  - [ ] `make test` passes with ≥80% coverage on implemented modules
  - [ ] `pre-commit run --all-files` passes
  - [ ] Directory structure matches PLAN.md §2.2

- [ ] Task: Conductor - User Manual Verification 'Phase 6: Verification & Exit Criteria' (Protocol in workflow.md)
