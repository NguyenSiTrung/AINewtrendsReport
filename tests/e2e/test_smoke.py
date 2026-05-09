"""E2E smoke tests for deployment validation.

These tests verify the full stack is operational by probing the
running application through its HTTP API. They are designed to be
run against a deployed instance (local or remote).

Usage:
    # Against local dev server
    pytest tests/e2e/test_smoke.py -v

    # Against deployed instance
    AINEWS_BASE_URL=http://server:8000 pytest tests/e2e/test_smoke.py -v
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("AINEWS_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = int(os.environ.get("AINEWS_E2E_TIMEOUT", "600"))  # 10 min default


def _server_reachable() -> bool:
    """Check if the target server is reachable."""
    try:
        httpx.get(f"{BASE_URL}/api/health", timeout=3)
        return True
    except Exception:
        return False


# Skip all tests in this module if the server is not running
pytestmark = pytest.mark.skipif(
    not _server_reachable(),
    reason=f"E2E server not reachable at {BASE_URL}",
)


def _get(path: str, **kwargs) -> httpx.Response:
    """Helper for GET requests to the test server."""
    return httpx.get(f"{BASE_URL}{path}", timeout=30, **kwargs)


def _post(path: str, **kwargs) -> httpx.Response:
    """Helper for POST requests to the test server."""
    return httpx.post(f"{BASE_URL}{path}", timeout=30, **kwargs)


def _get_auth_cookies() -> dict[str, str]:
    """Login and return cookies for authenticated API requests.

    Uses AINEWS_ADMIN_EMAIL / AINEWS_ADMIN_PASSWORD env vars,
    defaulting to admin@ainews.local / admin.
    """
    email = os.environ.get("AINEWS_ADMIN_EMAIL", "admin@ainews.local")
    password = os.environ.get("AINEWS_ADMIN_PASSWORD", "admin")

    with httpx.Client(base_url=BASE_URL, timeout=30, follow_redirects=False) as client:
        # Get CSRF token from login page
        login_page = client.get("/login")
        csrf_cookie = login_page.cookies.get("csrf_token", "")

        # POST login
        resp = client.post(
            "/login",
            data={
                "email": email,
                "password": password,
                "csrf_token": csrf_cookie,
            },
            cookies={"csrf_token": csrf_cookie},
        )

        # Extract JWT cookie from redirect response
        jwt_token = resp.cookies.get("access_token")
        if jwt_token:
            return {"access_token": jwt_token}

    return {}


def _auth_get(path: str, cookies: dict[str, str], **kwargs) -> httpx.Response:
    """GET with authentication cookies."""
    return httpx.get(f"{BASE_URL}{path}", timeout=30, cookies=cookies, **kwargs)


def _auth_post(path: str, cookies: dict[str, str], **kwargs) -> httpx.Response:
    """POST with authentication cookies."""
    return httpx.post(f"{BASE_URL}{path}", timeout=30, cookies=cookies, **kwargs)


class TestHealthEndpoint:
    """Verify the /api/health endpoint returns structured status."""

    def test_health_returns_200(self) -> None:
        resp = _get("/api/health")
        assert resp.status_code == 200

    def test_health_has_components(self) -> None:
        resp = _get("/api/health")
        data = resp.json()
        assert "status" in data
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_health_has_db_component(self) -> None:
        resp = _get("/api/health")
        data = resp.json()
        assert "db" in data["components"]
        assert data["components"]["db"]["status"] in ("ok", "down")

    def test_health_has_valkey_component(self) -> None:
        resp = _get("/api/health")
        data = resp.json()
        assert "valkey" in data["components"]

    def test_health_has_llm_component(self) -> None:
        resp = _get("/api/health")
        data = resp.json()
        assert "llm" in data["components"]


class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    def test_csp_header_present(self) -> None:
        resp = _get("/api/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src" in csp

    def test_x_content_type_options(self) -> None:
        resp = _get("/api/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self) -> None:
        resp = _get("/api/health")
        assert resp.headers.get("x-frame-options") == "DENY"


class TestAPIAuthentication:
    """Verify API endpoints require authentication."""

    def test_unauthenticated_runs_returns_401(self) -> None:
        resp = _get("/api/runs")
        assert resp.status_code == 401

    def test_unauthenticated_sites_returns_401(self) -> None:
        resp = _get("/api/sites")
        assert resp.status_code == 401

    def test_unauthenticated_schedules_returns_401(self) -> None:
        resp = _get("/api/schedules")
        assert resp.status_code == 401

    def test_unauthenticated_trigger_returns_401(self) -> None:
        resp = _post("/api/trigger", json={"schedule_name": "test"})
        assert resp.status_code == 401


class TestAPIEndpoints:
    """Verify core API endpoints respond correctly with authentication."""

    @pytest.fixture(autouse=True)
    def _auth(self) -> None:
        self.cookies = _get_auth_cookies()
        if not self.cookies:
            pytest.skip("Could not authenticate — check admin credentials")

    def test_list_runs(self) -> None:
        resp = _auth_get("/api/runs", self.cookies)
        assert resp.status_code == 200

    def test_list_sites(self) -> None:
        resp = _auth_get("/api/sites", self.cookies)
        assert resp.status_code == 200

    def test_list_schedules(self) -> None:
        resp = _auth_get("/api/schedules", self.cookies)
        assert resp.status_code == 200


class TestPipelineTrigger:
    """Trigger a pipeline run and poll for completion.

    This test is skipped unless AINEWS_E2E_RUN=1 is set, as it
    requires a fully configured environment with LLM + Tavily.
    """

    @pytest.mark.skipif(
        os.environ.get("AINEWS_E2E_RUN", "0") != "1",
        reason="Set AINEWS_E2E_RUN=1 to enable pipeline E2E tests",
    )
    def test_trigger_and_poll(self) -> None:
        cookies = _get_auth_cookies()
        if not cookies:
            pytest.skip("Could not authenticate — check admin credentials")

        # Trigger a run
        trigger_resp = _auth_post(
            "/api/trigger",
            cookies,
            json={"schedule_name": "weekly-ai-news"},
        )
        assert trigger_resp.status_code in (201, 409)

        if trigger_resp.status_code == 409:
            pytest.skip("A run is already in progress")

        data = trigger_resp.json()
        run_id = data.get("run_id")
        assert run_id is not None

        # Poll for completion
        deadline = time.time() + TIMEOUT
        status = "pending"
        while time.time() < deadline:
            status_resp = _auth_get(f"/api/runs/{run_id}", cookies)
            assert status_resp.status_code == 200
            run_data = status_resp.json()
            status = run_data.get("run", {}).get("status", "")

            if status in ("completed", "failed", "capped"):
                break
            time.sleep(10)
        else:
            pytest.fail(f"Run {run_id} did not complete within {TIMEOUT}s")

        assert status in ("completed", "capped"), f"Run ended with status: {status}"
