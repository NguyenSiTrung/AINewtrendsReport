"""Celery task: run_pipeline — executes the LangGraph pipeline asynchronously.

This task is enqueued by the shared service layer and picks up a Run by
``run_id``, transitions its status through ``pending → running → completed``
(or ``failed``), and persists metrics/errors to the database.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any

import structlog

from ainews.core.config import Settings
from ainews.core.database import create_engine, get_db_session
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
    from ainews.agents.state import GraphState, RunParams

    settings = Settings()
    engine = create_engine(settings.database_url)

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
        run.started_at = datetime.now(tz=timezone.utc).isoformat()
        session.flush()

        # Resolve params
        schedule_id = run.schedule_id
        input_params: dict[str, Any] = run.input_params or {}

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

    # ── Build and invoke graph ────────────────────────────
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        checkpoint_db = str(settings.db_path.parent / f"checkpoint_{run_id}.db")

        params = RunParams(
            timeframe_days=timeframe_days,
            topics=topics,
            sites=sites,
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

        # ── Update Run on success ─────────────────────────
        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            if run is not None:
                run.status = "completed"
                run.finished_at = datetime.now(tz=timezone.utc).isoformat()
                run.stats = result.get("metrics", {})

        log.info("run_pipeline.completed")
        return {"status": "completed", "run_id": run_id}

    except Exception as exc:
        tb = traceback.format_exc()
        log.error("run_pipeline.failed", error=str(exc), traceback=tb)

        with get_db_session(engine) as session:
            run = session.get(Run, run_id)
            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(tz=timezone.utc).isoformat()
                run.error = str(exc)

        return {"status": "failed", "run_id": run_id, "error": str(exc)}

    finally:
        engine.dispose()
