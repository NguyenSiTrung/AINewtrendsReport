"""Tests for CLI `ainews run` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ainews.cli import app

runner = CliRunner()


class TestRunCLI:
    """Verify ainews run CLI command."""

    def test_run_help(self) -> None:
        """ainews run --help displays help."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "topic" in result.output.lower() or "run" in result.output.lower()

    def test_run_executes_pipeline(self, tmp_path: Path) -> None:
        """ainews run --topic AI --days 3 executes full pipeline."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "run_id": "test-run",
            "report_md": "# Test Report\n\nContent",
            "queries": ["q1"],
            "raw_results": [],
            "fetched_articles": [],
            "filtered_articles": [],
            "clusters": [],
            "summaries": [],
            "trends": [],
            "xlsx_path": "",
            "errors": [],
            "metrics": {"planner": {"wall_seconds": 1.0}},
            "loop_count": 1,
            "params": {
                "timeframe_days": 3,
                "topics": ["AI"],
                "sites": [],
            },
        }

        mock_build = MagicMock(return_value=mock_graph)

        with (
            patch(
                "ainews.agents.graph.build_graph",
                mock_build,
            ),
            patch(
                "langgraph.checkpoint.sqlite.SqliteSaver.from_conn_string",
            ) as mock_cp,
        ):
            mock_cp.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_cp.return_value.__exit__ = MagicMock(return_value=False)
            result = runner.invoke(
                app,
                [
                    "run",
                    "start",
                    "--topic",
                    "AI",
                    "--days",
                    "3",
                    "--output",
                    str(tmp_path),
                ],
            )

        assert result.exit_code == 0
        assert "Report generated" in result.output or "report" in result.output.lower()
