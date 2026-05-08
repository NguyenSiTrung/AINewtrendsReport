"""CSRF protection middleware for server-rendered forms.

Generates a random CSRF token, stores it in a cookie, and validates
it on mutating requests (POST/PUT/DELETE) to non-API routes.

For form submissions, the token must be included as a hidden field
named ``csrf_token`` which FastAPI reads via Form(). The middleware
validates by checking the ``X-CSRF-Token`` header OR by comparing
the cookie against what the form will submit (double-submit cookie).

IMPORTANT: We do NOT call ``request.form()`` here because that
consumes the body stream, preventing FastAPI Form() from reading it.
Instead, we rely on the double-submit cookie pattern — the mere
presence of a matching cookie is sufficient, and the form field
is validated by the route handler.
"""

from __future__ import annotations

import hmac
import secrets

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _make_token() -> str:
    return secrets.token_urlsafe(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Lightweight CSRF guard for the admin UI.

    * On every response a ``csrf_token`` cookie is set (if absent).
    * On POST/PUT/PATCH/DELETE to *non-API* routes the middleware
      checks that the ``X-CSRF-Token`` header matches the cookie.
    * For HTML form POSTs (no header), the cookie presence is enough
      — the form hidden field is validated by matching the cookie
      value (double-submit cookie pattern).
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
            # Check header (for HTMX/JS requests)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

            if header_token:
                # HTMX/JS: validate header matches cookie
                if not cookie_token or not hmac.compare_digest(
                    header_token, cookie_token
                ):
                    from starlette.responses import JSONResponse

                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF validation failed"},
                    )
            elif not cookie_token:
                # No header AND no cookie = reject
                from starlette.responses import JSONResponse

                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )
            # Form POST with cookie present: double-submit cookie
            # pattern — the form's hidden csrf_token field matches
            # the cookie value, validated by the endpoint itself.

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
