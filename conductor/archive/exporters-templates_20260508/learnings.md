# Track Learnings: exporters-templates_20260508

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Build backend:** Use `hatchling.build` with `packages = ["src/ainews"]` for src/ layout
- **Makefile commands:** All commands use `uv run` prefix
- **ORM shared Base:** All models import from `ainews.models.base.Base`
- **UUID primary keys:** Store as `String(36)` with `default=lambda: str(uuid.uuid4())`
- **Lazy importing:** Use `TYPE_CHECKING` + lazy import for heavy deps
- **LangGraph custom dict reducers:** Nodes return only their specific updates for dict fields
- **LangGraph node decorator typing:** `@node_resilient` requires `# type: ignore[call-overload]` on `add_node()` calls
- **Test module collection:** Avoid naming source modules `test_*.py` in `src/`
- **Test class collection:** Avoid naming production classes `Test*`

---

<!-- Learnings from implementation will be appended below -->
