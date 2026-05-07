# Track Learnings: foundations_20260507

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

No patterns yet — this is the first track. Patterns discovered here will seed `conductor/patterns.md`.

---

<!-- Learnings from implementation will be appended below -->

## [2026-05-07 22:34] - Phase 1-6: Full Foundations Implementation
- **Implemented:** Complete project scaffold — pyproject.toml (uv+hatchling), ruff/mypy/pytest config, pre-commit, Makefile, 13-package src/ tree, deploy skeleton, pydantic-settings config, structlog logging, Typer CLI with sub-apps
- **Files changed:** pyproject.toml, uv.lock, Makefile, .pre-commit-config.yaml, .env.example, .gitignore, src/ainews/ (16 files), tests/ (4 files), deploy/ (4 files), alembic/.gitkeep, var/.gitkeep
- **Commits:** 1c2b83d → 9b242e8 (8 commits)
- **Learnings:**
  - Patterns: hatchling build backend uses `hatchling.build` not `hatchling.backends`; hatch needs `packages = ["src/ainews"]` for src/ layout
  - Patterns: ruff needs `exclude = [".agents", ".beads", ".claude"]` to skip non-project dirs
  - Patterns: `var/.gitkeep` needs `git add -f` because parent dir is in .gitignore; adding `!var/.gitkeep` negation pattern
  - Gotchas: Python 3.14 is available on this system, but `requires-python >= 3.12` covers it
  - Context: All tests pass with 100% coverage on implemented modules (config, logging, cli)
---
