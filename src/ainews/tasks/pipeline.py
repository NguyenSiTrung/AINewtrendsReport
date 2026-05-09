"""Celery task: run_pipeline — executes the LangGraph pipeline asynchronously.

This task is enqueued by the shared service layer and picks up a Run by
``run_id``, transitions its status through ``pending → running → completed``
(or ``failed``), and persists metrics/errors to the database.
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from ainews.core.config import Settings
from ainews.core.database import create_engine, get_db_session
from ainews.exporters.markdown import export_markdown
from ainews.exporters.xlsx import export_xlsx
from ainews.models.report import Report
from ainews.models.run import Run
from ainews.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="ainews.run_pipeline", max_retries=0)  # type: ignore[misc]
def run_pipeline(self: Any, run_id: str) -> dict[str, Any]:
    """Execute the LangGraph pipeline for a given run.

    Parameters
    ----------
    run_id:
        UUID of the Run row in the database.

    Returns
    -------
    dict with ``status`` and summary info.
    """
    from ainews.agents.graph import build_graph
    from ainews.agents.resilience import set_logging_engine
    from ainews.agents.state import GraphState, RunParams
    from ainews.services.run_logger import log_to_db

    settings = Settings()
    engine = create_engine(settings.database_url)

    # Share this engine with @node_resilient so all nodes can log
    set_logging_engine(engine)

    # ── Capture raw worker output to file ─────────────────
    raw_log_handler: logging.FileHandler | None = None
    try:
        logs_dir = settings.db_path.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        raw_log_path = logs_dir / f"{run_id}.log"
        raw_log_handler = logging.FileHandler(str(raw_log_path), encoding="utf-8")
        raw_log_handler.setLevel(logging.DEBUG)
        raw_log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(raw_log_handler)
    except Exception:
        raw_log_handler = None  # Non-fatal; proceed without capture

    log = logger.bind(run_id=run_id)
    log.info("run_pipeline.start")

    # ── Load Run row ──────────────────────────────────────
    with get_db_session(engine) as session:
        run = session.get(Run, run_id)
        if run is None:
            log.error("run_pipeline.not_found")
            engine.dispose()
            return {"status": "error", "detail": "Run not found"}

        run.status = "running"
        run.started_at = datetime.now(tz=UTC).isoformat()
        session.flush()

        # Resolve params
        schedule_id = run.schedule_id
        input_params: dict[str, Any] = run.input_params or {}

    # Log pipeline start
    log_to_db(engine, run_id, "pipeline", "INFO", "Pipeline started")

    # ── Resolve schedule if needed ────────────────────────
    topics: list[str] = input_params.get("topics", [])
    sites: list[str] = input_params.get("sites", [])
    timeframe_days: int = input_params.get("timeframe_days", 7)

    if schedule_id is not None:
        from ainews.models.schedule import Schedule

        with get_db_session(engine) as session:
            schedule = session.get(Schedule, schedule_id)
            if schedule is not None:
                topics = topics or (schedule.topics or [])
                timeframe_days = schedule.timeframe_days
                if schedule.site_filter:
                    sites = sites or schedule.site_filter

    # Fallback: if no sites are specified, use all sites from the database
    if not sites:
        import urllib.parse

        from sqlalchemy import select

        from ainews.models.site import Site

        with get_db_session(engine) as session:
            all_urls = session.execute(select(Site.url)).scalars().all()
            # Extract just the domain from the URLs for Tavily
            parsed_domains = [
                urllib.parse.urlparse(url).netloc for url in all_urls if url
            ]
            # Remove any empty strings and www. prefix for better matching
            sites = list({d.removeprefix("www.") for d in parsed_domains if d})

    # ── Build and invoke graph ────────────────────────────
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        checkpoint_db = str(settings.db_path.parent / f"checkpoint_{run_id}.db")

        # Resolve report_max_sources (DB pipeline settings override env)
        report_max_sources: int = settings.report_max_sources
        from ainews.models.settings_kv import SettingsKV

        with get_db_session(engine) as session:
            pipeline_row = session.get(SettingsKV, "pipeline")
            if pipeline_row and isinstance(pipeline_row.value, dict):
                db_max = pipeline_row.value.get("report_max_sources")
                if db_max is not None:
                    report_max_sources = int(db_max)

        params = RunParams(
            timeframe_days=timeframe_days,
            topics=topics,
            sites=sites,
            use_smart_planner=input_params.get("use_smart_planner", True),
            report_max_sources=report_max_sources,
        )

        initial_state: GraphState = {
            "run_id": run_id,
            "params": params,
            "queries": [],
            "raw_results": [],
            "fetched_articles": [],
            "filtered_articles": [],
            "clusters": [],
            "summaries": [],
            "trends": [],
            "report_md": "",
            "xlsx_path": "",
            "errors": [],
            "metrics": {},
            "loop_count": 0,
        }

        with SqliteSaver.from_conn_string(checkpoint_db) as cp:
            graph = build_graph(checkpointer=cp)
            config = {"configurable": {"thread_id": run_id}}
            result = graph.invoke(initial_state, config)

        # ── Export reports & persist Report row ────────────
        reports_dir = settings.db_path.parent / "reports"
        _persist_report(engine, run_id, result, reports_dir, log)

        # ── Determine final status ────────────────────────
        node_errors = result.get("errors", [])
        if node_errors:
            final_status = "completed_with_errors"
            error_nodes = ", ".join(
                {e.node for e in node_errors if hasattr(e, "node")}
            )
            error_summary = (
                f"{len(node_errors)} node error(s) in: {error_nodes}"
                if error_nodes
                else f"{len(node_errors)} node error(s)"
            )
        else:
            final_status = "completed"
            error_summary = None

        # ── Update Run ────────────────────────────────────
        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            if run is not None:
                run.status = final_status
                run.finished_at = datetime.now(tz=UTC).isoformat()
                run.stats = result.get("metrics", {})
                if error_summary:
                    run.error = error_summary

        log_to_db(
            engine,
            run_id,
            "pipeline",
            "WARNING" if node_errors else "INFO",
            f"Pipeline {final_status}" + (f" — {error_summary}" if error_summary else ""),
        )
        log.info("run_pipeline.completed", status=final_status)
        return {"status": final_status, "run_id": run_id}

    except Exception as exc:
        tb = traceback.format_exc()
        log.error("run_pipeline.failed", error=str(exc), traceback=tb)

        log_to_db(
            engine,
            run_id,
            "pipeline",
            "ERROR",
            f"Pipeline failed: {exc}",
        )

        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(tz=UTC).isoformat()
                run.error = str(exc)

        return {"status": "failed", "run_id": run_id, "error": str(exc)}

    finally:
        # Remove the per-run file handler
        if raw_log_handler is not None:
            try:
                logging.getLogger().removeHandler(raw_log_handler)
                raw_log_handler.close()
            except Exception:
                pass
        engine.dispose()


def _persist_report(
    engine: Any,
    run_id: str,
    result: dict[str, Any],
    reports_dir: Path,
    log: Any,
) -> None:
    """Export MD/XLSX and create a Report row in the database."""
    try:
        report_md: str = result.get("report_md", "")
        summaries: list[dict[str, Any]] = result.get("summaries", [])
        trends: list[dict[str, Any]] = result.get("trends", [])

        # Export files
        md_path = export_markdown(report_md, run_id, reports_dir)
        xlsx_data = {
            "summaries": summaries,
            "trends": trends,
            "executive_summary": report_md[:500] if report_md else "",
            "params": {},
            "generated_at": datetime.now(tz=UTC).isoformat(),
        }
        xlsx_path = export_xlsx(xlsx_data, run_id, reports_dir)

        # Build title from first markdown heading or fallback
        title = _extract_title(report_md)

        # Extract summary snippet
        summary_md = _extract_summary(report_md)

        with get_db_session(engine) as session:
            report = Report(
                run_id=run_id,
                title=title,
                summary_md=summary_md,
                full_md_path=str(md_path),
                xlsx_path=str(xlsx_path),
                trends=trends,
                token_usage=result.get("metrics", {}).get("token_usage"),
                created_at=datetime.now(tz=UTC).isoformat(),
            )
            session.add(report)

        log.info("run_pipeline.report_persisted", run_id=run_id)

    except Exception as exc:
        # Report persistence failure should not fail the pipeline
        log.warning(
            "run_pipeline.report_persist_failed",
            run_id=run_id,
            error=str(exc),
        )


def _extract_title(report_md: str) -> str:
    """Extract the first heading from markdown, or return a default."""
    for line in report_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return f"AI News Report — {datetime.now(tz=UTC).strftime('%Y-%m-%d')}"


def _extract_summary(report_md: str, max_chars: int = 500) -> str:
    """Extract the first paragraph after the title as a summary snippet."""
    lines = report_md.splitlines()
    collecting = False
    paragraphs: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            collecting = True
            continue
        if collecting:
            if stripped.startswith("## "):
                break
            if stripped:
                paragraphs.append(stripped)

    summary = " ".join(paragraphs)
    return summary[:max_chars] if summary else report_md[:max_chars]
