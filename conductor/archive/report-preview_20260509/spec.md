# Spec: Report Preview & Download

## Overview

When a pipeline run completes, the admin should be able to preview the generated
Markdown report as rendered HTML and download both the `.md` and `.xlsx` files
directly from the admin web interface. Currently the pipeline task does not
persist report artifacts to the `reports` table, and the run detail page has no
report-related UI.

## Functional Requirements

### FR-1: Wire Pipeline Output → Report Table
- After the graph completes successfully, create a `Report` row linked to the run.
- Populate `full_md_path`, `xlsx_path`, `summary_md`, `title`, and `trends` from
  the graph result state (`report_md`, `xlsx_path`, `summaries`, `trends`).
- Store `created_at` timestamp on the Report row.

### FR-2: Report Summary Card on Run Detail Page
- When viewing `/runs/{run_id}`, if a completed run has an associated `Report`,
  display a summary card showing:
  - Report title (or "AI News Report — {date}")
  - Executive summary snippet (first ~200 chars of `summary_md`)
  - Story count and trend count
  - "View Full Report" button → links to `/runs/{run_id}/report`
  - Download buttons for `.md` and `.xlsx`

### FR-3: Dedicated Report Preview Page
- New route: `GET /runs/{run_id}/report`
- Reads the Markdown file from `Report.full_md_path`
- Converts Markdown → HTML server-side using the `markdown` Python library
- Renders inside a styled reading container within the admin layout
- Back link to run detail page
- Download buttons (.md + .xlsx) in the page header

### FR-4: File Download Endpoints
- `GET /runs/{run_id}/report/download/md` — serves the `.md` file via `FileResponse`
- `GET /runs/{run_id}/report/download/xlsx` — serves the `.xlsx` file via `FileResponse`
- Both return 404 if file doesn't exist on disk
- Content-Disposition header for proper filename

### FR-5: Dependency Addition
- Add `markdown` (BSD license) to `pyproject.toml` dependencies

## Non-Functional Requirements

- Server-side rendering only — no client-side JS libraries for markdown
- File downloads must be auth-gated (same `_require_auth` pattern)
- Report page must be responsive and readable on all screen sizes
- Handle edge cases: run not completed, report file missing from disk

## Acceptance Criteria

1. A completed pipeline run creates a `Report` row with valid file paths
2. Run detail page shows summary card with download buttons when report exists
3. `/runs/{run_id}/report` renders the full markdown as styled HTML
4. `.md` and `.xlsx` downloads work and return correct content types
5. All new routes are auth-protected
6. Missing report/files show appropriate error messages
7. Tests cover: report creation in pipeline, download endpoints, preview rendering

## Out of Scope

- PDF export (future enhancement)
- Report editing from the admin UI
- Report comparison between runs
- Email delivery of reports
