"""Tests for degradation dashboard endpoints.

Story 7-10, Task 5.4: Router tests.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.degradation.models import ServiceHealthStatus, RecoveryResult
from ui.backend.routers.degradation import (
    router,
    get_health_registry,
    get_recovery_processor,
)


@pytest.fixture
def registry_mock():
    """Mock ServiceHealthRegistry."""
    mock = AsyncMock()
    mock.get_all_statuses = AsyncMock(return_value=[])
    mock.get_status = AsyncMock()
    mock.get_queued_count = AsyncMock(return_value=0)
    mock.reset_status = AsyncMock()
    return mock


@pytest.fixture
def processor_mock():
    """Mock RecoveryProcessor."""
    mock = AsyncMock()
    mock.check_and_recover = AsyncMock()
    mock.process_all_services = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def client(registry_mock, processor_mock):
    """Test client with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_health_registry] = lambda: registry_mock
    app.dependency_overrides[get_recovery_processor] = lambda: processor_mock

    return TestClient(app)


class TestGetSystemStatus:
    """Tests for GET /api/system/status."""

    def test_returns_all_services(self, client, registry_mock):
        """GET /api/system/status returns all monitored services."""
        now = datetime.now(UTC)
        registry_mock.get_all_statuses.return_value = [
            ServiceHealthStatus(service_name="instagram", status="healthy", updated_at=now),
            ServiceHealthStatus(service_name="shopify", status="healthy", updated_at=now),
        ]

        response = client.get("/api/system/status")

        assert response.status_code == 200
        data = response.json()
        assert len(data["services"]) == 2
        assert data["overall_status"] == "healthy"

    def test_overall_status_reflects_worst(self, client, registry_mock):
        """overall_status reflects the worst service status."""
        now = datetime.now(UTC)
        registry_mock.get_all_statuses.return_value = [
            ServiceHealthStatus(service_name="instagram", status="healthy", updated_at=now),
            ServiceHealthStatus(service_name="shopify", status="degraded", consecutive_failures=5, updated_at=now),
            ServiceHealthStatus(service_name="discord", status="unhealthy", consecutive_failures=15, updated_at=now),
        ]

        response = client.get("/api/system/status")

        assert response.status_code == 200
        assert response.json()["overall_status"] == "unhealthy"

    def test_includes_total_queued_operations(self, client, registry_mock):
        """Response includes total_queued_operations summed across services."""
        now = datetime.now(UTC)
        registry_mock.get_all_statuses.return_value = [
            ServiceHealthStatus(service_name="instagram", status="degraded", updated_at=now),
            ServiceHealthStatus(service_name="shopify", status="healthy", updated_at=now),
        ]
        # Return 3 for instagram, 2 for shopify
        registry_mock.get_queued_count.side_effect = [3, 2]

        response = client.get("/api/system/status")

        assert response.status_code == 200
        assert response.json()["total_queued_operations"] == 5


class TestGetServiceStatus:
    """Tests for GET /api/system/status/{service_name}."""

    def test_returns_single_service(self, client, registry_mock):
        """GET /api/system/status/instagram returns single service status."""
        now = datetime.now(UTC)
        registry_mock.get_status.return_value = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=5,
            last_error="Timeout",
            updated_at=now,
        )

        response = client.get("/api/system/status/instagram")

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "instagram"
        assert data["status"] == "degraded"
        assert data["consecutive_failures"] == 5

    def test_unknown_service_returns_404(self, client):
        """GET /api/system/status/unknown returns 404."""
        response = client.get("/api/system/status/unknown_service")

        assert response.status_code == 404


class TestTriggerRecovery:
    """Tests for POST /api/system/recover."""

    def test_recover_all_services(self, client, processor_mock):
        """POST /api/system/recover recovers all services."""
        processor_mock.process_all_services.return_value = [
            RecoveryResult(service_name="instagram", processed=2, remaining=0),
            RecoveryResult(service_name="shopify", processed=0, remaining=0),
        ]

        response = client.post("/api/system/recover", json={})

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["processed"] == 2

    def test_recover_single_service(self, client, processor_mock):
        """POST /api/system/recover with service_name recovers single service."""
        processor_mock.check_and_recover.return_value = RecoveryResult(
            service_name="instagram", processed=3, remaining=1
        )

        response = client.post("/api/system/recover", json={"service_name": "instagram"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["service_name"] == "instagram"
        assert data["results"][0]["processed"] == 3


class TestResetServiceStatus:
    """Tests for POST /api/system/reset/{service_name}."""

    def test_resets_to_healthy(self, client, registry_mock):
        """POST /api/system/reset/instagram resets service to healthy."""
        now = datetime.now(UTC)
        registry_mock.reset_status.return_value = ServiceHealthStatus(
            service_name="instagram",
            status="healthy",
            consecutive_failures=0,
            last_success=now,
            updated_at=now,
        )

        response = client.post("/api/system/reset/instagram")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["consecutive_failures"] == 0

    def test_unknown_service_returns_404(self, client):
        """POST /api/system/reset/unknown returns 404."""
        response = client.post("/api/system/reset/unknown_service")

        assert response.status_code == 404


class TestAllHealthyVsDegraded:
    """Tests for response when all healthy vs when some degraded."""

    def test_all_healthy(self, client, registry_mock):
        """When all services healthy, overall_status is healthy."""
        now = datetime.now(UTC)
        registry_mock.get_all_statuses.return_value = [
            ServiceHealthStatus(service_name="instagram", status="healthy", updated_at=now),
            ServiceHealthStatus(service_name="shopify", status="healthy", updated_at=now),
        ]

        response = client.get("/api/system/status")

        assert response.json()["overall_status"] == "healthy"

    def test_some_degraded(self, client, registry_mock):
        """When some services degraded, overall_status is degraded."""
        now = datetime.now(UTC)
        registry_mock.get_all_statuses.return_value = [
            ServiceHealthStatus(service_name="instagram", status="healthy", updated_at=now),
            ServiceHealthStatus(service_name="shopify", status="degraded", consecutive_failures=5, updated_at=now),
        ]

        response = client.get("/api/system/status")

        assert response.json()["overall_status"] == "degraded"
