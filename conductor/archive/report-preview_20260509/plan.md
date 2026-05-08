# Plan: Report Preview & Download

Track: `report-preview_20260509`

## Phase 1: Pipeline → Report Persistence

- [x] Task 1: Add `markdown` dependency to `pyproject.toml`
  - [x] Add `markdown>=3.7` to project dependencies
  - [x] Run `uv sync` to install

- [x] Task 2: Wire pipeline task to create Report row on completion
  - [x] Write tests: verify `Report` row created with correct fields after successful run
  - [x] Write tests: verify no `Report` row on failed run
  - [x] Update `tasks/pipeline.py` to import Report model and exporters
  - [x] After graph completes, call `export_markdown()` and `export_xlsx()`
  - [x] Create `Report` row with `full_md_path`, `xlsx_path`, `summary_md`, `title`, `trends`, `token_usage`
  - [x] Verify tests pass

- [x] Task 3: Conductor - Phase 1 verified (all tests pass, lint clean)

## Phase 2: Report Summary Card on Run Detail

- [x] Task 1: Add report query to run detail route
  - [x] Write test: run detail page includes report summary when Report exists
  - [x] Write test: run detail page shows no report section when Report is absent
  - [x] Update `run_detail()` in `views.py` to query `Report` by `run_id`
  - [x] Pass `report` object to template context

- [x] Task 2: Create report summary card template
  - [x] Add summary card section to `runs/detail.html`
  - [x] Show title, summary snippet (truncated), story/trend counts
  - [x] "View Full Report" button linking to `/runs/{run_id}/report`
  - [x] Download buttons for `.md` and `.xlsx`
  - [x] Only render when report exists

- [x] Task 3: Conductor - Phase 2 verified (all tests pass, lint clean)

## Phase 3: Report Preview Page & Download Endpoints

- [x] Task 1: Create report preview route and template
  - [x] Write test: `GET /runs/{run_id}/report` returns rendered HTML when report exists
  - [x] Write test: returns 404/redirect when report missing
  - [x] Write test: route requires auth
  - [x] Add `GET /runs/{run_id}/report` route in `views.py`
  - [x] Read markdown file from disk, convert to HTML via `markdown` library
  - [x] Create `runs/report.html` template with styled reading container
  - [x] Include back-link and download buttons in header

- [x] Task 2: Create file download endpoints
  - [x] Write test: `GET /runs/{run_id}/report/download/md` returns file with correct content-type
  - [x] Write test: `GET /runs/{run_id}/report/download/xlsx` returns file with correct content-type
  - [x] Write test: returns 404 when file missing on disk
  - [x] Write test: routes require auth
  - [x] Add both download routes using `FileResponse`
  - [x] Set `Content-Disposition` header with proper filename

- [x] Task 3: Style the report preview page
  - [x] Add CSS for rendered markdown content (headings, lists, tables, code blocks)
  - [x] Ensure responsive layout
  - [x] Dark mode support consistent with admin theme

- [x] Task 4: Conductor - All phases verified

### Exit Criteria
- `ruff check . && ruff format --check . && mypy src/`
- `pytest --cov` — all tests pass, coverage ≥ 80%
- Manual verification: trigger a run, confirm report card appears, preview renders, downloads work
