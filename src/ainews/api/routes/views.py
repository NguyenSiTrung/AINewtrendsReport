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


# ── Sites CRUD ───────────────────────────────────────────


@router.get("/sites", response_class=HTMLResponse)
def sites_list(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """List all sites."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.site import Site

    sites = session.execute(select(Site).order_by(Site.priority.desc())).scalars().all()
    return _render(request, "sites/list.html", {"sites": sites})


@router.get("/sites/new", response_class=HTMLResponse)
def site_new_form(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show new site form."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect
    return _render(request, "sites/form.html", {"site": None})


@router.post("/sites/new")
def site_create(
    request: Request,
    url: str = Form(...),
    category: str = Form("tech"),
    priority: int = Form(5),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Create a new site."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.site import Site

    site = Site(url=url, category=category, priority=priority)
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
    return _render(request, "sites/form.html", {"site": site})


@router.post("/sites/{site_id}")
def site_update(
    request: Request,
    site_id: int,
    url: str = Form(...),
    category: str = Form("tech"),
    priority: int = Form(5),
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
        session.flush()

    resp = RedirectResponse(url="/sites", status_code=303)
    flash(resp, "Site updated", "success")
    return resp


# ── Schedules CRUD ───────────────────────────────────────


@router.get("/schedules", response_class=HTMLResponse)
def schedules_list(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """List all schedules."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.schedule import Schedule

    schedules = (
        session.execute(select(Schedule).order_by(Schedule.name)).scalars().all()
    )
    return _render(request, "schedules/list.html", {"schedules": schedules})


@router.get("/schedules/new", response_class=HTMLResponse)
def schedule_new_form(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show new schedule form."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect
    return _render(request, "schedules/form.html", {"schedule": None})


@router.post("/schedules/new")
def schedule_create(
    request: Request,
    name: str = Form(...),
    cron_expr: str = Form(...),
    timeframe_days: int = Form(7),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Create a new schedule."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.schedule import Schedule

    sched = Schedule(
        name=name,
        cron_expr=cron_expr,
        timeframe_days=timeframe_days,
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

    from ainews.models.schedule import Schedule

    sched = session.get(Schedule, schedule_id)
    if not sched:
        return RedirectResponse(url="/schedules", status_code=303)
    return _render(request, "schedules/form.html", {"schedule": sched})


@router.post("/schedules/{schedule_id}")
def schedule_update(
    request: Request,
    schedule_id: int,
    name: str = Form(...),
    cron_expr: str = Form(...),
    timeframe_days: int = Form(7),
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Update an existing schedule."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.models.schedule import Schedule

    sched = session.get(Schedule, schedule_id)
    if sched:
        sched.name = name
        sched.cron_expr = cron_expr
        sched.timeframe_days = timeframe_days
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

    from sqlalchemy import select

    from ainews.models.schedule import Schedule

    schedules = (
        session.execute(select(Schedule).order_by(Schedule.name)).scalars().all()
    )
    return _render(request, "trigger.html", {"schedules": schedules})


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

    from ainews.models.settings_kv import SettingsKV

    row = session.get(SettingsKV, "llm")
    settings_data = row.value if row else {}
    return _render(request, "llm.html", {"settings": settings_data})


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


# ── Runs ─────────────────────────────────────────────────


@router.get("/runs", response_class=HTMLResponse)
def runs_list(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """List all pipeline runs."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.run import Run

    runs = session.execute(select(Run).order_by(Run.created_at.desc())).scalars().all()
    has_active_runs = any(r.status in ("pending", "running") for r in runs)
    return _render(
        request,
        "runs/list.html",
        {"runs": runs, "has_active_runs": has_active_runs},
    )


@router.get("/runs/table", response_class=HTMLResponse)
def runs_table_partial(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """HTMX partial: runs table body with auto-refresh."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.run import Run

    runs = session.execute(select(Run).order_by(Run.created_at.desc())).scalars().all()
    has_active_runs = any(r.status in ("pending", "running") for r in runs)

    return _render(
        request,
        "partials/runs_table.html",
        {"runs": runs, "has_active_runs": has_active_runs},
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
    return _render(
        request,
        "runs/detail.html",
        {
            "run": run,
            "logs": logs,
            "node_states": node_states,
            "report": report,
        },
    )


# ── Logs ─────────────────────────────────────────────────


@router.get("/logs", response_class=HTMLResponse)
def logs_page(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Show recent system logs."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from sqlalchemy import select

    from ainews.models.run_log import RunLog

    logs = (
        session.execute(select(RunLog).order_by(RunLog.ts.desc()).limit(200))
        .scalars()
        .all()
    )
    return _render(request, "logs.html", {"logs": logs})


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

    total_runs = session.scalar(select(func.count(Run.id))) or 0
    total_logs = session.scalar(select(func.count(RunLog.id))) or 0

    return _render(
        request,
        "settings.html",
        {
            "stats": {
                "total_runs": total_runs,
                "total_logs": total_logs,
            },
        },
    )


@router.post("/settings/seed")
def settings_seed(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Seed default sites and schedules."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect

    from ainews.seed import seed_all

    result = seed_all(session)
    msg = f"Seeded: {result.sites_created} sites, {result.schedules_created} schedules"
    resp = RedirectResponse(url="/settings", status_code=303)
    flash(resp, msg, "success")
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
        elif "started" in msg:
            if node not in states:
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
    report_html = ""
    md_path = Path(report.full_md_path) if report.full_md_path else None
    if md_path and md_path.exists():
        raw_md = md_path.read_text(encoding="utf-8")
        report_html = md_lib.markdown(
            raw_md,
            extensions=["tables", "fenced_code", "codehilite", "toc"],
        )
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
