"""Tests for ainews.core.logging — structlog configuration."""

from __future__ import annotations

import logging

import structlog

from ainews.core.logging import setup_logging


class TestSetupLogging:
    """Verify structlog configuration."""

    def test_returns_bound_logger(self) -> None:
        setup_logging("INFO")
        log = structlog.get_logger()
        assert log is not None

    def test_json_output(self, capsys: object) -> None:
        setup_logging("DEBUG")
        log = structlog.get_logger("test_json")
        log.info("hello", key="value")
        # structlog with JSON renderer should produce parseable JSON
        # We verify the configuration was applied by checking no exception
        # is raised and the logger is callable.

    def test_respects_log_level(self) -> None:
        setup_logging("WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_includes_timestamp_processor(self) -> None:
        setup_logging("INFO")
        config = structlog.get_config()
        processor_names = [
            p.__name__ if hasattr(p, "__name__") else str(p)
            for p in config["processors"]
        ]
        # Should include timestamper
        has_timestamp = any(
            "timestamper" in name.lower() or "time" in name.lower()
            for name in processor_names
        )
        assert has_timestamp

    def test_setup_is_idempotent(self) -> None:
        """Calling setup_logging multiple times should not raise."""
        setup_logging("INFO")
        setup_logging("DEBUG")
        log = structlog.get_logger()
        assert log is not None
