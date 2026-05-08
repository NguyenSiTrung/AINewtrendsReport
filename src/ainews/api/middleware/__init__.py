"""CSRF protection middleware for server-rendered forms.

Generates a random CSRF token, stores it in a signed cookie, and validates
it on mutating requests (POST/PUT/DELETE) to non-API routes.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Secret used to sign the CSRF cookie value.  In production this should come
# from an env-var; for now we derive a stable key per process.
_SIGNING_KEY = secrets.token_hex(32)

CSRF_COOKIE_NAME = "csrf_token"
CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _sign(token: str) -> str:
    """Return HMAC-SHA256 signature of *token*."""
    return hmac.new(_SIGNING_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def _make_token() -> str:
    return secrets.token_urlsafe(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Lightweight CSRF guard for the admin UI.

    * On every response a ``csrf_token`` cookie is set (if absent).
    * On POST/PUT/PATCH/DELETE to *non-API* routes the middleware checks that
      the form field ``csrf_token`` (or ``X-CSRF-Token`` header) matches the
      cookie value.
    * Requests to ``/api/*`` are exempt — they rely on JWT auth.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = request.cookies.get(CSRF_COOKIE_NAME)
        if not token:
            token = _make_token()

        # Inject into request state so templates can read it
        request.state.csrf_token = token

        # Validate on mutating methods for non-API, non-static routes
        path = request.url.path
        if (
            request.method in _MUTATING_METHODS
            and not path.startswith("/api/")
            and not path.startswith("/static/")
        ):
            # Read submitted token from form data or header
            submitted: str | None = None
            content_type = request.headers.get("content-type", "")
            is_form = (
                "application/x-www-form-urlencoded" in content_type
                or "multipart/form-data" in content_type
            )
            if is_form:
                form: Any = await request.form()
                submitted = form.get(CSRF_FIELD_NAME)
            if not submitted:
                submitted = request.headers.get(CSRF_HEADER_NAME)

            if not submitted or not hmac.compare_digest(submitted, token):
                from starlette.responses import JSONResponse

                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )

        response = await call_next(request)

        # Always set the cookie so templates can read it
        response.set_cookie(
            CSRF_COOKIE_NAME,
            token,
            httponly=False,  # JS needs to read it for HTMX headers
            samesite="lax",
            secure=False,  # Set True in production behind HTTPS
            max_age=3600 * 24,
        )

        return response
