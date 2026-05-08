"""Tests for CSP middleware."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ainews.api.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.state.engine = None  # Skip DB for these tests
    return TestClient(app, raise_server_exceptions=False)


class TestCSPMiddleware:
    def test_csp_header_on_health(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert "Content-Security-Policy" in resp.headers

    def test_csp_header_contains_default_src(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp

    def test_x_content_type_options(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert "Referrer-Policy" in resp.headers
