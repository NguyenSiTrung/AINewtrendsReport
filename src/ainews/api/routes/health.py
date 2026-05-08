"""Health check router — probes DB and Valkey connectivity."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ainews.api.deps import get_db
from ainews.core.config import Settings
from ainews.schemas.health import ComponentStatus, HealthResponse

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
def health_check(
    session: Session = Depends(get_db),  # noqa: B008
) -> HealthResponse:
    """Probe infrastructure components and return overall status."""
    components: dict[str, ComponentStatus] = {}

    # ── DB probe ──────────────────────────────────────────
    try:
        session.execute(text("SELECT 1"))
        components["db"] = ComponentStatus(status="ok")
    except Exception as exc:
        components["db"] = ComponentStatus(status="down", detail=str(exc))

    # ── Valkey probe ──────────────────────────────────────
    try:
        import redis

        settings = Settings()
        r: Any = redis.from_url(settings.valkey_url, socket_timeout=2)
        r.ping()
        components["valkey"] = ComponentStatus(status="ok")
    except Exception as exc:
        components["valkey"] = ComponentStatus(status="down", detail=str(exc))

    # ── Overall status ────────────────────────────────────
    statuses = [c.status for c in components.values()]
    if all(s == "ok" for s in statuses):
        overall = "ok"
    elif any(s == "ok" for s in statuses):
        overall = "degraded"
    else:
        overall = "down"

    return HealthResponse(status=overall, components=components)
