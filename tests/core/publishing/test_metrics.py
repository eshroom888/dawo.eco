"""Tests for PublishMetricsCollector.

Story 4-5, Task 10: Tests for performance and monitoring.
Tests cover:
- Metric recording (success/failure)
- Latency tracking
- Success rate calculation
- Quota tracking
- Health status
"""

import pytest
from datetime import datetime, timedelta

from core.publishing.metrics import (
    PublishMetricsCollector,
    PublishMetrics,
    HealthStatus,
)


class TestPublishMetricsCollector:
    """Tests for PublishMetricsCollector."""

    @pytest.fixture
    def collector(self):
        """Create a fresh collector for each test."""
        return PublishMetricsCollector()

    def test_initial_metrics(self, collector):
        """Test initial metrics are zeroed."""
        metrics = collector.get_metrics()

        assert metrics.total_attempts == 0
        assert metrics.successful_publishes == 0
        assert metrics.failed_publishes == 0
        assert metrics.success_rate == 100.0
        assert metrics.avg_latency_seconds == 0.0

    def test_record_successful_publish(self, collector):
        """Test recording a successful publish."""
        collector.record_publish_attempt(
            success=True,
            latency_seconds=2.5,
        )

        metrics = collector.get_metrics()
        assert metrics.total_attempts == 1
        assert metrics.successful_publishes == 1
        assert metrics.failed_publishes == 0
        assert metrics.success_rate == 100.0
        assert metrics.avg_latency_seconds == 2.5

    def test_record_failed_publish(self, collector):
        """Test recording a failed publish."""
        collector.record_publish_attempt(
            success=False,
            latency_seconds=1.0,
            error_message="API error",
        )

        metrics = collector.get_metrics()
        assert metrics.total_attempts == 1
        assert metrics.successful_publishes == 0
        assert metrics.failed_publishes == 1
        assert metrics.success_rate == 0.0

    def test_success_rate_calculation(self, collector):
        """Test success rate calculation with mixed outcomes."""
        # 8 successes, 2 failures = 80% success rate
        for _ in range(8):
            collector.record_publish_attempt(success=True, latency_seconds=1.0)
        for _ in range(2):
            collector.record_publish_attempt(success=False, latency_seconds=1.0)

        metrics = collector.get_metrics()
        assert metrics.success_rate == 80.0

    def test_latency_statistics(self, collector):
        """Test latency min/max/avg calculation."""
        latencies = [1.0, 2.0, 3.0, 4.0, 5.0]
        for lat in latencies:
            collector.record_publish_attempt(success=True, latency_seconds=lat)

        metrics = collector.get_metrics()
        assert metrics.min_latency_seconds == 1.0
        assert metrics.max_latency_seconds == 5.0
        assert metrics.avg_latency_seconds == 3.0

    def test_consecutive_failures_tracking(self, collector):
        """Test consecutive failure count."""
        # 3 consecutive failures
        for _ in range(3):
            collector.record_publish_attempt(success=False, latency_seconds=1.0)

        health = collector.get_health_status()
        assert health.consecutive_failures == 3

        # Success resets count
        collector.record_publish_attempt(success=True, latency_seconds=1.0)
        health = collector.get_health_status()
        assert health.consecutive_failures == 0

    def test_health_status_healthy(self, collector):
        """Test healthy status with good metrics."""
        for _ in range(10):
            collector.record_publish_attempt(success=True, latency_seconds=1.0)

        health = collector.get_health_status()
        assert health.healthy is True
        assert health.instagram_api_available is True
        assert health.consecutive_failures == 0

    def test_health_status_unhealthy_failures(self, collector):
        """Test unhealthy status with consecutive failures."""
        # Exceed failure threshold (3)
        for _ in range(4):
            collector.record_publish_attempt(success=False, latency_seconds=1.0)

        health = collector.get_health_status()
        assert health.healthy is False
        assert health.consecutive_failures == 4

    def test_api_availability_flag(self, collector):
        """Test Instagram API availability flag."""
        assert collector.get_health_status().instagram_api_available is True

        collector.set_instagram_api_available(False)
        health = collector.get_health_status()
        assert health.instagram_api_available is False
        assert health.healthy is False

        collector.set_instagram_api_available(True)
        assert collector.get_health_status().instagram_api_available is True

    def test_quota_tracking(self, collector):
        """Test API quota tracking."""
        # Initial quota
        metrics = collector.get_metrics()
        assert metrics.quota_remaining == 200

        # Record 10 calls
        for _ in range(10):
            collector.record_publish_attempt(success=True, latency_seconds=1.0)

        metrics = collector.get_metrics()
        assert metrics.quota_remaining == 190

    def test_last_publish_timestamps(self, collector):
        """Test last successful/failed publish timestamps."""
        collector.record_publish_attempt(success=True, latency_seconds=1.0)
        health = collector.get_health_status()
        assert health.last_successful_publish is not None
        assert health.last_failed_publish is None

        collector.record_publish_attempt(success=False, latency_seconds=1.0)
        health = collector.get_health_status()
        assert health.last_failed_publish is not None

    def test_reset(self, collector):
        """Test metrics reset."""
        # Add some data
        for _ in range(5):
            collector.record_publish_attempt(success=True, latency_seconds=2.0)
        collector.record_publish_attempt(success=False, latency_seconds=1.0)

        # Reset
        collector.reset()

        metrics = collector.get_metrics()
        assert metrics.total_attempts == 0
        assert metrics.successful_publishes == 0
        assert metrics.failed_publishes == 0

        health = collector.get_health_status()
        assert health.consecutive_failures == 0
        assert health.last_successful_publish is None


class TestPublishMetrics:
    """Tests for PublishMetrics dataclass."""

    def test_default_values(self):
        """Test default values for PublishMetrics."""
        metrics = PublishMetrics()

        assert metrics.total_attempts == 0
        assert metrics.successful_publishes == 0
        assert metrics.failed_publishes == 0
        assert metrics.success_rate == 100.0
        assert metrics.quota_remaining == 200


class TestHealthStatus:
    """Tests for HealthStatus dataclass."""

    def test_default_values(self):
        """Test default values for HealthStatus."""
        status = HealthStatus()

        assert status.healthy is True
        assert status.instagram_api_available is True
        assert status.consecutive_failures == 0
        assert status.details == {}

    def test_unhealthy_status(self):
        """Test unhealthy status construction."""
        status = HealthStatus(
            healthy=False,
            instagram_api_available=False,
            consecutive_failures=5,
            details={"error": "API unreachable"},
        )

        assert status.healthy is False
        assert status.consecutive_failures == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
