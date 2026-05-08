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
    """Render the dashboard page (auth required)."""
    redirect = _require_auth(request, session)
    if redirect:
        return redirect
    return _render(request, "dashboard.html")
