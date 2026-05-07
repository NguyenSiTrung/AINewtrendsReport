# Codebase Patterns

Reusable patterns discovered during development. Read this before starting new work.

---

- **Build backend:** Use `hatchling.build` (not `hatchling.backends`) with `packages = ["src/ainews"]` for src/ layout (from: foundations_20260507, 2026-05-07)
- **Ruff excludes:** Add `exclude = [".agents", ".beads", ".claude", "alembic"]` to `[tool.ruff]` to skip non-project directories (from: foundations_20260507, 2026-05-07)
- **Gitignore negation:** When a parent dir is ignored (e.g. `var/`), use `!var/.gitkeep` negation pattern and `git add -f` to force-track the gitkeep (from: foundations_20260507, 2026-05-07)
- **Config env prefix:** All settings use `AINEWS_*` prefix via `pydantic-settings` `SettingsConfigDict(env_prefix="AINEWS_")` (from: foundations_20260507, 2026-05-07)
- **Makefile commands:** All commands use `uv run` prefix (e.g., `uv run ruff check .`, `uv run pytest --cov`) (from: foundations_20260507, 2026-05-07)
