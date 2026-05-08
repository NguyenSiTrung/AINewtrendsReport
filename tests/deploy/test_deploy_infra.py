"""Tests for systemd unit files — validate structure and key directives."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

DEPLOY_DIR = Path(__file__).resolve().parents[2] / "deploy"
SYSTEMD_DIR = DEPLOY_DIR / "systemd"

UNIT_FILES = [
    "ainews-api.service",
    "ainews-worker.service",
    "ainews-beat.service",
]


def _parse_unit(name: str) -> configparser.ConfigParser:
    """Parse a systemd unit file (INI-like format)."""
    path = SYSTEMD_DIR / name
    assert path.exists(), f"Unit file not found: {path}"
    parser = configparser.ConfigParser(interpolation=None)
    # systemd allows duplicate keys but configparser doesn't — read raw
    parser.read(str(path))
    return parser


class TestSystemdUnits:
    """Validate systemd unit file structure and security directives."""

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_unit_files_exist(self, unit_file: str) -> None:
        assert (SYSTEMD_DIR / unit_file).exists()

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_has_required_sections(self, unit_file: str) -> None:
        cfg = _parse_unit(unit_file)
        for section in ["Unit", "Service", "Install"]:
            assert cfg.has_section(section), (
                f"{unit_file} missing [{section}] section"
            )

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_user_is_ainews(self, unit_file: str) -> None:
        cfg = _parse_unit(unit_file)
        assert cfg.get("Service", "User") == "ainews"

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_environment_file(self, unit_file: str) -> None:
        cfg = _parse_unit(unit_file)
        assert cfg.get("Service", "EnvironmentFile") == "/etc/ainews/ainews.env"

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_restart_on_failure(self, unit_file: str) -> None:
        cfg = _parse_unit(unit_file)
        assert cfg.get("Service", "Restart") == "on-failure"

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_protect_system_strict(self, unit_file: str) -> None:
        cfg = _parse_unit(unit_file)
        assert cfg.get("Service", "ProtectSystem") == "strict"

    @pytest.mark.parametrize("unit_file", UNIT_FILES)
    def test_no_new_privileges(self, unit_file: str) -> None:
        cfg = _parse_unit(unit_file)
        assert cfg.get("Service", "NoNewPrivileges") == "yes"

    def test_api_exec_start_uvicorn(self) -> None:
        cfg = _parse_unit("ainews-api.service")
        exec_start = cfg.get("Service", "ExecStart")
        assert "uvicorn" in exec_start
        assert "--port 8000" in exec_start
        assert "--workers 2" in exec_start

    def test_worker_exec_start_celery(self) -> None:
        cfg = _parse_unit("ainews-worker.service")
        exec_start = cfg.get("Service", "ExecStart")
        assert "celery" in exec_start
        assert "default,scrape,llm" in exec_start
        assert "--concurrency 4" in exec_start

    def test_beat_exec_start_celery_beat(self) -> None:
        cfg = _parse_unit("ainews-beat.service")
        exec_start = cfg.get("Service", "ExecStart")
        assert "celery" in exec_start
        assert "beat" in exec_start


class TestCronFiles:
    """Validate cron schedule files."""

    def test_cron_file_exists(self) -> None:
        assert (DEPLOY_DIR / "cron" / "ainews").exists()

    def test_backup_cron_exists(self) -> None:
        assert (DEPLOY_DIR / "cron" / "ainews-backup").exists()

    def test_cron_has_weekly_trigger(self) -> None:
        content = (DEPLOY_DIR / "cron" / "ainews").read_text()
        # Monday 7 AM
        assert "0 7 * * 1" in content
        assert "ainews" in content
        assert "trigger-run" in content

    def test_cron_has_monthly_trigger(self) -> None:
        content = (DEPLOY_DIR / "cron" / "ainews").read_text()
        # 1st of month 8 AM
        assert "0 8 1 * *" in content
        assert "trigger-run" in content

    def test_cron_output_redirected(self) -> None:
        content = (DEPLOY_DIR / "cron" / "ainews").read_text()
        assert "/var/log/ainews/cron.log" in content


class TestBackupScript:
    """Validate backup script structure."""

    def test_backup_script_exists(self) -> None:
        assert (DEPLOY_DIR / "scripts" / "backup_db.sh").exists()

    def test_backup_script_has_retention(self) -> None:
        content = (DEPLOY_DIR / "scripts" / "backup_db.sh").read_text()
        assert "RETENTION_DAYS" in content
        assert "mtime" in content
        assert "-delete" in content

    def test_backup_uses_sqlite_backup(self) -> None:
        content = (DEPLOY_DIR / "scripts" / "backup_db.sh").read_text()
        assert ".backup" in content

    def test_backup_script_set_euo_pipefail(self) -> None:
        content = (DEPLOY_DIR / "scripts" / "backup_db.sh").read_text()
        assert "set -euo pipefail" in content


class TestLogrotateConfig:
    """Validate logrotate configuration."""

    def test_logrotate_file_exists(self) -> None:
        assert (DEPLOY_DIR / "logrotate" / "ainews").exists()

    def test_logrotate_daily_rotation(self) -> None:
        content = (DEPLOY_DIR / "logrotate" / "ainews").read_text()
        assert "daily" in content
        assert "rotate 14" in content

    def test_logrotate_compression(self) -> None:
        content = (DEPLOY_DIR / "logrotate" / "ainews").read_text()
        assert "compress" in content
        assert "delaycompress" in content

    def test_logrotate_target_path(self) -> None:
        content = (DEPLOY_DIR / "logrotate" / "ainews").read_text()
        assert "/var/log/ainews/*.log" in content

    def test_logrotate_notifempty(self) -> None:
        content = (DEPLOY_DIR / "logrotate" / "ainews").read_text()
        assert "notifempty" in content


class TestInstallScript:
    """Validate install.sh structure and idempotency markers."""

    def test_install_script_exists(self) -> None:
        assert (DEPLOY_DIR / "install.sh").exists()

    def test_install_has_set_euo_pipefail(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "set -euo pipefail" in content

    def test_install_detects_ubuntu(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "VERSION_ID" in content or "lsb_release" in content

    def test_install_creates_ainews_user(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "ainews" in content
        assert "useradd" in content or "adduser" in content

    def test_install_copies_systemd_units(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "systemd" in content
        assert "daemon-reload" in content

    def test_install_copies_cron_files(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "/etc/cron.d/" in content

    def test_install_copies_logrotate(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "/etc/logrotate.d/" in content

    def test_install_env_file_no_overwrite(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        # Should check before overwriting
        assert "-f" in content or "exist" in content.lower()

    def test_install_alembic_and_seed(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "alembic" in content
        assert "seed" in content

    def test_install_file_mode_audit(self) -> None:
        content = (DEPLOY_DIR / "install.sh").read_text()
        assert "0640" in content
