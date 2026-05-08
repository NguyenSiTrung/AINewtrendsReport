"""FastAPI application factory with lifespan-managed DB engine."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ainews.core.config import Settings
from ainews.core.database import create_engine

logger = structlog.get_logger(__name__)


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

    # ── CORS ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    # ── Routers ───────────────────────────────────────────
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

    return app


# Module-level instance for `uvicorn ainews.api.main:app`
app = create_app()
