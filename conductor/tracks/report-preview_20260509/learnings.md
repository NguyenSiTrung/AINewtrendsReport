# Track Learnings: report-preview_20260509

Patterns, gotchas, and context discovered during implementation.

## Codebase Patterns (Inherited)

- **Starlette TemplateResponse API:** Use `TemplateResponse(request, name, context)` — not `(name, {request: ..., ...})`.
- **Auth gating pattern:** Use `_require_auth(request, session)` helper that returns `RedirectResponse` or sets `request.state.user`.
- **RunLog timestamp field:** The field is `ts`, not `created_at`. Templates and queries must use `RunLog.ts`.
- **FastAPI route ordering for path params:** Static routes like `/runs/table` must be registered BEFORE parameterized `/runs/{run_id}`.
- **CSRF double-submit cookie:** Middleware must NOT consume `request.body()` or `request.form()`.
- **Tailwind v4 standalone:** Uses CSS-based `@theme` and `@source` directives instead of `tailwind.config.js`.

---

## [2026-05-09 06:15] - Phase 1 Task 1-2: Add markdown dependency & wire pipeline report persistence
- **Implemented:** Added `markdown>=3.7` to dependencies, updated `pipeline.py` to create Report rows on successful pipeline completion
- **Files changed:** `pyproject.toml`, `src/ainews/tasks/pipeline.py`, `tests/test_report_preview.py`
- **Commit:** 5e21476
- **Learnings:**
  - Patterns: Report persistence uses `_persist_report()` helper with try/catch to avoid blocking the pipeline on export failures
  - Patterns: `_extract_title()` and `_extract_summary()` parse markdown headings to populate Report metadata
  - Gotchas: `export_markdown` and `export_xlsx` are imported at module level (not lazily) since they're always needed on success path
  - Context: Report.trends is a JSON column — pass Python list directly, NOT `json.dumps()` string

## [2026-05-09 06:18] - Phase 2 Task 1-2: Report summary card on run detail
- **Implemented:** Updated `run_detail()` to query Report, added conditional summary card template section
- **Files changed:** `src/ainews/api/routes/views.py`, `src/ainews/api/templates/runs/detail.html`
- **Commit:** 5e21476
- **Learnings:**
  - Patterns: `report` variable is passed to template and conditionally rendered with `{% if report %}`
  - Gotchas: When inserting test data with FK constraints, must commit parent (Run) before child (Report) in separate sessions
  - Context: Summary card includes "View Full Report" link, .md and .xlsx download buttons

## [2026-05-09 06:20] - Phase 3 Task 1-3: Report preview page & download endpoints
- **Implemented:** New route `GET /runs/{run_id}/report` converts MD→HTML, download endpoints for .md/.xlsx via FileResponse
- **Files changed:** `src/ainews/api/routes/views.py`, `src/ainews/api/templates/runs/report.html`
- **Commit:** 5e21476
- **Learnings:**
  - Patterns: Use `markdown.markdown(raw_md, extensions=["tables", "fenced_code", "codehilite", "toc"])` for full-featured rendering
  - Patterns: Download endpoints return `JSONResponse(status_code=404)` for missing files, not redirects
  - Patterns: `FileResponse` with `filename=` parameter auto-sets Content-Disposition header
  - Gotchas: `import markdown as md_lib` inside the route function to avoid importing at module level (lazy import pattern)
  - Context: Report preview template includes comprehensive CSS for markdown rendering with dark mode support
---
