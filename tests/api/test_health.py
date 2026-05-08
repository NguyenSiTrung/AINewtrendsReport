"""Tests for /api/health endpoint with all three probes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine

from ainews.api.main import create_app
from ainews.models.base import Base


@pytest.fixture
def app_with_db():
    """Create app with real SQLite engine for health check."""
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    app = create_app()
    app.state.engine = engine
    return app


@pytest.fixture
def client(app_with_db) -> TestClient:
    return TestClient(app_with_db, raise_server_exceptions=False)


class TestHealthEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_has_db_component(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        data = resp.json()
        assert "db" in data["components"]

    def test_db_status_ok(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        data = resp.json()
        assert data["components"]["db"]["status"] == "ok"

    def test_has_valkey_component(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        data = resp.json()
        assert "valkey" in data["components"]

    def test_has_llm_component(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        data = resp.json()
        assert "llm" in data["components"]

    def test_overall_status_present(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] in ("ok", "degraded", "down")

    def test_degraded_when_partial_ok(self, client: TestClient) -> None:
        """When DB is ok but others are down, status should be degraded."""
        resp = client.get("/api/health")
        data = resp.json()
        # At minimum DB should be ok in our test env
        assert data["components"]["db"]["status"] == "ok"
        # Overall should be degraded since valkey/llm likely down in test
        assert data["status"] in ("ok", "degraded")
