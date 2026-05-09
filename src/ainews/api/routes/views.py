"""View routes — server-rendered HTML pages for the admin UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
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

    from datetime import UTC, datetime, timedelta

    from sqlalchemy import func, select

    from ainews.models.report import Report
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

    # Runs per day (last 7 days) for sparkline
    today = datetime.now(tz=UTC).date()
    runs_per_day = []
    all_recent = (
        session.execute(
            select(Run.created_at).where(
                Run.created_at >= (today - timedelta(days=6)).isoformat()
            )
        )
        .scalars()
        .all()
    )
    for i in range(7):
        day = today - timedelta(days=6 - i)
        day_str = day.isoformat()
        count = sum(1 for ts in all_recent if ts and ts[:10] == day_str)
        runs_per_day.append(count)

    sparkline_svg = _sparkline_svg(runs_per_day, width=120, height=40)
    ring_svg = _ring_chart_svg(success_rate, size=64)

    # Latest completed run with report
    latest_report_run = session.execute(
        select(Run)
        .join(Report, Report.run_id == Run.id)
        .where(Run.status == "completed")
        .order_by(Run.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    # Recent runs (last 10)
    recent_runs = (
        session.execute(select(Run).order_by(Run.created_at.desc()).limit(10))
        .scalars()
        .all()
    )

    # Personalized greeting
    hour = datetime.now(tz=UTC).hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

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
            "sparkline_svg": sparkline_svg,
            "ring_svg": ring_svg,
            "latest_report_run": latest_report_run,
            "greeting": greeting,
        },
    )


def _sparkline_svg(data_points: list[int], width: int = 120, height: int = 40) -> str:
    """Generate an inline SVG sparkline polyline from a list of values."""
    if not data_points or max(data_points, default=0) == 0:
        # Flat line at bottom
        y = height - 4
        return (
            f'<svg viewBox="0 0 {width} {height}" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg" class="w-full h-full opacity-50">'
            f'<polyline points="0,{y} {width},{y}" stroke="currentColor" '
            f'stroke-width="1.5" stroke-linecap="round"/></svg>'
        )

    n = len(data_points)
    max_val = max(data_points)
    padding = 4
    usable_h = height - padding * 2
    usable_w = width - padding * 2

    points = []
    for i, v in enumerate(data_points):
        x = padding + (i / (n - 1)) * usable_w if n > 1 else width / 2
        y = padding + usable_h - (v / max_val) * usable_h
        points.append(f"{x:.1f},{y:.1f}")

    pts_str = " ".join(points)
    # Build fill path (area under line)
    first_x = points[0].split(",")[0]
    last_x = points[-1].split(",")[0]
    bottom = height - padding
    fill_path = (
        f"M{first_x},{bottom} "
        + " ".join(f"L{p}" for p in points)
        + f" L{last_x},{bottom} Z"
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" class="w-full h-full">'
        f'<path d="{fill_path}" fill="currentColor" opacity="0.15"/>'
        f'<polyline points="{pts_str}" stroke="currentColor" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f"</svg>"
    )


def _ring_chart_svg(percentage: int, size: int = 64) -> str:
    """Generate an inline SVG donut ring chart for a percentage value."""
    r = (size - 8) / 2
    cx = cy = size / 2
    circumference = 2 * 3.14159 * r
    filled = circumference * percentage / 100
    gap = circumference - filled

    return (
        f'<svg viewBox="0 0 {size} {size}" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg" class="w-full h-full -rotate-90">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="currentColor" '
        f'stroke-width="4" opacity="0.15"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="currentColor" '
        f'stroke-width="4" stroke-dasharray="{filled:.2f} {gap:.2f}" '
        f'stroke-linecap="round"/>'
        f"</svg>"
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

    return _render(request, "health.html")


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


@router.get("/health/ribbon", response_class=HTMLResponse)
def health_ribbon(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: return just the health ribbon for dashboard load."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    health_data = _probe_health(session)
    return _render(request, "partials/health_ribbon.html", {"health_ribbon": health_data})


def _probe_health(session: Session) -> dict[str, Any]:
    """Run health probes and return template context.

    Each component dict contains:
        status   – "ok" | "degraded" | "down"
        detail   – human-readable description (optional)
        latency  – probe round-trip in milliseconds
        icon     – heroicon path for the component type
        subtitle – short description of the component
    """
    import time
    from datetime import datetime, timezone

    from sqlalchemy import text

    components: dict[str, dict[str, Any]] = {}

    # ── DB probe ──────────────────────────────────────────
    t0 = time.monotonic()
    try:
        session.execute(text("SELECT 1"))
        latency = round((time.monotonic() - t0) * 1000, 1)
        components["Database"] = {
            "status": "ok",
            "latency": latency,
            "icon": "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
            "subtitle": "PostgreSQL",
        }
    except Exception as exc:
        latency = round((time.monotonic() - t0) * 1000, 1)
        components["Database"] = {
            "status": "down",
            "detail": str(exc),
            "latency": latency,
            "icon": "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
            "subtitle": "PostgreSQL",
        }

    # ── Valkey probe ──────────────────────────────────────
    t0 = time.monotonic()
    try:
        import redis

        from ainews.core.config import Settings

        settings = Settings()
        r: Any = redis.from_url(settings.valkey_url, socket_timeout=2)
        r.ping()
        latency = round((time.monotonic() - t0) * 1000, 1)
        components["Valkey"] = {
            "status": "ok",
            "latency": latency,
            "icon": "M13 10V3L4 14h7v7l9-11h-7z",
            "subtitle": "Cache & Broker",
        }
    except Exception as exc:
        latency = round((time.monotonic() - t0) * 1000, 1)
        components["Valkey"] = {
            "status": "down",
            "detail": str(exc),
            "latency": latency,
            "icon": "M13 10V3L4 14h7v7l9-11h-7z",
            "subtitle": "Cache & Broker",
        }

    # ── Celery worker probe ───────────────────────────────
    t0 = time.monotonic()
    try:
        from ainews.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=2)
        active = inspector.active()
        latency = round((time.monotonic() - t0) * 1000, 1)
        if active is None:
            components["Celery"] = {
                "status": "down",
                "detail": "No workers responding",
                "latency": latency,
                "icon": "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
                "subtitle": "Task Workers",
            }
        else:
            worker_count = len(active)
            active_tasks = sum(len(t) for t in active.values())
            components["Celery"] = {
                "status": "ok",
                "detail": f"{worker_count} worker(s), {active_tasks} active task(s)",
                "latency": latency,
                "icon": "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
                "subtitle": "Task Workers",
            }
    except Exception as exc:
        latency = round((time.monotonic() - t0) * 1000, 1)
        components["Celery"] = {
            "status": "down",
            "detail": str(exc),
            "latency": latency,
            "icon": "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
            "subtitle": "Task Workers",
        }

    # ── Summary metrics ───────────────────────────────────
    statuses = [c["status"] for c in components.values()]
    if all(s == "ok" for s in statuses):
        overall = "ok"
    elif any(s == "ok" for s in statuses):
        overall = "degraded"
    else:
        overall = "down"

    latencies = [c.get("latency", 0) for c in components.values()]
    passing = sum(1 for s in statuses if s == "ok")

    return {
        "components": components,
        "overall": overall,
        "checked_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "avg_latency": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "total_probes": len(components),
        "passing_probes": passing,
    }


# ── Sites CRUD ───────────────────────────────────────────


@router.get("/sites", response_class=HTMLResponse)
def sites_list(
    request: Request,
    search: str = "",
    category: str = "",
    page: int = 1,
    per_page: int = 25,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """List all sites with server-side search, category filter, and pagination."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.site import Site

    # ── Aggregate stats (unfiltered) for hero header ─────
    total_all = session.scalar(select(func.count(Site.id))) or 0
    active_count = session.scalar(
        select(func.count(Site.id)).where(Site.enabled == 1)
    ) or 0
    inactive_count = total_all - active_count

    # Category breakdown (unfiltered)
    cat_rows = (
        session.execute(
            select(Site.category, func.count(Site.id))
            .group_by(Site.category)
            .order_by(func.count(Site.id).desc())
        )
        .all()
    )
    all_categories = [row[0] for row in cat_rows if row[0]]
    category_counts = {row[0]: row[1] for row in cat_rows if row[0]}

    # ── Filtered query ───────────────────────────────────
    q = select(Site).order_by(Site.priority.desc())
    if search:
        q = q.where(Site.url.ilike(f"%{search}%") | Site.category.ilike(f"%{search}%"))
    if category:
        q = q.where(Site.category == category)

    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    sites = session.execute(q.limit(per_page).offset(offset)).scalars().all()
    query_params: dict[str, str] = {}
    if search:
        query_params["search"] = search
    if category:
        query_params["category"] = category
    return _render(
        request,
        "sites/list.html",
        {
            "sites": sites,
            "search": search,
            "category_filter": category,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "query_params": query_params,
            "total_all": total_all,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "all_categories": all_categories,
            "category_counts": category_counts,
        },
    )


