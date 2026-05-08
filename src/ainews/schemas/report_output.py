"""Pydantic validation schemas for report outputs.

Used by exporters to validate generated artifacts before returning.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, field_validator


class ReportOutput(BaseModel):
    """Validates a rendered Markdown report.

    Attributes
    ----------
    report_md
        The full Markdown report content.
    file_path
        Absolute path where the report was written.
    """

    report_md: str
    file_path: Path

    @field_validator("report_md")
    @classmethod
    def report_md_not_empty(cls, v: str) -> str:
        """Ensure report_md is non-empty."""
        if not v.strip():
            msg = "report_md must not be empty"
            raise ValueError(msg)
        return v

    @field_validator("report_md")
    @classmethod
    def report_md_has_sections(cls, v: str) -> str:
        """Ensure report_md contains expected section markers."""
        required_sections = [
            "# AI News & Trends Report",
            "## Executive Summary",
            "## Methodology",
        ]
        for section in required_sections:
            if section not in v:
                msg = f"report_md missing required section: {section}"
                raise ValueError(msg)
        return v


class XlsxOutput(BaseModel):
    """Validates an exported Excel workbook.

    Attributes
    ----------
    file_path
        Absolute path to the generated .xlsx file.
    """

    file_path: Path

    @field_validator("file_path")
    @classmethod
    def file_must_exist(cls, v: Path) -> Path:
        """Ensure the xlsx file exists on disk."""
        if not v.exists():
            msg = f"xlsx file does not exist: {v}"
            raise ValueError(msg)
        return v

    @field_validator("file_path")
    @classmethod
    def file_must_have_content(cls, v: Path) -> Path:
        """Ensure the xlsx file is non-empty."""
        if v.exists() and v.stat().st_size == 0:
            msg = f"xlsx file is empty: {v}"
            raise ValueError(msg)
        return v
