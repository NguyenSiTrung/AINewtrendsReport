"""CSRF protection middleware for server-rendered forms.

Generates a random CSRF token, stores it in a cookie, and validates
it on mutating requests (POST/PUT/DELETE) to non-API routes.

Uses the **double-submit cookie** pattern with header validation:
- Every response gets a ``csrf_token`` cookie (SameSite=Lax).
- Mutating requests must include the token via ``X-CSRF-Token`` header.
- HTMX reads the cookie and sends it as a header automatically via
  ``hx-headers`` configured in the base template.
- The ``SameSite=Lax`` attribute on the cookie provides baseline
  protection against cross-site form submissions.

API routes (``/api/*``) are exempt — they use JWT bearer auth.
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
    * The base template configures HTMX to send the cookie value as
      the ``X-CSRF-Token`` header on all requests.
    * Forms include a hidden ``csrf_token`` field; a small inline
      script copies it to the ``X-CSRF-Token`` header before submit.
    * Requests to ``/api/*`` are exempt — they rely on JWT auth.

    NOTE: We intentionally do NOT read ``request.form()`` here because
    ``BaseHTTPMiddleware`` wraps the ASGI body stream, and reading it
    in the middleware prevents FastAPI ``Form()`` dependencies from
    accessing it downstream. Header-only checking avoids this issue.
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
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)

            # Fallback to form body for standard HTML form submissions
            form_token = None
            if not header_token and "application/x-www-form-urlencoded" in request.headers.get("content-type", ""):
                body = await request.body()
                from urllib.parse import parse_qs
                parsed = parse_qs(body.decode("utf-8", errors="replace"))
                form_token = parsed.get("csrf_token", [None])[0]

            token_to_verify = header_token or form_token

            if not cookie_token or not token_to_verify:
                # Missing cookie or token → reject
                return self._reject()
            if not hmac.compare_digest(token_to_verify, cookie_token):
                # Token mismatch → reject
                return self._reject()

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

    @staticmethod
    def _reject() -> Response:
        """Return a 403 CSRF rejection response."""
        from starlette.responses import JSONResponse

        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF validation failed"},
        )
