"""Tests for Agent Schedule router.

Story 7-6, Task 7.4: Router tests with mock service, error cases, validation.
Target: 15+ tests.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.scheduling.dtos import AgentScheduleDTO, DependencyWarning, ScheduleChangeLogDTO
from ui.backend.routers.schedules import (
    router,
    get_schedule_service,
)


def _make_dto(**overrides) -> AgentScheduleDTO:
    """Create a test AgentScheduleDTO."""
    defaults = {
        "id": uuid4(),
        "agent_name": "health_claims_monitor",
        "display_name": "EU Health Claims Monitor",
        "description": None,
        "schedule_cron": "0 5 * * 0",
        "cron_human_readable": "Weekly on Sunday at 05:00",
        "timezone": "UTC",
        "enabled": True,
        "last_run_at": None,
        "last_run_status": None,
        "last_run_duration_seconds": None,
        "next_run_at": datetime(2026, 3, 1, 5, 0, tzinfo=UTC),
        "dependencies": [],
        "config_source": "dawo_health_claims.json",
    }
    defaults.update(overrides)
    return AgentScheduleDTO(**defaults)


def _make_app(mock_service: AsyncMock) -> FastAPI:
    """Create test app with schedule router and mocked service."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_schedule_service] = lambda: mock_service
    return app


class TestListSchedules:
    """Tests for GET /api/schedules/."""

    def test_returns_all_schedules(self) -> None:
        mock_service = AsyncMock()
        dto1 = _make_dto(agent_name="health_claims_monitor")
        dto2 = _make_dto(agent_name="novel_food_monitor", display_name="Novel Food Monitor")
        mock_service.get_all_schedules.return_value = [dto1, dto2]

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/schedules/")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["schedules"]) == 2
        assert data["schedules"][0]["agent_name"] == "health_claims_monitor"

    def test_empty_list(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_all_schedules.return_value = []

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/schedules/")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["schedules"] == []


class TestGetSchedule:
    """Tests for GET /api/schedules/{agent_name}."""

    def test_returns_schedule(self) -> None:
        mock_service = AsyncMock()
        dto = _make_dto()
        mock_service.get_schedule.return_value = dto

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/schedules/health_claims_monitor")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_name"] == "health_claims_monitor"
        assert data["cron_human_readable"] == "Weekly on Sunday at 05:00"

    def test_not_found(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_schedule.return_value = None

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/schedules/nonexistent_agent")

        assert response.status_code == 404


class TestUpdateSchedule:
    """Tests for PUT /api/schedules/{agent_name}."""

    def test_update_cron(self) -> None:
        mock_service = AsyncMock()
        updated = _make_dto(schedule_cron="0 6 * * 0")
        mock_service.update_schedule.return_value = updated
        mock_service.check_dependencies.return_value = []

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.put(
            "/api/schedules/health_claims_monitor",
            json={"schedule_cron": "0 6 * * 0"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["schedule"]["schedule_cron"] == "0 6 * * 0"
        assert data["warnings"] == []

    def test_update_with_dependency_warnings(self) -> None:
        mock_service = AsyncMock()
        updated = _make_dto(schedule_cron="0 3 * * *")
        mock_service.update_schedule.return_value = updated
        mock_service.check_dependencies.return_value = [
            DependencyWarning(
                agent_name="post_publish_scoring",
                dependency_name="shopify_attribution_poll",
                agent_next_run=datetime(2026, 3, 1, 3, 0, tzinfo=UTC),
                dependency_next_run=datetime(2026, 3, 1, 3, 0, tzinfo=UTC),
                warning_message="May run before dependency completes",
                severity="warning",
            )
        ]

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.put(
            "/api/schedules/post_publish_scoring",
            json={"schedule_cron": "0 3 * * *"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["severity"] == "warning"

    def test_update_not_found(self) -> None:
        mock_service = AsyncMock()
        mock_service.update_schedule.return_value = None

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.put(
            "/api/schedules/nonexistent_agent",
            json={"schedule_cron": "0 6 * * 0"},
        )

        assert response.status_code == 404

    def test_update_invalid_cron(self) -> None:
        mock_service = AsyncMock()
        mock_service.update_schedule.side_effect = ValueError(
            "Invalid cron expression: bad_cron"
        )

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.put(
            "/api/schedules/health_claims_monitor",
            json={"schedule_cron": "bad_cron"},
        )

        assert response.status_code == 400
        assert "Invalid cron" in response.json()["detail"]


class TestToggleEnabled:
    """Tests for POST /api/schedules/{agent_name}/toggle."""

    def test_disable_schedule(self) -> None:
        mock_service = AsyncMock()
        dto = _make_dto(enabled=False)
        mock_service.toggle_enabled.return_value = dto

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post(
            "/api/schedules/health_claims_monitor/toggle",
            json={"enabled": False},
        )

        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_enable_schedule(self) -> None:
        mock_service = AsyncMock()
        dto = _make_dto(enabled=True)
        mock_service.toggle_enabled.return_value = dto

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post(
            "/api/schedules/health_claims_monitor/toggle",
            json={"enabled": True},
        )

        assert response.status_code == 200
        assert response.json()["enabled"] is True

    def test_toggle_not_found(self) -> None:
        mock_service = AsyncMock()
        mock_service.toggle_enabled.return_value = None

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post(
            "/api/schedules/nonexistent/toggle",
            json={"enabled": True},
        )

        assert response.status_code == 404


class TestAuditLog:
    """Tests for GET /api/schedules/{agent_name}/audit."""

    def test_returns_audit_entries(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_audit_log.return_value = [
            ScheduleChangeLogDTO(
                id=str(uuid4()),
                agent_name="health_claims_monitor",
                field_changed="schedule_cron",
                old_value="0 5 * * 0",
                new_value="0 6 * * 0",
                changed_by="operator",
                created_at=datetime(2026, 2, 27, 12, 0, tzinfo=UTC),
            )
        ]

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/schedules/health_claims_monitor/audit")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["field_changed"] == "schedule_cron"

    def test_audit_empty(self) -> None:
        mock_service = AsyncMock()
        mock_service.get_audit_log.return_value = []

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.get("/api/schedules/health_claims_monitor/audit")

        assert response.status_code == 200
        assert response.json()["entries"] == []


class TestSeedDefaults:
    """Tests for POST /api/schedules/seed."""

    def test_seed_returns_count(self) -> None:
        mock_service = AsyncMock()
        mock_service.seed_defaults.return_value = 8

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post("/api/schedules/seed")

        assert response.status_code == 200
        assert response.json()["seeded_count"] == 8

    def test_seed_already_populated(self) -> None:
        mock_service = AsyncMock()
        mock_service.seed_defaults.return_value = 0

        app = _make_app(mock_service)
        client = TestClient(app)
        response = client.post("/api/schedules/seed")

        assert response.status_code == 200
        assert response.json()["seeded_count"] == 0
