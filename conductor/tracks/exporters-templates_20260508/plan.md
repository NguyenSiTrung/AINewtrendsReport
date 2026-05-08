# Plan: Exporters & Report Templates (Phase 4)

Based on: `spec.md`
Workflow: TDD per `conductor/workflow.md`

---

## Phase 1: Jinja2 Report Template & Writer Refactor

- [x] Task 1: Create Jinja2 report template (commit: d291a8f)
  - [x] Create `src/ainews/agents/prompts/report.j2` with all report sections (header, exec summary, top stories, trends, source index, methodology, degradation notice)
  - [x] Template must accept: `title`, `generated_at`, `params`, `summaries`, `trends`, `errors`, `executive_summary`

- [x] Task 2: Write tests for writer refactor (TDD) (commit: d291a8f)
  - [x] Test that `writer_node` with template produces identical output to current hardcoded implementation for a known fixture
  - [x] Test degradation notice renders when `errors` is non-empty
  - [x] Test empty summaries edge case
  - [x] Test empty trends edge case

- [x] Task 3: Refactor `writer_node` to use Jinja2 template (commit: d291a8f)
  - [x] Replace hardcoded string assembly with `render_template("report", **context)` call
  - [x] Keep `_generate_executive_summary()` LLM logic unchanged
  - [x] Ensure all existing writer tests still pass (285 passed)

- [x] Task: Conductor - User Manual Verification 'Jinja2 Template & Writer Refactor' (verified: all 285 tests pass)

## Phase 2: Markdown Exporter & Validation Schemas
<!-- depends: phase1 -->
<!-- execution: sequential -->

- [x] Task 1: Create Pydantic validation schemas (commit: 3313f30)
  - [x] `ReportOutput` in `src/ainews/schemas/report_output.py`: validates `report_md` non-empty, contains expected section markers
  - [x] `XlsxOutput` in `src/ainews/schemas/report_output.py`: validates file path, file size > 0

- [x] Task 2: Write tests for Markdown exporter (TDD) (commit: 3313f30)
  - [x] Test file creation at `{reports_dir}/{run_id}/report.md`
  - [x] Test directory auto-creation
  - [x] Test returned path is absolute
  - [x] Test Pydantic validation passes for valid output
  - [x] Test Pydantic validation rejects empty `report_md`

- [x] Task 3: Implement `exporters/markdown.py` (commit: 3313f30)
  - [x] `export_markdown(report_md: str, run_id: str, reports_dir: Path) -> Path`
  - [x] Create `{reports_dir}/{run_id}/` directory if not exists
  - [x] Write `report.md` with UTF-8 encoding
  - [x] Validate output with `ReportOutput` schema
  - [x] Return absolute path

- [x] Task: Conductor - User Manual Verification 'Markdown Exporter' (verified: 10 tests pass, 100% coverage)

## Phase 3: Excel Exporter
<!-- depends: phase1 -->
<!-- execution: sequential -->

- [x] Task 1: Write tests for xlsx builder (TDD) (commit: 3313f30)
  - [x] Test workbook has 4 sheets: Summary, Stories, Sources, Trends
  - [x] Test freeze panes on all sheets (row 2 frozen)
  - [x] Test header row styling (bold, background color)
  - [x] Test hyperlinks in Sources sheet URL column
  - [x] Test auto-sized columns (capped at 80 chars)
  - [x] Test edge cases: empty summaries, empty trends, long text truncation
  - [x] Test file is valid xlsx (can be loaded back by openpyxl)

- [x] Task 2: Implement `exporters/xlsx.py` (commit: 3313f30)
  - [x] `export_xlsx(data: dict, run_id: str, reports_dir: Path) -> Path`
  - [x] Summary sheet: metadata rows (date, topics, timeframe) + executive summary text
  - [x] Stories sheet: headline, bullets (joined), why_it_matters, source_count columns
  - [x] Sources sheet: URL (hyperlinked), title, cluster_id columns
  - [x] Trends sheet: name, description, evidence_cluster_ids columns
  - [x] Formatting constants extracted to module-level `STYLES` dict for future customization
  - [x] Validate output with `XlsxOutput` schema
  - [x] Return absolute path

- [x] Task: Conductor - User Manual Verification 'Excel Exporter' (verified: 15 tests pass, 100% coverage)

## Phase 4: Exporter Node & Graph Integration
<!-- depends: phase2, phase3 -->
<!-- execution: sequential -->

- [x] Task 1: Extend GraphState (commit: a1a321b)
  - [x] Add `xlsx_path: str` to `GraphState` in `agents/state.py`

- [x] Task 2: Write tests for exporter node (TDD) (commit: a1a321b)
  - [x] Test exporter node calls both markdown and xlsx exporters
  - [x] Test exporter node returns `xlsx_path` and `metrics` in partial state
  - [x] Test DB `reports` row is created with correct paths
  - [x] Test `@node_resilient` error handling (export failure → error appended, no crash)

- [x] Task 3: Implement `agents/nodes/exporter.py` (commit: a1a321b)
  - [x] `exporter_node(state: GraphState) -> dict` decorated with `@node_resilient("exporter")`
  - [x] Call `export_markdown()` and `export_xlsx()`
  - [x] Create `Report` ORM row with `full_md_path`, `xlsx_path`, `title`, `summary_md`, `trends`
  - [x] Return `{"xlsx_path": ..., "metrics": track_metrics(...)}`

- [x] Task 4: Wire exporter into LangGraph (commit: a1a321b)
  - [x] Import and register `exporter_node` in `agents/graph.py`
  - [x] Add edge: Writer → Exporter → END
  - [x] Update all test files with new `xlsx_path` field

- [x] Task: Conductor - User Manual Verification 'Exporter Node & Graph Integration' (verified: 314 tests pass, 97% coverage, mypy clean)

## Phase 5: Final Verification
<!-- depends: phase4 -->
<!-- execution: sequential -->

- [x] Task 1: End-to-end validation
  - [x] Run `ruff check && mypy src/ && pytest --cov` — all pass
  - [x] Verify ≥ 80% test coverage on new modules (100% on exporters, 97% overall)
  - [x] Graph wiring verified: Writer → Exporter → END

- [x] Task: Conductor - User Manual Verification 'Final Verification' (all checks green)
