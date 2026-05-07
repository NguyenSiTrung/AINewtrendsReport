"""Tests for ainews CLI entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from ainews import __version__
from ainews.cli import app

runner = CliRunner()


class TestCLIHelp:
    """ainews --help should display formatted help."""

    def test_help_exits_zero(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_shows_app_name(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert "ainews" in result.output.lower()

    def test_help_shows_command_groups(self) -> None:
        result = runner.invoke(app, ["--help"])
        output = result.output.lower()
        assert "version" in output
        assert "llm" in output
        assert "run" in output
        assert "seed" in output


class TestCLIVersion:
    """ainews version should print the package version."""

    def test_version_command(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_format(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.output.strip().startswith("ainews")


class TestCLISubApps:
    """Stub sub-apps should be accessible with --help."""

    def test_llm_help(self) -> None:
        result = runner.invoke(app, ["llm", "--help"])
        assert result.exit_code == 0

    def test_run_help(self) -> None:
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

    def test_seed_help(self) -> None:
        result = runner.invoke(app, ["seed", "--help"])
        assert result.exit_code == 0
