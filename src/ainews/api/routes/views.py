"""View routes — server-rendered HTML pages for the admin UI."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ainews.api.flash import get_flashed_messages

router = APIRouter(tags=["views"])


def _render(
    request: Request,
    template_name: str,
    context: dict | None = None,
) -> HTMLResponse:
    """Render a Jinja2 template with common context."""
    templates = request.app.state.templates
    ctx = {
        "get_flashed_messages": get_flashed_messages,
        **(context or {}),
    }
    return templates.TemplateResponse(request, template_name, ctx)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """Render the dashboard page."""
    return _render(request, "dashboard.html")
