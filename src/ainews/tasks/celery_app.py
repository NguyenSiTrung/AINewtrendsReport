"""Celery application configuration.

Connects to Valkey (Redis-compatible) as broker and result backend.
Declares three queues: ``default``, ``scrape``, ``llm`` (only ``default``
used in v1 — sub-task routing is planned for v2).
"""

from __future__ import annotations

from typing import Any

from celery import Celery

from ainews.core.config import Settings, get_settings


def make_celery(settings: Settings | None = None) -> Celery:
    """Create and configure a Celery application.

    Parameters
    ----------
    settings:
        Optional settings override; defaults to loading from env.
    """
    if settings is None:
        settings = get_settings()

    app = Celery("ainews")

    app.conf.update(
        broker_url=settings.valkey_url,
        result_backend=settings.valkey_url,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone=settings.timezone,
        enable_utc=True,
        task_track_started=True,
        # Queue declarations
        task_default_queue="default",
        task_queues={
            "default": {"exchange": "default", "routing_key": "default"},
            "scrape": {"exchange": "scrape", "routing_key": "scrape"},
            "llm": {"exchange": "llm", "routing_key": "llm"},
        },
        # Autodiscover tasks in ainews.tasks package
        include=["ainews.tasks.pipeline", "ainews.tasks.beat"],
        beat_schedule={
            "check-schedules-every-minute": {
                "task": "ainews.tasks.beat.check_schedules",
                "schedule": 60.0,
            },
        },
    )

    return app


# Module-level instance used by `celery -A ainews.tasks.celery_app worker`
celery_app = make_celery()


# ── Worker startup diagnostics ────────────────────────────
from celery.signals import worker_ready  # noqa: E402

@worker_ready.connect
def _on_worker_ready(**kwargs: Any) -> None:
    """Log critical environment diagnostics when worker starts."""
    import os
    from ainews.core.config import get_settings

    settings = get_settings()
    tavily_key = settings.tavily_api_key
    import structlog
    log = structlog.get_logger("ainews.worker_diagnostics")
    log.info(
        "worker_ready_diagnostics",
        cwd=os.getcwd(),
        tavily_api_key_length=len(tavily_key),
        tavily_api_key_set=bool(tavily_key),
        tavily_api_key_prefix=tavily_key[:8] + "..." if len(tavily_key) > 8 else "(empty/short)",
        llm_base_url=settings.llm_base_url,
        db_path=str(settings.db_path),
        valkey_url=settings.valkey_url,
        env_AINEWS_TAVILY_API_KEY=os.environ.get("AINEWS_TAVILY_API_KEY", "(NOT SET)"),
    )
