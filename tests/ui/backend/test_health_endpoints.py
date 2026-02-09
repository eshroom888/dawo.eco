"""Tests for health check endpoints.

Story 4-5, Task 10.3: Tests for health check API.
Tests cover:
- Overall health endpoint
- Publishing health endpoint
- Publishing metrics endpoint
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from ui.backend.routers.health import router
from core.publishing.metrics import (
    PublishMetricsCollector,
    PublishMetrics,
    HealthStatus,
)


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_collector():
    """Create mock metrics collector."""
    collector = MagicMock(spec=PublishMetricsCollector)

    # Default healthy metrics
    collector.get_metrics.return_value = PublishMetrics(
        total_attempts=100,
        successful_publishes=99,
        failed_publishes=1,
        success_rate=99.0,
        avg_latency_seconds=2.5,
        max_latency_seconds=5.0,
        min_latency_seconds=1.0,
        quota_remaining=150,
        quota_reset_at=datetime.utcnow(),
    )

    collector.get_health_status.return_value = HealthStatus(
        healthy=True,
        instagram_api_available=True,
        last_successful_publish=datetime.utcnow(),
        last_failed_publish=None,
        consecutive_failures=0,
        details={"success_rate": 99.0},
    )

    collector.LATENCY_TARGET_SECONDS = 30.0
    collector.SUCCESS_RATE_THRESHOLD = 99.0

    return collector


class TestOverallHealthEndpoint:
    """Tests for GET /api/health."""

    def test_healthy_status(self, client, mock_collector):
        """Test healthy overall status."""
        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert data["services"]["instagram_publishing"]["healthy"] is True

    def test_degraded_status(self, client, mock_collector):
        """Test degraded status with consecutive failures."""
        mock_collector.get_health_status.return_value = HealthStatus(
            healthy=True,
            instagram_api_available=True,
            consecutive_failures=2,
        )

        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_unhealthy_status(self, client, mock_collector):
        """Test unhealthy status."""
        mock_collector.get_health_status.return_value = HealthStatus(
            healthy=False,
            instagram_api_available=False,
            consecutive_failures=5,
        )

        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"


class TestPublishingHealthEndpoint:
    """Tests for GET /api/health/publishing."""

    def test_publishing_health_response(self, client, mock_collector):
        """Test publishing health endpoint response."""
        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health/publishing")

        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert data["instagram_api_available"] is True
        assert data["consecutive_failures"] == 0
        assert data["success_rate"] == 99.0
        assert data["avg_latency_seconds"] == 2.5
        assert data["quota_remaining"] == 150

    def test_unhealthy_publishing(self, client, mock_collector):
        """Test unhealthy publishing status."""
        mock_collector.get_health_status.return_value = HealthStatus(
            healthy=False,
            instagram_api_available=False,
            consecutive_failures=5,
        )
        mock_collector.get_metrics.return_value = PublishMetrics(
            success_rate=50.0,
            avg_latency_seconds=10.0,
            quota_remaining=50,
        )

        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health/publishing")

        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is False
        assert data["instagram_api_available"] is False


class TestPublishingMetricsEndpoint:
    """Tests for GET /api/health/metrics."""

    def test_metrics_response(self, client, mock_collector):
        """Test metrics endpoint response."""
        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_attempts"] == 100
        assert data["successful_publishes"] == 99
        assert data["failed_publishes"] == 1
        assert data["success_rate"] == 99.0
        assert data["avg_latency_seconds"] == 2.5
        assert data["max_latency_seconds"] == 5.0
        assert data["min_latency_seconds"] == 1.0
        assert data["quota_remaining"] == 150
        assert data["latency_target_seconds"] == 30.0
        assert data["success_rate_threshold"] == 99.0

    def test_metrics_with_zero_attempts(self, client, mock_collector):
        """Test metrics with no publish attempts."""
        mock_collector.get_metrics.return_value = PublishMetrics()

        with patch(
            "ui.backend.routers.health.get_metrics_collector",
            return_value=mock_collector,
        ):
            response = client.get("/api/health/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_attempts"] == 0
        assert data["success_rate"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
