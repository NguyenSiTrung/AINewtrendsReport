"""FastAPI application factory with lifespan-managed DB engine."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from ainews.core.config import Settings
from ainews.core.database import create_engine

logger = structlog.get_logger(__name__)

# ── Template directory paths ────────────────────────────
_API_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _API_DIR / "templates"
_STATIC_DIR = _API_DIR / "static"


def _create_templates() -> Jinja2Templates:
    """Create Jinja2Templates instance with global context variables."""
    from zoneinfo import ZoneInfo

    from ainews.core.config import Settings

    settings = Settings()
    local_tz = ZoneInfo(settings.timezone)

    def _localtime_filter(value: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """Convert a UTC ISO 8601 string to the configured local timezone."""
        if not value:
            return "—"
        try:
            from datetime import datetime, timezone

            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # If naive (no tz info), assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(local_tz).strftime(fmt)
        except (ValueError, TypeError):
            return value[:16] if len(value) > 16 else value

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    templates.env.filters["localtime"] = _localtime_filter
    templates.env.globals.update(
        app_name="AI News & Trends",
        app_version="0.1.0",
        current_year=datetime.now().year,
        app_timezone=settings.timezone,
    )
    return templates


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise the DB engine at startup; dispose at shutdown."""
    settings = Settings()
    engine = create_engine(settings.database_url)
    app.state.engine = engine
    logger.info("api.startup", db_url=settings.database_url)
    yield
    engine.dispose()
    logger.info("api.shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="AI News & Trends Report API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── Jinja2 Templates ─────────────────────────────────
    app.state.templates = _create_templates()

    # ── Static files ─────────────────────────────────────
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # ── CORS ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── CSRF middleware ──────────────────────────────────
    from ainews.api.middleware.csrf import CSRFMiddleware

    app.add_middleware(CSRFMiddleware)

    # ── CSP middleware ───────────────────────────────────
    from ainews.api.middleware.csp import CSPMiddleware

    app.add_middleware(CSPMiddleware)

    # ── Exception handlers ────────────────────────────────
    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    # ── API Routers (JSON) ────────────────────────────────
    from ainews.api.routes.health import router as health_router
    from ainews.api.routes.runs import router as runs_router
    from ainews.api.routes.schedules import router as schedules_router
    from ainews.api.routes.sites import router as sites_router
    from ainews.api.routes.trigger import router as trigger_router

    app.include_router(health_router, prefix="/api")
    app.include_router(trigger_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(sites_router, prefix="/api")
    app.include_router(schedules_router, prefix="/api")

    # ── View Routers (HTML pages) ─────────────────────────
    from ainews.api.routes.views import router as views_router

    app.include_router(views_router)

    return app


# Module-level instance for `uvicorn ainews.api.main:app`
app = create_app()
