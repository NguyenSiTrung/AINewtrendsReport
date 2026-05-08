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


class TestCLILLMTest:
    """ainews llm test should display config and test connectivity."""

    def test_llm_test_success(self) -> None:
        import httpx
        import respx

        from ainews.core.config import Settings
        
        with respx.mock:
            respx.post(f"{Settings().llm_base_url}/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": "chatcmpl-test",
                        "object": "chat.completion",
                        "model": "local-model",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "Hi",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 5,
                            "completion_tokens": 1,
                            "total_tokens": 6,
                        },
                    },
                )
            )
            result = runner.invoke(app, ["llm", "test"])

        assert result.exit_code == 0
        assert "Resolved LLM Config" in result.output
        assert "base_url" in result.output
        assert "***" in result.output  # masked api_key
        assert "Connection OK" in result.output

    def test_llm_test_failure(self) -> None:
        import httpx
        import respx

        from ainews.core.config import Settings

        with respx.mock:
            respx.post(f"{Settings().llm_base_url}/chat/completions").mock(
                side_effect=httpx.ConnectError("Connection refused"),
            )
            result = runner.invoke(app, ["llm", "test"])

        assert result.exit_code == 1
        assert "Connection FAILED" in result.output

    def test_llm_test_shows_config_fields(self) -> None:
        import httpx
        import respx

        from ainews.core.config import Settings

        with respx.mock:
            respx.post(f"{Settings().llm_base_url}/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "model": "local-model",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "Hi",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 5,
                            "completion_tokens": 1,
                            "total_tokens": 6,
                        },
                    },
                )
            )
            result = runner.invoke(app, ["llm", "test"])

        output = result.output
        assert "temperature" in output
        assert "max_tokens" in output
        assert "timeout" in output
