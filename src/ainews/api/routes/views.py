"""View routes — server-rendered HTML pages for the admin UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ainews.api.auth import (
    JWT_COOKIE_NAME,
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_by_id,
)
from ainews.api.deps import get_db
from ainews.api.flash import flash, get_flashed_messages

router = APIRouter(tags=["views"])


# ── Helpers ──────────────────────────────────────────────


def _render(
    request: Request,
    template_name: str,
    context: dict | None = None,
) -> Any:
    """Render a Jinja2 template with common context."""
    templates = request.app.state.templates
    ctx = {
        "get_flashed_messages": get_flashed_messages,
        **(context or {}),
    }
    return templates.TemplateResponse(request, template_name, ctx)


def _get_current_user(request: Request, session: Session) -> Any | None:
    """Extract and validate the current user from the JWT cookie."""
    token = request.cookies.get(JWT_COOKIE_NAME)
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return get_user_by_id(session, int(user_id))


def _require_auth(request: Request, session: Session) -> RedirectResponse | None:
    """Return a redirect to /login if user is not authenticated."""
    user = _get_current_user(request, session)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    request.state.user = user
    return None


# ── Auth routes (public) ─────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Any:
    """Render the login page."""
    return _render(request, "login.html")


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Validate credentials, set JWT cookie, redirect to dashboard."""
    user = authenticate_user(session, email, password)
    if user is None:
        return _render(
            request,
            "login.html",
            {"error": "Invalid email or password", "email": email},
        )

    token = create_access_token(user.id, user.email)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        JWT_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=False,  # True in production behind HTTPS
        max_age=3600 * 24,
    )
    flash(response, "Welcome back!", "success")
    return response


@router.get("/logout")
def logout(request: Request) -> RedirectResponse:
    """Clear the JWT cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(JWT_COOKIE_NAME)
    flash(response, "Logged out successfully", "info")
    return response


# ── Protected page routes ────────────────────────────────


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Render the dashboard page with real data (auth required)."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.run import Run
    from ainews.models.schedule import Schedule
    from ainews.models.site import Site

    # Stats
    total_runs = session.scalar(select(func.count(Run.id))) or 0
    completed = (
        session.scalar(select(func.count(Run.id)).where(Run.status == "completed")) or 0
    )
    success_rate = round(completed / total_runs * 100) if total_runs else 0
    active_sites = session.scalar(select(func.count(Site.id))) or 0
    schedule_count = session.scalar(select(func.count(Schedule.id))) or 0

    # Recent runs (last 10)
    recent_runs = (
        session.execute(select(Run).order_by(Run.created_at.desc()).limit(10))
        .scalars()
        .all()
    )

    return _render(
        request,
        "dashboard.html",
        {
            "stats": {
                "total_runs": total_runs,
                "success_rate": success_rate,
                "active_sites": active_sites,
                "schedule_count": schedule_count,
            },
            "recent_runs": recent_runs,
        },
    )


@router.get("/health", response_class=HTMLResponse)
def health_page(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Render the health page (auth required)."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    health_data = _probe_health(session)
    return _render(request, "health.html", health_data)


@router.get("/health/probes", response_class=HTMLResponse)
def health_probes(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: return just the health grid for auto-refresh."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    health_data = _probe_health(session)
    return _render(request, "partials/health_grid.html", health_data)


def _probe_health(session: Session) -> dict[str, Any]:
    """Run health probes and return template context."""
    from sqlalchemy import text

    components: dict[str, dict[str, str]] = {}

    # DB probe
    try:
        session.execute(text("SELECT 1"))
        components["Database"] = {"status": "ok"}
    except Exception as exc:
        components["Database"] = {
            "status": "down",
            "detail": str(exc),
        }

    # Valkey probe
    try:
        import redis

        from ainews.core.config import Settings

        settings = Settings()
        r: Any = redis.from_url(settings.valkey_url, socket_timeout=2)
        r.ping()
        components["Valkey"] = {"status": "ok"}
    except Exception as exc:
        components["Valkey"] = {
            "status": "down",
            "detail": str(exc),
        }

    # Overall
    statuses = [c["status"] for c in components.values()]
    if all(s == "ok" for s in statuses):
        overall = "ok"
    elif any(s == "ok" for s in statuses):
        overall = "degraded"
    else:
        overall = "down"

    return {"components": components, "overall": overall}
