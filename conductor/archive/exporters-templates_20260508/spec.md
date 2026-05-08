# Spec: Exporters & Report Templates (Phase 4)

## Overview

Implement the Exporters module and Jinja2 report templates for the AI News & Trends pipeline. This phase bridges the gap between the Writer node's in-memory `report_md` output and persistent, validated report files on disk (`.md` + `.xlsx`), completing the graph's final stage (Writer → Exporter → END).

## Functional Requirements

### FR-1: Jinja2 Markdown Report Template
- Extract the hardcoded Markdown structure from `writer_node` into a Jinja2 template (`agents/prompts/report.j2`).
- Template sections: Header (title, date, params), Executive Summary, Top Stories (per-cluster), Key Trends, Source Index, Methodology footer.
- Degradation notice block when `errors` is non-empty.
- Refactored `writer_node` must produce byte-identical output to the current implementation for the same input.

### FR-2: Markdown Exporter (`exporters/markdown.py`)
- Accept `report_md` string and `run_id`.
- Write to `{reports_dir}/{run_id}/report.md`.
- Create directory if not exists.
- Return the absolute file path.

### FR-3: Excel Exporter (`exporters/xlsx.py`)
- Accept structured data (summaries, trends, articles/sources, params, run metadata).
- Build an openpyxl workbook with 4 sheets:
  - **Summary** — Executive summary text, report metadata (date, topics, timeframe).
  - **Stories** — One row per story: headline, bullets (joined), why_it_matters, source count.
  - **Sources** — One row per source URL across all stories: URL (hyperlinked), title, cluster_id.
  - **Trends** — One row per trend: name, description, evidence cluster IDs.
- Formatting: freeze top row on all sheets, auto-sized columns (capped at 80 chars), bold + colored header row, hyperlinked URLs in Sources sheet.
- Return the absolute file path.

### FR-4: Exporter Graph Node (`agents/nodes/exporter.py`)
- New LangGraph node wired after Writer, before END.
- Reads `report_md`, `summaries`, `trends`, `filtered_articles`, `params`, `run_id` from state.
- Calls Markdown exporter and Excel exporter.
- Registers file paths in the `reports` DB table (via SQLAlchemy ORM).
- Returns partial state: `xlsx_path`, `metrics`.
- Uses `@node_resilient` decorator for error handling.

### FR-5: GraphState Extension
- Add `xlsx_path: str` to `GraphState` TypedDict.

### FR-6: Pydantic Validation Schemas
- `ReportOutput` schema: validates report_md is non-empty, has expected sections (header, executive summary, methodology).
- `XlsxOutput` schema: validates file path exists, file size > 0.
- Validation runs inside the exporter node before returning.

## Non-Functional Requirements

- **No LLM calls** in any exporter (all LLM work is done in Writer).
- **Deterministic output** — same input always produces same xlsx structure.
- **Performance** — Export of 50-story report completes in < 5 seconds.
- **Extensibility** — xlsx formatting constants extracted to a config dict for easy future customization.

## Acceptance Criteria

1. `writer_node` uses `report.j2` template and produces identical Markdown output for the same input.
2. Running a full graph produces both `report.md` and `report.xlsx` in `{reports_dir}/{run_id}/`.
3. The xlsx file opens correctly in LibreOffice Calc with 4 sheets, frozen panes, auto-sized columns, and clickable hyperlinks.
4. Pydantic validation catches malformed outputs (tested with edge cases: empty summaries, missing trends).
5. `reports` DB row is created with valid `full_md_path` and `xlsx_path`.
6. All tests pass: `pytest tests/exporters/` green, ≥ 80% coverage.
7. `make lint && make typecheck && make test` all green.

## Out of Scope

- PDF export (potential v2 feature).
- Customizable template selection via admin UI (Phase 6).
- Chart/visualization sheets in xlsx (future enhancement per user request).
- Email/Slack delivery of reports.
