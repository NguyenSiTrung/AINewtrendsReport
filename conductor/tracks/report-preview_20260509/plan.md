# Plan: Report Preview & Download

Track: `report-preview_20260509`

## Phase 1: Pipeline → Report Persistence

- [ ] Task 1: Add `markdown` dependency to `pyproject.toml`
  - [ ] Add `markdown>=3.7` to project dependencies
  - [ ] Run `uv sync` to install

- [ ] Task 2: Wire pipeline task to create Report row on completion
  - [ ] Write tests: verify `Report` row created with correct fields after successful run
  - [ ] Write tests: verify no `Report` row on failed run
  - [ ] Update `tasks/pipeline.py` to import Report model and exporters
  - [ ] After graph completes, call `export_markdown()` and `export_xlsx()`
  - [ ] Create `Report` row with `full_md_path`, `xlsx_path`, `summary_md`, `title`, `trends`, `token_usage`
  - [ ] Verify tests pass

- [ ] Task 3: Conductor - User Manual Verification 'Pipeline → Report Persistence' (Protocol in workflow.md)

## Phase 2: Report Summary Card on Run Detail

- [ ] Task 1: Add report query to run detail route
  - [ ] Write test: run detail page includes report summary when Report exists
  - [ ] Write test: run detail page shows no report section when Report is absent
  - [ ] Update `run_detail()` in `views.py` to query `Report` by `run_id`
  - [ ] Pass `report` object to template context

- [ ] Task 2: Create report summary card template
  - [ ] Add summary card section to `runs/detail.html`
  - [ ] Show title, summary snippet (truncated), story/trend counts
  - [ ] "View Full Report" button linking to `/runs/{run_id}/report`
  - [ ] Download buttons for `.md` and `.xlsx`
  - [ ] Only render when report exists

- [ ] Task 3: Conductor - User Manual Verification 'Report Summary Card' (Protocol in workflow.md)

## Phase 3: Report Preview Page & Download Endpoints

- [ ] Task 1: Create report preview route and template
  - [ ] Write test: `GET /runs/{run_id}/report` returns rendered HTML when report exists
  - [ ] Write test: returns 404/redirect when report missing
  - [ ] Write test: route requires auth
  - [ ] Add `GET /runs/{run_id}/report` route in `views.py`
  - [ ] Read markdown file from disk, convert to HTML via `markdown` library
  - [ ] Create `runs/report.html` template with styled reading container
  - [ ] Include back-link and download buttons in header

- [ ] Task 2: Create file download endpoints
  - [ ] Write test: `GET /runs/{run_id}/report/download/md` returns file with correct content-type
  - [ ] Write test: `GET /runs/{run_id}/report/download/xlsx` returns file with correct content-type
  - [ ] Write test: returns 404 when file missing on disk
  - [ ] Write test: routes require auth
  - [ ] Add both download routes using `FileResponse`
  - [ ] Set `Content-Disposition` header with proper filename

- [ ] Task 3: Style the report preview page
  - [ ] Add CSS for rendered markdown content (headings, lists, tables, code blocks)
  - [ ] Ensure responsive layout
  - [ ] Dark mode support consistent with admin theme

- [ ] Task 4: Conductor - User Manual Verification 'Report Preview & Downloads' (Protocol in workflow.md)

### Exit Criteria
- `ruff check . && ruff format --check . && mypy src/`
- `pytest --cov` — all tests pass, coverage ≥ 80%
- Manual verification: trigger a run, confirm report card appears, preview renders, downloads work
