# Development Workflow

## Commit Strategy

- **Frequency:** Commit after each completed task
- **Format:** `conductor(<track_id>): <task description>`
- **Scope:** Each commit should be atomic — one task, one commit
- **Notes:** Use `git notes` for task summaries and metadata

## Test Coverage

- **Target:** ≥ 80% line coverage
- **Enforcement:** Measure with `pytest --cov` before marking a task complete
- **Pyramid:** Unit tests > Integration tests > E2E tests
- **Pattern:** Arrange-Act-Assert (AAA)

## Task Execution Protocol

1. **Read** the task description and acceptance criteria
2. **Write tests first** (TDD when applicable)
3. **Implement** the minimum code to pass tests
4. **Refactor** if needed while keeping tests green
5. **Run lints:** `ruff check . && ruff format --check . && mypy src/`
6. **Run tests:** `pytest --cov`
7. **Commit** with the conductor format
8. **Update** task status in plan.md

## Phase Verification

At the end of each phase:
1. All phase tasks must be `[x]` checked
2. Run the phase's **Exit Criteria** (defined in plan.md)
3. Complete the **User Manual Verification** task
4. User confirms phase completion before proceeding

## Branch Strategy

- **Main branch:** `main` — always deployable
- **Feature branches:** `conductor/<track_id>` — one branch per track
- **Merge:** Squash merge recommended for clean history

## Code Review Checklist

Before marking a task complete:
- [ ] Tests pass (`pytest`)
- [ ] Lints pass (`ruff check .`)
- [ ] Types pass (`mypy src/`)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling follows node pattern (catch → append to errors → return partial state)
- [ ] Docstrings on public APIs

## Environment Management

- **Dev:** Local SQLite at `./var/ainews.db`, `.env` file for config
- **Staging/Prod:** `/var/lib/ainews/ainews.db`, systemd `EnvironmentFile`
- **Dependencies:** Managed via `pyproject.toml` (uv or pip-tools)
