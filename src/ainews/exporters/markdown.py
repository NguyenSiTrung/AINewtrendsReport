"""Markdown report exporter.

Writes the rendered Markdown report to disk and validates it
via the :class:`~ainews.schemas.report_output.ReportOutput` schema.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from ainews.schemas.report_output import ReportOutput

logger = structlog.get_logger(__name__)


def export_markdown(
    report_md: str,
    run_id: str,
    reports_dir: Path,
) -> Path:
    """Write a Markdown report to ``{reports_dir}/{run_id}/report.md``.

    Parameters
    ----------
    report_md
        Rendered Markdown report content.
    run_id
        Unique identifier for the pipeline run.
    reports_dir
        Base directory for report outputs.

    Returns
    -------
    Path
        Absolute path to the written report file.

    Raises
    ------
    pydantic.ValidationError
        If the report content fails validation.
    """
    out_dir = reports_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    file_path = (out_dir / "report.md").resolve()
    file_path.write_text(report_md, encoding="utf-8")

    # Validate output
    ReportOutput(report_md=report_md, file_path=file_path)

    logger.info(
        "markdown_exported",
        run_id=run_id,
        path=str(file_path),
        size_bytes=file_path.stat().st_size,
    )

    return file_path
