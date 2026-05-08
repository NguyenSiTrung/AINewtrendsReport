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

- [ ] Task: Conductor - User Manual Verification 'Jinja2 Template & Writer Refactor' (Protocol in workflow.md)

## Phase 2: Markdown Exporter & Validation Schemas
<!-- depends: phase1 -->
<!-- execution: sequential -->

- [ ] Task 1: Create Pydantic validation schemas
  - [ ] `ReportOutput` in `src/ainews/schemas/report_output.py`: validates `report_md` non-empty, contains expected section markers
  - [ ] `XlsxOutput` in `src/ainews/schemas/report_output.py`: validates file path, file size > 0

- [ ] Task 2: Write tests for Markdown exporter (TDD)
  - [ ] Test file creation at `{reports_dir}/{run_id}/report.md`
  - [ ] Test directory auto-creation
  - [ ] Test returned path is absolute
  - [ ] Test Pydantic validation passes for valid output
  - [ ] Test Pydantic validation rejects empty `report_md`

- [ ] Task 3: Implement `exporters/markdown.py`
  - [ ] `export_markdown(report_md: str, run_id: str, reports_dir: Path) -> Path`
  - [ ] Create `{reports_dir}/{run_id}/` directory if not exists
  - [ ] Write `report.md` with UTF-8 encoding
  - [ ] Validate output with `ReportOutput` schema
  - [ ] Return absolute path

- [ ] Task: Conductor - User Manual Verification 'Markdown Exporter' (Protocol in workflow.md)

## Phase 3: Excel Exporter
<!-- depends: phase1 -->
<!-- execution: sequential -->

- [ ] Task 1: Write tests for xlsx builder (TDD)
  - [ ] Test workbook has 4 sheets: Summary, Stories, Sources, Trends
  - [ ] Test freeze panes on all sheets (row 2 frozen)
  - [ ] Test header row styling (bold, background color)
  - [ ] Test hyperlinks in Sources sheet URL column
  - [ ] Test auto-sized columns (capped at 80 chars)
  - [ ] Test edge cases: empty summaries, empty trends, long text truncation
  - [ ] Test file is valid xlsx (can be loaded back by openpyxl)

- [ ] Task 2: Implement `exporters/xlsx.py`
  - [ ] `export_xlsx(data: dict, run_id: str, reports_dir: Path) -> Path`
  - [ ] Summary sheet: metadata rows (date, topics, timeframe) + executive summary text
  - [ ] Stories sheet: headline, bullets (joined), why_it_matters, source_count columns
  - [ ] Sources sheet: URL (hyperlinked), title, cluster_id columns
  - [ ] Trends sheet: name, description, evidence_cluster_ids columns
  - [ ] Formatting constants extracted to module-level `STYLES` dict for future customization
  - [ ] Validate output with `XlsxOutput` schema
  - [ ] Return absolute path

- [ ] Task: Conductor - User Manual Verification 'Excel Exporter' (Protocol in workflow.md)

## Phase 4: Exporter Node & Graph Integration
<!-- depends: phase2, phase3 -->
<!-- execution: sequential -->

- [ ] Task 1: Extend GraphState
  - [ ] Add `xlsx_path: str` to `GraphState` in `agents/state.py`

- [ ] Task 2: Write tests for exporter node (TDD)
  - [ ] Test exporter node calls both markdown and xlsx exporters
  - [ ] Test exporter node returns `xlsx_path` and `metrics` in partial state
  - [ ] Test DB `reports` row is created with correct paths
  - [ ] Test `@node_resilient` error handling (export failure → error appended, no crash)

- [ ] Task 3: Implement `agents/nodes/exporter.py`
  - [ ] `exporter_node(state: GraphState) -> dict` decorated with `@node_resilient("exporter")`
  - [ ] Call `export_markdown()` and `export_xlsx()`
  - [ ] Create `Report` ORM row with `full_md_path`, `xlsx_path`, `title`, `summary_md`, `trends`
  - [ ] Return `{"xlsx_path": ..., "metrics": track_metrics(...)}`

- [ ] Task 4: Wire exporter into LangGraph
  - [ ] Import and register `exporter_node` in `agents/graph.py`
  - [ ] Add edge: Writer → Exporter → END
  - [ ] Update integration tests to verify full graph produces both files

- [ ] Task: Conductor - User Manual Verification 'Exporter Node & Graph Integration' (Protocol in workflow.md)

## Phase 5: Final Verification
<!-- depends: phase4 -->
<!-- execution: sequential -->

- [ ] Task 1: End-to-end validation
  - [ ] Run `make lint && make typecheck && make test`
  - [ ] Verify ≥ 80% test coverage on new modules
  - [ ] Verify `ainews run start --topic AI --days 3` produces both `.md` and `.xlsx` files

- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
