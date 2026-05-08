"""Exporter node — writes report files and registers them in the database.

Calls both Markdown and Excel exporters, validates outputs via Pydantic,
and persists the file paths in the ``reports`` DB table.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from ainews.agents.resilience import node_resilient, track_metrics
from ainews.agents.state import GraphState
from ainews.core.database import get_db_session
from ainews.exporters.markdown import export_markdown
from ainews.exporters.xlsx import export_xlsx
from ainews.models.report import Report

logger = structlog.get_logger(__name__)


def _get_reports_dir() -> Path:
    """Return the reports output directory from settings."""
    from ainews.core.config import Settings

    settings = Settings()
    # Reports live alongside the database
    return settings.db_path.parent / "reports"


@node_resilient("exporter")
def exporter_node(state: GraphState) -> dict[str, Any]:
    """Export report files and register in database.

    Parameters
    ----------
    state
        Current graph state with ``report_md``, ``summaries``,
        ``trends``, ``params``, ``run_id``.

    Returns
    -------
    dict
        Partial state with ``xlsx_path`` and ``metrics``.
    """
    start = time.time()
    run_id = state["run_id"]
    report_md = state["report_md"]
    summaries = state.get("summaries", [])
    trends: list[dict[str, Any]] = state.get("trends", [])  # type: ignore[assignment]
    params = state["params"]

    reports_dir = _get_reports_dir()

    # Export Markdown report
    md_path = export_markdown(report_md, run_id, reports_dir)
    logger.info("exporter_md_done", path=str(md_path))

    # Build xlsx data dict
    xlsx_data: dict[str, Any] = {
        "executive_summary": _extract_executive_summary(report_md),
        "params": params,
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "summaries": summaries,
        "trends": trends,
    }

    # Export Excel report
    xlsx_path = export_xlsx(xlsx_data, run_id, reports_dir)
    logger.info("exporter_xlsx_done", path=str(xlsx_path))

    # Register in database
    _register_report(
        run_id=run_id,
        report_md=report_md,
        md_path=md_path,
        xlsx_path=xlsx_path,
        trends=trends,
    )

    return {
        "xlsx_path": str(xlsx_path),
        "metrics": track_metrics("exporter", state, start_time=start),
    }


def _extract_executive_summary(report_md: str) -> str:
    """Extract the Executive Summary section from the rendered report."""
    marker = "## Executive Summary"
    next_marker = "## "

    start_idx = report_md.find(marker)
    if start_idx == -1:
        return ""

    content_start = start_idx + len(marker)
    # Find the next ## heading
    next_idx = report_md.find(next_marker, content_start + 1)
    if next_idx == -1:
        return report_md[content_start:].strip()

    return report_md[content_start:next_idx].strip()


def _register_report(
    *,
    run_id: str,
    report_md: str,
    md_path: Path,
    xlsx_path: Path,
    trends: list[dict[str, Any]],
) -> None:
    """Register report paths in the database."""
    from ainews.core.config import Settings
    from ainews.core.database import create_engine

    settings = Settings()
    engine = create_engine(settings.database_url)

    with get_db_session(engine) as session:
        report = Report(
            run_id=run_id,
            title="AI News & Trends Report",
            summary_md=report_md[:500] if report_md else None,
            full_md_path=str(md_path),
            xlsx_path=str(xlsx_path),
            trends=[t.get("name", "") for t in trends],
            created_at=datetime.now(tz=UTC).isoformat(),
        )
        session.add(report)

    logger.info("exporter_db_registered", run_id=run_id)
