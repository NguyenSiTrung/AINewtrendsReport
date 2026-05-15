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

from ainews.core.config import get_settings
from ainews.core.database import create_engine, get_db_session
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

    settings = get_settings()
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

    # ── Load site priorities for smart ranking in writer ───
    import urllib.parse

    from sqlalchemy import select

    from ainews.models.site import Site

    site_priorities: dict[str, int] = {}
    with get_db_session(engine) as session:
        site_rows = session.execute(
            select(Site.url, Site.priority).where(Site.enabled == 1)
        ).all()
        for site_url, site_prio in site_rows:
            domain = urllib.parse.urlparse(site_url).netloc.removeprefix("www.")
            if domain:
                site_priorities[domain] = site_prio

    # Fallback: if no sites specified, use all enabled sites
    if not sites:
        sites = list(site_priorities.keys())

    # ── Build and invoke graph ────────────────────────────
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        checkpoint_db = str(settings.db_path.parent / f"checkpoint_{run_id}.db")

        # Resolve pipeline settings (DB overrides env)
        report_max_sources: int = settings.report_max_sources
        tavily_max_results: int = settings.tavily_max_results
        from ainews.models.settings_kv import SettingsKV

        with get_db_session(engine) as session:
            pipeline_row = session.get(SettingsKV, "pipeline")
            if pipeline_row and isinstance(pipeline_row.value, dict):
                db_max = pipeline_row.value.get("report_max_sources")
                if db_max is not None:
                    report_max_sources = int(db_max)
                db_tavily = pipeline_row.value.get("tavily_max_results")
                if db_tavily is not None:
                    tavily_max_results = int(db_tavily)

        params = RunParams(
            timeframe_days=timeframe_days,
            topics=topics,
            sites=sites,
            use_smart_planner=input_params.get("use_smart_planner", True),
            report_max_sources=report_max_sources,
            tavily_max_results=tavily_max_results,
            site_priorities=site_priorities,
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

        # ── Push to Confluence wiki (if configured) ───────
        _push_to_wiki(engine, run_id, result, schedule_id, log)

        # ── Determine final status ────────────────────────
        node_errors = result.get("errors", [])
        if node_errors:
            final_status = "completed_with_errors"
            error_nodes = ", ".join({e.node for e in node_errors if hasattr(e, "node")})
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
            f"Pipeline {final_status}"
            + (f" — {error_summary}" if error_summary else ""),
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
    """Create a Report DB row using paths written by the exporter node.

    The exporter node already writes ``report.md`` and ``report.xlsx``
    to ``reports_dir / run_id / ...``.  This function only constructs
    the deterministic paths and persists the metadata row — no file I/O.
    """
    try:
        report_md: str = result.get("report_md", "")
        trends: list[dict[str, Any]] = result.get("trends", [])

        # Deterministic paths written by the exporter node
        run_dir = reports_dir / run_id
        md_path = run_dir / "report.md"
        xlsx_path = run_dir / "report.xlsx"

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
                xlsx_path=str(xlsx_path) if xlsx_path.exists() else None,
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


def _push_to_wiki(
    engine: Any,
    run_id: str,
    result: dict[str, Any],
    schedule_id: int | None,
    log: Any,
) -> None:
    """Push report to Confluence wiki if enabled for this schedule.

    This is a **non-blocking** operation: failures are logged as warnings
    and the pipeline continues as ``completed``.  Wiki push is considered
    a best-effort post-processing step.
    """
    from ainews.models.schedule import Schedule
    from ainews.models.run import Run

    with get_db_session(engine) as session:
        run = session.get(Run, run_id)
        if not run:
            return

        wiki_enabled = False
        space_key = ""
        ancestor_id = ""
        title_prefix = "AI News, Trends"

        if run.input_params and run.input_params.get("wiki_enabled"):
            wiki_enabled = True
            space_key = run.input_params.get("wiki_space_key", "")
            ancestor_id = run.input_params.get("wiki_ancestor_id", "")
            title_prefix = run.input_params.get("wiki_title_prefix", title_prefix)
        elif schedule_id is not None:
            schedule = session.get(Schedule, schedule_id)
            if schedule and schedule.wiki_enabled:
                wiki_enabled = True
                space_key = schedule.wiki_space_key
                ancestor_id = schedule.wiki_ancestor_id
                title_prefix = schedule.wiki_title_prefix or title_prefix

        if not wiki_enabled:
            return

        # Read effective wiki settings (DB → env fallback)
        from ainews.core.config import get_wiki_settings

        wiki = get_wiki_settings(session)

    if not wiki["base_url"] or not wiki["username"]:
        return  # Wiki not configured globally — skip

    if not space_key or not ancestor_id:
        log.warning(
            "wiki_push.missing_config",
            run_id=run_id,
            schedule_id=schedule_id,
            detail="wiki_space_key or wiki_ancestor_id not set",
        )
        return

    report_md: str = result.get("report_md", "")
    if not report_md.strip():
        log.warning("wiki_push.empty_report", run_id=run_id)
        return

    from ainews.services.run_logger import log_to_db

    log_to_db(engine, run_id, "wiki", "INFO", "Publishing report to Confluence wiki…")

    try:
        from ainews.services.wiki_publisher import WikiPublisher

        publisher = WikiPublisher(
            base_url=wiki["base_url"],
            username=wiki["username"],
            password=wiki["password"],
            verify_ssl=wiki["verify_ssl"],
        )
        pub_result = publisher.publish(
            markdown_content=report_md,
            space_key=space_key,
            ancestor_id=ancestor_id,
            title_prefix=title_prefix,
        )

        if pub_result.success:
            # Update Report row with wiki URL
            with get_db_session(engine) as session:
                report = (
                    session.query(Report)
                    .filter_by(run_id=run_id)
                    .first()
                )
                if report:
                    report.wiki_url = pub_result.url
                    report.wiki_pushed_at = datetime.now(tz=UTC).isoformat()

            log.info(
                "wiki_push.success",
                run_id=run_id,
                url=pub_result.url,
                page_id=pub_result.page_id,
            )
            log_to_db(
                engine,
                run_id,
                "wiki",
                "INFO",
                f"Wiki page created: {pub_result.url}",
            )
        else:
            log.warning(
                "wiki_push.publish_failed",
                run_id=run_id,
                error=pub_result.error,
            )
            log_to_db(
                engine,
                run_id,
                "wiki",
                "WARNING",
                f"Wiki push failed: {pub_result.error}",
            )

    except Exception as exc:
        # Wiki push failure should NOT fail the pipeline
        log.warning("wiki_push.error", run_id=run_id, error=str(exc))
        log_to_db(
            engine,
            run_id,
            "wiki",
            "WARNING",
            f"Wiki push error: {exc}",
        )