@router.get("/sites/new", response_class=HTMLResponse)
def site_new_form(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show new site form."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect
    return _render(
        request,
        "sites/form.html",
        {
            "site": None,
            "breadcrumbs": [
                {"label": "Sites", "url": "/sites"},
                {"label": "New Site", "url": None},
            ],
        },
    )


@router.post("/sites/new")
def site_create(
    request: Request,
    url: str = Form(...),
    category: str = Form("tech"),
    priority: int = Form(5),
    crawl_depth: int = Form(2),
    enabled: str | None = Form(None),
    js_render: str | None = Form(None),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Create a new site."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.site import Site

    site = Site(
        url=url, 
        category=category, 
        priority=priority,
        crawl_depth=crawl_depth,
        enabled=1 if enabled else 0,
        js_render=1 if js_render else 0,
    )
    session.add(site)
    session.flush()

    resp = RedirectResponse(url="/sites", status_code=303)
    flash(resp, f"Site '{url}' created", "success")
    return resp


@router.get("/sites/{site_id}/edit", response_class=HTMLResponse)
def site_edit_form(
    request: Request,
    site_id: int,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show edit form for a site."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.site import Site

    site = session.get(Site, site_id)
    if not site:
        return RedirectResponse(url="/sites", status_code=303)
    return _render(
        request,
        "sites/form.html",
        {
            "site": site,
            "breadcrumbs": [
                {"label": "Sites", "url": "/sites"},
                {"label": "Edit Site", "url": None},
            ],
        },
    )


@router.post("/sites/{site_id}")
def site_update(
    request: Request,
    site_id: int,
    url: str = Form(...),
    category: str = Form("tech"),
    priority: int = Form(5),
    crawl_depth: int = Form(2),
    enabled: str | None = Form(None),
    js_render: str | None = Form(None),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Update an existing site."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.site import Site

    site = session.get(Site, site_id)
    if site:
        site.url = url
        site.category = category
        site.priority = priority
        site.crawl_depth = crawl_depth
        site.enabled = 1 if enabled else 0
        site.js_render = 1 if js_render else 0
        session.flush()

    resp = RedirectResponse(url="/sites", status_code=303)
    flash(resp, "Site updated", "success")
    return resp


# ── Schedules CRUD ───────────────────────────────────────


def _cron_to_human(expr: str) -> str:
    """Convert a cron expression to a human-readable string.

    Handles common patterns; falls back to the raw expression for
    anything too exotic.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return expr

    minute, hour, dom, month, dow = parts

    # Day-of-week mapping
    dow_names = {
        "0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed",
        "4": "Thu", "5": "Fri", "6": "Sat", "7": "Sun",
    }

    def _fmt_time(h: str, m: str) -> str:
        try:
            hi, mi = int(h), int(m)
            suffix = "AM" if hi < 12 else "PM"
            h12 = hi % 12 or 12
            return f"{h12}:{mi:02d} {suffix}"
        except ValueError:
            return f"{h}:{m}"

    # Every minute
    if all(p == "*" for p in parts):
        return "Every minute"

    # Every N minutes
    if minute.startswith("*/") and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return f"Every {minute[2:]} minutes"

    # Every hour at :MM
    if hour == "*" and dom == "*" and month == "*" and dow == "*":
        try:
            return f"Every hour at :{int(minute):02d}"
        except ValueError:
            pass

    # Daily at HH:MM
    if dom == "*" and month == "*" and dow == "*" and hour != "*" and minute != "*":
        return f"Daily at {_fmt_time(hour, minute)}"

    # Specific weekday(s) at HH:MM
    if dom == "*" and month == "*" and dow != "*" and hour != "*" and minute != "*":
        time_str = _fmt_time(hour, minute)
        if "," in dow:
            days = [dow_names.get(d.strip(), d.strip()) for d in dow.split(",")]
            return f"{', '.join(days)} at {time_str}"
        if "-" in dow:
            start, end = dow.split("-", 1)
            return f"{dow_names.get(start, start)}–{dow_names.get(end, end)} at {time_str}"
        day = dow_names.get(dow, dow)
        return f"Every {day} at {time_str}"

    # Specific day of month
    if dom != "*" and month == "*" and dow == "*" and hour != "*" and minute != "*":
        time_str = _fmt_time(hour, minute)
        return f"Monthly on day {dom} at {time_str}"

    return expr


@router.get("/schedules", response_class=HTMLResponse)
def schedules_list(
    request: Request,
    search: str = "",
    page: int = 1,
    per_page: int = 25,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """List all schedules with pagination."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.schedule import Schedule

    # ── Aggregate stats (unfiltered) for hero header ─────
    total_all = session.scalar(select(func.count(Schedule.id))) or 0
    active_count = session.scalar(
        select(func.count(Schedule.id)).where(Schedule.enabled == 1)
    ) or 0
    paused_count = total_all - active_count
    smart_planner_count = session.scalar(
        select(func.count(Schedule.id)).where(Schedule.use_smart_planner == 1)
    ) or 0

    # ── Filtered query ───────────────────────────────────
    q = select(Schedule).order_by(Schedule.name)
    if search:
        q = q.where(Schedule.name.ilike(f"%{search}%") | Schedule.cron_expr.ilike(f"%{search}%"))

    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    schedules = session.execute(q.limit(per_page).offset(offset)).scalars().all()

    # Build human-readable cron map
    cron_human: dict[int, str] = {s.id: _cron_to_human(s.cron_expr) for s in schedules}

    query_params: dict[str, str] = {}
    if search:
        query_params["search"] = search

    return _render(
        request,
        "schedules/list.html",
        {
            "schedules": schedules,
            "search": search,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "query_params": query_params,
            "total_all": total_all,
            "active_count": active_count,
            "paused_count": paused_count,
            "smart_planner_count": smart_planner_count,
            "cron_human": cron_human,
        },
    )


@router.get("/schedules/new", response_class=HTMLResponse)
def schedule_new_form(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show new schedule form."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.schedule import Schedule

    total_schedules = session.scalar(select(func.count(Schedule.id))) or 0
    active_count = session.scalar(
        select(func.count(Schedule.id)).where(Schedule.enabled == 1)
    ) or 0

    return _render(
        request,
        "schedules/form.html",
        {
            "schedule": None,
            "cron_human": _cron_to_human("0 7 * * 1"),
            "total_schedules": total_schedules,
            "active_count": active_count,
            "breadcrumbs": [
                {"label": "Schedules", "url": "/schedules"},
                {"label": "New Schedule", "url": None},
            ],
        },
    )


@router.post("/schedules/new")
def schedule_create(
    request: Request,
    name: str = Form(...),
    cron_expr: str = Form(...),
    timeframe_days: int = Form(7),
    topics: str = Form(""),
    enabled: str | None = Form(None),
    use_smart_planner: str | None = Form(None),
    model_override: str = Form(""),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Create a new schedule."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from datetime import UTC, datetime

    from ainews.models.schedule import Schedule

    topics_list = [t.strip() for t in topics.split(",") if t.strip()] if topics.strip() else None

    sched = Schedule(
        name=name,
        cron_expr=cron_expr,
        timeframe_days=timeframe_days,
        topics=topics_list,
        enabled=1 if enabled else 0,
        use_smart_planner=1 if use_smart_planner else 0,
        model_override=model_override.strip() or None,
        created_at=datetime.now(tz=UTC).isoformat(),
    )
    session.add(sched)
    session.flush()

    resp = RedirectResponse(url="/schedules", status_code=303)
    flash(resp, f"Schedule '{name}' created", "success")
    return resp


@router.get("/schedules/{schedule_id}/edit", response_class=HTMLResponse)
def schedule_edit_form(
    request: Request,
    schedule_id: int,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show edit form for a schedule."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.schedule import Schedule

    sched = session.get(Schedule, schedule_id)
    if not sched:
        return RedirectResponse(url="/schedules", status_code=303)

    total_schedules = session.scalar(select(func.count(Schedule.id))) or 0
    active_count = session.scalar(
        select(func.count(Schedule.id)).where(Schedule.enabled == 1)
    ) or 0

    return _render(
        request,
        "schedules/form.html",
        {
            "schedule": sched,
            "cron_human": _cron_to_human(sched.cron_expr),
            "total_schedules": total_schedules,
            "active_count": active_count,
            "breadcrumbs": [
                {"label": "Schedules", "url": "/schedules"},
                {"label": "Edit Schedule", "url": None},
            ],
        },
    )


@router.post("/schedules/{schedule_id}")
def schedule_update(
    request: Request,
    schedule_id: int,
    name: str = Form(...),
    cron_expr: str = Form(...),
    timeframe_days: int = Form(7),
    topics: str = Form(""),
    enabled: str | None = Form(None),
    use_smart_planner: str | None = Form(None),
    model_override: str = Form(""),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Update an existing schedule."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.schedule import Schedule

    sched = session.get(Schedule, schedule_id)
    if sched:
        topics_list = [t.strip() for t in topics.split(",") if t.strip()] if topics.strip() else None
        sched.name = name
        sched.cron_expr = cron_expr
        sched.timeframe_days = timeframe_days
        sched.topics = topics_list
        sched.enabled = 1 if enabled else 0
        sched.use_smart_planner = 1 if use_smart_planner else 0
        sched.model_override = model_override.strip() or None
        session.flush()

    resp = RedirectResponse(url="/schedules", status_code=303)
    flash(resp, "Schedule updated", "success")
    return resp


# ── Trigger ──────────────────────────────────────────────


@router.get("/trigger", response_class=HTMLResponse)
def trigger_page(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show the trigger run form."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    import json

    from sqlalchemy import func, select

    from ainews.models.run import Run
    from ainews.models.schedule import Schedule

    schedules = (
        session.execute(select(Schedule).order_by(Schedule.name)).scalars().all()
    )

    # Quick stats for context sidebar
    total_runs = session.scalar(select(func.count(Run.id))) or 0
    completed = (
        session.scalar(select(func.count(Run.id)).where(Run.status == "completed")) or 0
    )
    success_rate = round(completed / total_runs * 100) if total_runs else 0

    # Last completed run
    last_run = session.execute(
        select(Run).where(Run.status == "completed").order_by(Run.created_at.desc()).limit(1)
    ).scalar_one_or_none()

    # Active run check
    active_run = session.execute(
        select(Run).where(Run.status.in_(["pending", "running"])).limit(1)
    ).scalar_one_or_none()

    # Compute last run duration
    last_run_duration = "—"
    if last_run and last_run.started_at and last_run.finished_at:
        try:
            from datetime import datetime

            start = datetime.fromisoformat(last_run.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(last_run.finished_at.replace("Z", "+00:00"))
            diff = int((end - start).total_seconds())
            m, s = divmod(abs(diff), 60)
            last_run_duration = f"{m}m {s}s"
        except (ValueError, TypeError):
            pass

    # Serialize schedule data for JS auto-populate
    schedules_json = json.dumps([
        {
            "name": s.name,
            "topics": s.topics or [],
            "timeframe_days": s.timeframe_days,
            "use_smart_planner": bool(s.use_smart_planner),
        }
        for s in schedules
    ])

    return _render(request, "trigger.html", {
        "schedules": schedules,
        "schedules_json": schedules_json,
        "total_runs": total_runs,
        "success_rate": success_rate,
        "last_run": last_run,
        "last_run_duration": last_run_duration,
        "active_run": active_run,
    })


@router.post("/trigger")
def trigger_submit(
    request: Request,
    schedule_name: str = Form(""),
    topics: str = Form(""),
    days: int = Form(7),
    use_smart_planner: bool = Form(False),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Enqueue a pipeline run and redirect to runs."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.services.pipeline import create_and_enqueue_run

    params: dict[str, object] = {}
    if topics.strip():
        params["topics"] = [t.strip() for t in topics.split(",")]
    params["timeframe_days"] = days
    params["use_smart_planner"] = use_smart_planner

    try:
        run_id = create_and_enqueue_run(
            session,
            schedule_name=schedule_name or None,
            params=params or None,
            triggered_by="admin",
        )
        resp = RedirectResponse(url="/runs", status_code=303)
        flash(resp, f"Run {run_id[:12]} enqueued", "success")
    except ValueError as exc:
        resp = RedirectResponse(url="/trigger", status_code=303)
        flash(resp, str(exc), "error")
    return resp


# ── LLM Settings ─────────────────────────────────────────


@router.get("/llm", response_class=HTMLResponse)
def llm_settings_page(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show LLM settings form."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.core.config import Settings
    from ainews.llm.factory import get_llm_config
    from ainews.models.settings_kv import SettingsKV

    row = session.get(SettingsKV, "llm")
    db_overrides = row.value if row else None

    # Resolve effective config (env defaults merged with DB overrides) so the
    # form always shows the values that would actually be used at runtime.
    effective = get_llm_config(Settings(), db_overrides=db_overrides)
    settings_data: dict[str, object] = {
        "base_url": effective.base_url,
        "model": effective.model,
        # Never echo the API key back into the form; the placeholder text
        # explains that leaving it blank preserves the existing key.
        "api_key": "",
        "temperature": effective.temperature,
        "max_tokens": effective.max_tokens,
    }

    # ── Sidebar context: connection probe + config summary ──
    has_api_key = bool(effective.api_key and effective.api_key.strip())
    masked_key = effective.masked_api_key if has_api_key else ""

    # Probe will be done asynchronously via HTMX to prevent UI blocking
    llm_status: dict[str, object] = {"connected": None, "latency_ms": 0, "error": ""}

    return _render(
        request,
        "llm.html",
        {
            "settings": settings_data,
            "has_api_key": has_api_key,
            "masked_key": masked_key,
            "llm_status": llm_status,
            "breadcrumbs": [
                {"label": "Settings", "url": "/settings"},
                {"label": "LLM Settings", "url": None},
            ],
        },
    )


@router.post("/llm")
def llm_settings_save(
    request: Request,
    base_url: str = Form(""),
    model: str = Form(""),
    api_key: str = Form(""),
    temperature: float = Form(0.3),
    max_tokens: int = Form(4096),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Save LLM settings."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from datetime import UTC, datetime

    from ainews.models.settings_kv import SettingsKV

    data: dict[str, object] = {
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_key:
        data["api_key"] = api_key

    row = session.get(SettingsKV, "llm")
    if row:
        # Merge: keep existing api_key if not provided
        existing = row.value or {}
        if not api_key and "api_key" in existing:
            data["api_key"] = existing["api_key"]
        row.value = data
        row.updated_at = datetime.now(tz=UTC).isoformat()
    else:
        session.add(
            SettingsKV(
                key="llm",
                value=data,
                updated_at=datetime.now(tz=UTC).isoformat(),
            )
        )
    session.flush()

    resp = RedirectResponse(url="/llm", status_code=303)
    flash(resp, "LLM settings saved", "success")
    return resp


@router.get("/llm/probe", response_class=HTMLResponse)
def llm_probe(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: asynchronously check LLM connectivity."""
    redirect = _require_auth(request, session)
    if redirect:
        return HTMLResponse("")

    from ainews.core.config import Settings
    from ainews.llm.factory import get_llm_config
    from ainews.models.settings_kv import SettingsKV
    from ainews.llm.connectivity import check_llm_connection

    row = session.get(SettingsKV, "llm")
    db_overrides = row.value if row else None
    effective = get_llm_config(Settings(), db_overrides=db_overrides)

    llm_status: dict[str, object] = {"connected": False, "latency_ms": 0, "error": ""}
    try:
        result = check_llm_connection(effective)
        llm_status = {
            "connected": result.success,
            "latency_ms": round(result.latency_ms),
            "error": result.error or "",
        }
    except Exception:
        llm_status["error"] = "Probe failed"

    return _render(request, "partials/llm_probe.html", {"llm_status": llm_status})



# ── Runs ─────────────────────────────────────────────────


@router.get("/runs", response_class=HTMLResponse)
def runs_list(
    request: Request,
    page: int = 1,
    per_page: int = 25,
    status: str = "",
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """List all pipeline runs with pagination and status filtering."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from datetime import datetime as _dt

    from sqlalchemy import func, select

    from ainews.models.run import Run

    # ── Aggregate metrics (unfiltered) ──
    count_total = session.scalar(select(func.count(Run.id))) or 0
    count_completed = (
        session.scalar(select(func.count(Run.id)).where(Run.status == "completed")) or 0
    )
    count_failed = (
        session.scalar(select(func.count(Run.id)).where(Run.status == "failed")) or 0
    )
    count_running = (
        session.scalar(
            select(func.count(Run.id)).where(Run.status.in_(["pending", "running"]))
        )
        or 0
    )

    # Average duration of completed runs
    avg_duration_str = "—"
    finished_runs = (
        session.execute(
            select(Run.started_at, Run.finished_at)
            .where(Run.status == "completed")
            .where(Run.started_at.isnot(None))
            .where(Run.finished_at.isnot(None))
        )
        .all()
    )
    if finished_runs:
        durations = []
        for s, f in finished_runs:
            try:
                start = _dt.fromisoformat(s.replace("Z", "+00:00"))
                end = _dt.fromisoformat(f.replace("Z", "+00:00"))
                durations.append(int((end - start).total_seconds()))
            except (ValueError, TypeError):
                pass
        if durations:
            avg = sum(durations) // len(durations)
            m, s = divmod(abs(avg), 60)
            avg_duration_str = f"{m}m {s}s"

    # ── Filtered query ──
    q = select(Run).order_by(Run.created_at.desc())
    if status:
        q = q.where(Run.status == status)

    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    runs = session.execute(q.limit(per_page).offset(offset)).scalars().all()
    has_active_runs = any(r.status in ("pending", "running") for r in runs)

    # ── Per-run enrichment (duration string) ──
    run_durations: dict[str, str] = {}
    for run in runs:
        if run.started_at and run.finished_at:
            try:
                start = _dt.fromisoformat(run.started_at.replace("Z", "+00:00"))
                end = _dt.fromisoformat(run.finished_at.replace("Z", "+00:00"))
                diff = int((end - start).total_seconds())
                m, s = divmod(abs(diff), 60)
                run_durations[run.id] = f"{m}m {s}s"
            except (ValueError, TypeError):
                run_durations[run.id] = "—"
        else:
            run_durations[run.id] = "—"

    query_params: dict[str, str] = {}
    if status:
        query_params["status"] = status

    return _render(
        request,
        "runs/list.html",
        {
            "runs": runs,
            "has_active_runs": has_active_runs,
            "run_durations": run_durations,
            "status_filter": status,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "query_params": query_params,
            "metrics": {
                "total": count_total,
                "completed": count_completed,
                "failed": count_failed,
                "running": count_running,
                "avg_duration": avg_duration_str,
            },
        },
    )


@router.get("/runs/table", response_class=HTMLResponse)
def runs_table_partial(
    request: Request,
    status: str = "",
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: runs table body with auto-refresh."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from datetime import datetime as _dt

    from sqlalchemy import select

    from ainews.models.run import Run

    q = select(Run).order_by(Run.created_at.desc())
    if status:
        q = q.where(Run.status == status)
    runs = session.execute(q).scalars().all()
    has_active_runs = any(r.status in ("pending", "running") for r in runs)

    run_durations: dict[str, str] = {}
    for run in runs:
        if run.started_at and run.finished_at:
            try:
                start = _dt.fromisoformat(run.started_at.replace("Z", "+00:00"))
                end = _dt.fromisoformat(run.finished_at.replace("Z", "+00:00"))
                diff = int((end - start).total_seconds())
                m, s = divmod(abs(diff), 60)
                run_durations[run.id] = f"{m}m {s}s"
            except (ValueError, TypeError):
                run_durations[run.id] = "—"
        else:
            run_durations[run.id] = "—"

    return _render(
        request,
        "partials/runs_table.html",
        {
            "runs": runs,
            "has_active_runs": has_active_runs,
            "run_durations": run_durations,
            "status_filter": status,
        },
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show run detail with logs and optional report card."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.report import Report
    from ainews.models.run import Run
    from ainews.models.run_log import RunLog

    run = session.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        resp = RedirectResponse(url="/runs", status_code=303)
        flash(resp, "Run not found", "error")
        return resp

    logs = (
        session.execute(
            select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.ts)
        )
        .scalars()
        .all()
    )

    # Query associated report
    report = session.execute(
        select(Report).where(Report.run_id == run_id)
    ).scalar_one_or_none()

    node_states = _derive_node_states(logs)

    # Compute human-readable duration for completed/failed runs
    duration_str = "—"
    if run.started_at and run.finished_at:
        try:
            from datetime import datetime

            start = datetime.fromisoformat(run.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(run.finished_at.replace("Z", "+00:00"))
            diff = int((end - start).total_seconds())
            m, s = divmod(abs(diff), 60)
            duration_str = f"{m}m {s}s"
        except (ValueError, TypeError):
            pass

    return _render(
        request,
        "runs/detail.html",
        {
            "run": run,
            "logs": logs,
            "node_states": node_states,
            "report": report,
            "duration_str": duration_str,
            "breadcrumbs": [
                {"label": "Runs", "url": "/runs"},
                {"label": f"Run {run.id[:12]}", "url": None},
            ],
        },
    )


# ── Logs ─────────────────────────────────────────────────


@router.get("/logs", response_class=HTMLResponse)
def logs_page(
    request: Request,
    level: str = "",
    search: str = "",
    run_id: str = "",
    page: int = 1,
    per_page: int = 50,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show system logs with filtering and pagination."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.run_log import RunLog

    # Build filtered query
    q = select(RunLog)
    if level:
        q = q.where(RunLog.level == level.upper())
    if search:
        q = q.where(RunLog.message.ilike(f"%{search}%"))
    if run_id:
        q = q.where(RunLog.run_id == run_id)

    # Count totals per level for summary bar
    level_counts_rows = session.execute(
        select(RunLog.level, func.count(RunLog.id)).group_by(RunLog.level)
    ).all()
    level_counts = {row[0]: row[1] for row in level_counts_rows}

    # Total matching records for pagination
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    logs = (
        session.execute(q.order_by(RunLog.ts.desc()).limit(per_page).offset(offset))
        .scalars()
        .all()
    )

    query_params: dict[str, str] = {}
    if level:
        query_params["level"] = level
    if search:
        query_params["search"] = search
    if run_id:
        query_params["run_id"] = run_id

    is_htmx = request.headers.get("HX-Request") == "true"
    htmx_target = request.headers.get("HX-Target", "")
    if is_htmx and htmx_target in {"logs-table-container", "page-content"}:
        template = "partials/logs_table.html"
    elif is_htmx:
        template = "partials/logs_content.html"
    else:
        template = "logs.html"

    return _render(
        request,
        template,
        {
            "logs": logs,
            "level_filter": level,
            "search": search,
            "run_id_filter": run_id,
            "level_counts": level_counts,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "query_params": query_params,
        },
    )


# ── Settings ─────────────────────────────────────────────


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show system settings with data management options."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import func, select

    from ainews.models.run import Run
    from ainews.models.run_log import RunLog
    from ainews.models.schedule import Schedule
    from ainews.models.site import Site

    total_runs = session.scalar(select(func.count(Run.id))) or 0
    total_logs = session.scalar(select(func.count(RunLog.id))) or 0
    total_sites = session.scalar(select(func.count(Site.id))) or 0
    total_schedules = session.scalar(select(func.count(Schedule.id))) or 0

    # Last run time (most recent started_at)
    last_run_row = session.execute(
        select(Run.started_at)
        .where(Run.started_at.isnot(None))
        .order_by(Run.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    from ainews.core.config import Settings
    from ainews.models.settings_kv import SettingsKV

    # Read pipeline settings from DB (falls back to env config defaults)
    env_settings = Settings()
    pipeline_row = session.get(SettingsKV, "pipeline")
    pipeline_db = pipeline_row.value if pipeline_row and isinstance(pipeline_row.value, dict) else {}

    pipeline_settings = {
        "report_max_sources": pipeline_db.get("report_max_sources", env_settings.report_max_sources),
    }

    return _render(
        request,
        "settings.html",
        {
            "stats": {
                "total_runs": total_runs,
                "total_logs": total_logs,
                "total_sites": total_sites,
                "total_schedules": total_schedules,
                "last_run_at": last_run_row,
            },
            "pipeline_settings": pipeline_settings,
        },
    )


@router.post("/settings/reset-defaults")
def settings_reset_defaults(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Reset sites and schedules to factory defaults."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.seed import reset_all

    result = reset_all(session)
    msg = (
        f"Reset complete: removed {result.sites_deleted} sites"
        f" & {result.schedules_deleted} schedules,"
        f" restored {result.sites_created} default sites"
        f" & {result.schedules_created} default schedules"
    )
    resp = RedirectResponse(url="/settings", status_code=303)
    flash(resp, msg, "success")
    return resp


@router.post("/settings/pipeline")
def settings_pipeline_save(
    request: Request,
    report_max_sources: int = Form(50),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Save pipeline configuration settings."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from datetime import UTC, datetime

    from ainews.models.settings_kv import SettingsKV

    data: dict[str, object] = {
        "report_max_sources": max(0, min(report_max_sources, 500)),
    }

    row = session.get(SettingsKV, "pipeline")
    if row:
        from sqlalchemy.orm.attributes import flag_modified

        # Must create a NEW dict — in-place mutation of JSON is not tracked
        merged = dict(row.value or {})
        merged.update(data)
        row.value = merged
        row.updated_at = datetime.now(tz=UTC).isoformat()
        flag_modified(row, "value")
    else:
        session.add(
            SettingsKV(
                key="pipeline",
                value=data,
                updated_at=datetime.now(tz=UTC).isoformat(),
            )
        )
    session.flush()

    resp = RedirectResponse(url="/settings", status_code=303)
    flash(resp, "Pipeline configuration saved", "success")
    return resp


# ── HTMX Polling Partials ────────────────────────────────

# Pipeline stage names in execution order
PIPELINE_NODES = [
    "planner",
    "retriever",
    "scraper",
    "filter",
    "dedup",
    "synthesizer",
    "trender",
    "writer",
    "exporter",
]


# Mapping from actual @node_resilient names to stepper display names
_NODE_DISPLAY_MAP: dict[str, str] = {
    "retrieve_one": "retriever",
    "synthesize_one": "synthesizer",
}


def _derive_node_states(
    logs: list[Any],
) -> dict[str, str]:
    """Derive node states from RunLog entries.

    Returns a dict mapping node name to state:
    - 'pending': no log entries for this node
    - 'running': has a 'started' log but no 'completed' log
    - 'completed': has a 'completed' log
    - 'failed': has an ERROR-level log
    """
    states: dict[str, str] = {}
    for log in logs:
        # Map sub-node names to their display names
        node = _NODE_DISPLAY_MAP.get(log.node, log.node)
        level = log.level.upper() if log.level else ""
        msg = (log.message or "").lower()

        if level == "ERROR":
            states[node] = "failed"
        elif "completed" in msg:
            # Don't override failed state
            if states.get(node) != "failed":
                states[node] = "completed"
        elif "started" in msg and node not in states:
            states[node] = "running"

    return states


@router.get("/runs/{run_id}/stepper", response_class=HTMLResponse)
def run_stepper_partial(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: pipeline node stepper visualization."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.run import Run
    from ainews.models.run_log import RunLog

    run = session.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        return HTMLResponse("")

    logs = (
        session.execute(
            select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.ts)
        )
        .scalars()
        .all()
    )

    node_states = _derive_node_states(logs)

    return _render(
        request,
        "partials/run_stepper.html",
        {"run": run, "node_states": node_states},
    )


@router.get("/runs/{run_id}/report-card", response_class=HTMLResponse)
def run_report_card_partial(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: report summary card for run detail page.

    Polled by the report-card-slot when the run completes but
    the report row hasn't been persisted yet.  Once the report
    exists, the card renders and polling stops automatically.
    """
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.report import Report
    from ainews.models.run import Run

    run = session.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        return HTMLResponse("")

    report = session.execute(
        select(Report).where(Report.run_id == run_id)
    ).scalar_one_or_none()

    return _render(
        request,
        "partials/run_report_card.html",
        {"run": run, "report": report},
    )


@router.get(
    "/runs/{run_id}/logs-partial",
    response_class=HTMLResponse,
)
def run_logs_partial(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: live log entries for a run."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.run import Run
    from ainews.models.run_log import RunLog

    run = session.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        return HTMLResponse("")

    logs = (
        session.execute(
            select(RunLog).where(RunLog.run_id == run_id).order_by(RunLog.ts)
        )
        .scalars()
        .all()
    )

    return _render(
        request,
        "partials/run_logs.html",
        {"run": run, "logs": logs},
    )


@router.get("/runs/{run_id}/raw-log", response_class=HTMLResponse)
def run_raw_log_partial(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: raw worker log output for a run."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.core.config import Settings
    from ainews.models.run import Run

    run = session.execute(
        __import__("sqlalchemy").select(Run).where(Run.id == run_id)
    ).scalar_one_or_none()
    if not run:
        return HTMLResponse("")

    settings = Settings()
    log_path = settings.db_path.parent / "logs" / f"{run_id}.log"
    raw_content = ""
    if log_path.exists():
        try:
            raw_content = log_path.read_text(encoding="utf-8")
        except Exception:
            raw_content = "Error reading log file."

    return _render(
        request,
        "partials/run_raw_log.html",
        {"run": run, "raw_content": raw_content},
    )


@router.get("/runs/{run_id}/raw-log/download")
def run_raw_log_download(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Download the raw worker log file."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.core.config import Settings

    settings = Settings()
    log_path = settings.db_path.parent / "logs" / f"{run_id}.log"
    if not log_path.exists():
        return JSONResponse({"detail": "Raw log not found"}, status_code=404)

    return FileResponse(
        path=str(log_path),
        media_type="text/plain",
        filename=f"worker_{run_id[:12]}.log",
    )


# ── Report Preview & Download ─────────────────────────────


@router.get("/runs/{run_id}/report", response_class=HTMLResponse)
def report_preview(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Render the full markdown report as styled HTML."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    import markdown as md_lib
    from sqlalchemy import select

    from ainews.models.report import Report
    from ainews.models.run import Run

    run = session.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        resp = RedirectResponse(url="/runs", status_code=303)
        flash(resp, "Run not found", "error")
        return resp

    report = session.execute(
        select(Report).where(Report.run_id == run_id)
    ).scalar_one_or_none()
    if not report:
        resp = RedirectResponse(url=f"/runs/{run_id}", status_code=303)
        flash(resp, "No report available for this run", "error")
        return resp

    # Read markdown from disk and convert to HTML
    import re

    report_html = ""
    report_meta: dict[str, object] = {}
    toc_entries: list[dict[str, str]] = []
    md_path = Path(report.full_md_path) if report.full_md_path else None
    if md_path and md_path.exists():
        raw_md = md_path.read_text(encoding="utf-8")

        # ── Extract metadata from markdown header ──
        lines = raw_md.split("\n")
        meta_lines_to_strip = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if i == 0 and stripped.startswith("# "):
                meta_lines_to_strip = 1
                continue
            if stripped.startswith("*") and stripped.endswith("*"):
                meta_lines_to_strip = i + 1
                inner = stripped.strip("*").strip()
                if inner.startswith("Generated:"):
                    report_meta["generated"] = inner.replace("Generated:", "").strip()
                elif inner.startswith("Topics:"):
                    parts = inner.split("|")
                    report_meta["topics"] = parts[0].replace("Topics:", "").strip()
                    if len(parts) > 1:
                        report_meta["window"] = parts[1].replace("Window:", "").strip()
                continue
            if not stripped:
                if meta_lines_to_strip > 0:
                    meta_lines_to_strip = i + 1
                continue
            break  # Stop at first non-metadata line

        # Strip metadata from the markdown body (avoid duplicate title)
        body_md = "\n".join(lines[meta_lines_to_strip:])

        # Count stats from raw markdown
        section_count = len(re.findall(r"^##\s+", raw_md, re.MULTILINE))
        source_count = len(re.findall(
            r"^- https?://", raw_md, re.MULTILINE
        ))
        story_count = len(re.findall(r"^###\s+\d+\.\s+", raw_md, re.MULTILINE))
        report_meta["sections"] = section_count
        report_meta["sources"] = source_count
        report_meta["stories"] = story_count

        # Convert body to HTML
        md_instance = md_lib.Markdown(
            extensions=["tables", "fenced_code", "codehilite", "toc"],
        )
        report_html = md_instance.convert(body_md)

        # Extract TOC entries from rendered headings
        for match in re.finditer(
            r'<h([23])\s+id="([^"]+)"[^>]*>(.*?)</h\1>',
            report_html,
        ):
            level, anchor, text = match.group(1), match.group(2), match.group(3)
            # Strip HTML tags from heading text
            clean_text = re.sub(r"<[^>]+>", "", text).strip()
            toc_entries.append({
                "level": level,
                "anchor": anchor,
                "text": clean_text,
            })
    else:
        report_html = (
            "<p class='text-surface-700/60 "
            "dark:text-surface-200/50'>"
            "Report file not found on disk.</p>"
        )

    return _render(
        request,
        "runs/report.html",
        {
            "run": run,
            "report": report,
            "report_html": report_html,
            "report_meta": report_meta,
            "toc_entries": toc_entries,
            "breadcrumbs": [
                {"label": "Runs", "url": "/runs"},
                {"label": f"Run {run.id[:12]}", "url": f"/runs/{run_id}"},
                {"label": "Report", "url": None},
            ],
        },
    )


@router.get("/runs/{run_id}/report/download/md")
def report_download_md(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Download the markdown report file."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.report import Report

    report = session.execute(
        select(Report).where(Report.run_id == run_id)
    ).scalar_one_or_none()
    if not report or not report.full_md_path:
        return JSONResponse({"detail": "Report not found"}, status_code=404)

    file_path = Path(report.full_md_path)
    if not file_path.exists():
        return JSONResponse({"detail": "File not found on disk"}, status_code=404)

    return FileResponse(
        path=str(file_path),
        media_type="text/markdown",
        filename=f"report_{run_id[:12]}.md",
    )


@router.get("/runs/{run_id}/report/download/xlsx")
def report_download_xlsx(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Download the Excel report file."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.report import Report

    report = session.execute(
        select(Report).where(Report.run_id == run_id)
    ).scalar_one_or_none()
    if not report or not report.xlsx_path:
        return JSONResponse({"detail": "Report not found"}, status_code=404)

    file_path = Path(report.xlsx_path)
    if not file_path.exists():
        return JSONResponse({"detail": "File not found on disk"}, status_code=404)

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"report_{run_id[:12]}.xlsx",
    )


# ── Data Management (Delete) ─────────────────────────────


@router.post("/runs/{run_id}/delete")
def run_delete(
    request: Request,
    run_id: str,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Delete a single run and all its associated logs."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import delete, select

    from ainews.models.run import Run
    from ainews.models.run_log import RunLog

    run = session.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if not run:
        resp = RedirectResponse(url="/runs", status_code=303)
        flash(resp, "Run not found", "error")
        return resp

    # Delete logs first (no FK cascade)
    log_count = session.execute(delete(RunLog).where(RunLog.run_id == run_id)).rowcount
    session.execute(delete(Run).where(Run.id == run_id))
    session.flush()

    resp = RedirectResponse(url="/runs", status_code=303)
    flash(resp, f"Deleted run {run_id[:12]} and {log_count} log(s)", "success")
    return resp


@router.post("/settings/purge-runs")
def settings_purge_runs(
    request: Request,
    older_than_days: int = Form(30),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Delete all runs (and their logs) older than N days."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete, select

    from ainews.models.run import Run
    from ainews.models.run_log import RunLog

    cutoff = (datetime.now(tz=UTC) - timedelta(days=older_than_days)).isoformat()

    # Find runs to delete
    old_run_ids = (
        session.execute(select(Run.id).where(Run.created_at < cutoff)).scalars().all()
    )

    if old_run_ids:
        # Delete associated logs first
        log_count = session.execute(
            delete(RunLog).where(RunLog.run_id.in_(old_run_ids))
        ).rowcount
        run_count = session.execute(delete(Run).where(Run.id.in_(old_run_ids))).rowcount
        session.flush()
        msg = (
            f"Purged {run_count} run(s) and {log_count} log(s)"
            f" older than {older_than_days} days"
        )
    else:
        msg = f"No runs older than {older_than_days} days found"

    resp = RedirectResponse(url="/settings", status_code=303)
    flash(resp, msg, "success")
    return resp


@router.post("/settings/clear-logs")
def settings_clear_logs(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Delete all run logs (keeps run records intact)."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import delete, func, select

    from ainews.models.run_log import RunLog

    count = session.scalar(select(func.count(RunLog.id))) or 0
    session.execute(delete(RunLog))
    session.flush()

    resp = RedirectResponse(url="/settings", status_code=303)
    flash(resp, f"Cleared {count} log entries", "success")
    return resp
