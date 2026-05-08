"""Tests for Pydantic API schemas — validation rules, required fields, edge cases."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ainews.schemas.health import ComponentStatus, HealthResponse
from ainews.schemas.run import RunDetail, RunDetailResponse, RunListResponse, RunSummary
from ainews.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from ainews.schemas.site import SiteCreate, SiteResponse, SiteUpdate
from ainews.schemas.trigger import TriggerRequest, TriggerResponse


# ── TriggerRequest / TriggerResponse ──────────────────────


class TestTriggerRequest:
    def test_schedule_name_only(self) -> None:
        req = TriggerRequest(schedule_name="weekly-ai-news")
        assert req.schedule_name == "weekly-ai-news"
        assert req.topics is None

    def test_adhoc_params(self) -> None:
        req = TriggerRequest(topics=["AI", "ML"], timeframe_days=14)
        assert req.topics == ["AI", "ML"]
        assert req.timeframe_days == 14
        assert req.schedule_name is None

    def test_empty_request_valid(self) -> None:
        """An empty body is valid — service layer handles missing context."""
        req = TriggerRequest()
        assert req.schedule_name is None

    def test_timeframe_days_range(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            TriggerRequest(timeframe_days=0)

        with pytest.raises(ValidationError, match="less than or equal to 365"):
            TriggerRequest(timeframe_days=999)


class TestTriggerResponse:
    def test_fields(self) -> None:
        resp = TriggerResponse(run_id="abc-123", status="pending")
        assert resp.run_id == "abc-123"
        assert resp.status == "pending"


# ── RunSummary / RunDetail / RunListResponse ──────────────


class TestRunSchemas:
    def test_run_summary_minimal(self) -> None:
        summary = RunSummary(id="r1", status="pending", triggered_by="api")
        assert summary.id == "r1"
        assert summary.schedule_id is None

    def test_run_detail_full(self) -> None:
        detail = RunDetail(
            id="r1",
            status="completed",
            triggered_by="cli",
            stats={"articles": 10},
            error=None,
        )
        assert detail.stats == {"articles": 10}

    def test_run_list_response(self) -> None:
        resp = RunListResponse(
            runs=[RunSummary(id="r1", status="pending", triggered_by="api")],
            total=1,
        )
        assert resp.total == 1
        assert len(resp.runs) == 1

    def test_run_detail_response(self) -> None:
        resp = RunDetailResponse(
            run=RunDetail(id="r1", status="failed", triggered_by="cron", error="timeout"),
        )
        assert resp.run.error == "timeout"


# ── SiteCreate / SiteUpdate / SiteResponse ────────────────


class TestSiteSchemas:
    def test_create_valid(self) -> None:
        site = SiteCreate(url="https://example.com")
        assert site.url == "https://example.com"
        assert site.priority == 5
        assert site.js_render is False
        assert site.enabled is True

    def test_create_bad_url(self) -> None:
        with pytest.raises(ValidationError, match="http://"):
            SiteCreate(url="ftp://bad.example.com")

    def test_create_priority_range(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            SiteCreate(url="https://x.com", priority=0)
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            SiteCreate(url="https://x.com", priority=11)

    def test_update_partial(self) -> None:
        update = SiteUpdate(priority=8)
        assert update.priority == 8
        assert update.url is None

    def test_update_url_validation(self) -> None:
        with pytest.raises(ValidationError, match="http://"):
            SiteUpdate(url="not-a-url")

    def test_response(self) -> None:
        resp = SiteResponse(
            id=1,
            url="https://a.com",
            priority=5,
            crawl_depth=2,
            js_render=False,
            enabled=True,
        )
        assert resp.id == 1


# ── ScheduleCreate / ScheduleUpdate / ScheduleResponse ───


class TestScheduleSchemas:
    def test_create_valid(self) -> None:
        sched = ScheduleCreate(name="weekly", cron_expr="0 7 * * 1")
        assert sched.name == "weekly"
        assert sched.timeframe_days == 7

    def test_create_bad_cron(self) -> None:
        with pytest.raises(ValidationError, match="Invalid cron"):
            ScheduleCreate(name="bad", cron_expr="not a cron")

    def test_create_name_required(self) -> None:
        with pytest.raises(ValidationError):
            ScheduleCreate(name="", cron_expr="0 7 * * 1")

    def test_update_partial(self) -> None:
        update = ScheduleUpdate(timeframe_days=30)
        assert update.timeframe_days == 30
        assert update.cron_expr is None

    def test_update_cron_validation(self) -> None:
        with pytest.raises(ValidationError, match="Invalid cron"):
            ScheduleUpdate(cron_expr="bad")

    def test_update_cron_none_ok(self) -> None:
        update = ScheduleUpdate(cron_expr=None)
        assert update.cron_expr is None

    def test_response(self) -> None:
        resp = ScheduleResponse(
            id=1,
            name="weekly",
            cron_expr="0 7 * * 1",
            timeframe_days=7,
            enabled=True,
        )
        assert resp.id == 1


# ── HealthResponse ────────────────────────────────────────


class TestHealthSchemas:
    def test_healthy(self) -> None:
        resp = HealthResponse(
            status="ok",
            components={
                "db": ComponentStatus(status="ok"),
                "valkey": ComponentStatus(status="ok"),
            },
        )
        assert resp.status == "ok"

    def test_degraded(self) -> None:
        resp = HealthResponse(
            status="degraded",
            components={
                "db": ComponentStatus(status="ok"),
                "valkey": ComponentStatus(status="down", detail="Connection refused"),
            },
        )
        assert resp.components["valkey"].detail == "Connection refused"
