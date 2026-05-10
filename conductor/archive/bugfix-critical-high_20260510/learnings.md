# Track Learnings: bugfix-critical-high_20260510

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **ContextVar for per-task state:** Use `contextvars.ContextVar` instead of module globals when Celery tasks may run concurrently in the same process.
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()` — compare header/cookie values instead.
- **Decorator-level DB logging:** `@node_resilient` handles logging automatically — don't duplicate in individual nodes.
- **Non-blocking persistence:** Use try/catch for artifact persistence to avoid failing the core pipeline.
- **SQLAlchemy engine factory:** Custom `create_engine(url)` with event listener for SQLite pragmas; `StaticPool` for in-memory URLs.
- **DB Session Manager:** `get_db_session(engine)` follows commit-on-success / rollback-on-exception / always-close.

---

<!-- Learnings from implementation will be appended below -->
