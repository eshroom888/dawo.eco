"""Tests for degradation data models.

Story 7-10, Task 1.6: ServiceHealthStatus and RecoveryResult frozen dataclass tests.
"""

import pytest
from datetime import datetime, UTC

from core.degradation.models import ServiceHealthStatus, RecoveryResult


class TestServiceHealthStatus:
    """Tests for ServiceHealthStatus frozen dataclass."""

    def test_create_with_defaults(self):
        """ServiceHealthStatus has sensible defaults."""
        status = ServiceHealthStatus(service_name="instagram")
        assert status.service_name == "instagram"
        assert status.status == "healthy"
        assert status.consecutive_failures == 0
        assert status.last_success is None
        assert status.last_failure is None
        assert status.last_error is None
        assert status.queued_operations == 0
        assert status.updated_at is None

    def test_create_with_all_fields(self):
        """ServiceHealthStatus accepts all fields."""
        now = datetime.now(UTC)
        status = ServiceHealthStatus(
            service_name="shopify",
            status="degraded",
            consecutive_failures=5,
            last_success=now,
            last_failure=now,
            last_error="Connection timeout",
            queued_operations=3,
            updated_at=now,
        )
        assert status.service_name == "shopify"
        assert status.status == "degraded"
        assert status.consecutive_failures == 5
        assert status.last_error == "Connection timeout"
        assert status.queued_operations == 3

    def test_frozen_immutability(self):
        """ServiceHealthStatus is frozen — cannot mutate."""
        status = ServiceHealthStatus(service_name="discord")
        with pytest.raises(AttributeError):
            status.status = "degraded"

    def test_frozen_consecutive_failures(self):
        """Cannot mutate consecutive_failures on frozen dataclass."""
        status = ServiceHealthStatus(service_name="discord")
        with pytest.raises(AttributeError):
            status.consecutive_failures = 5


class TestRecoveryResult:
    """Tests for RecoveryResult frozen dataclass."""

    def test_create_with_defaults(self):
        """RecoveryResult has sensible defaults."""
        result = RecoveryResult(service_name="instagram")
        assert result.service_name == "instagram"
        assert result.processed == 0
        assert result.remaining == 0
        assert result.errors == []

    def test_create_with_all_fields(self):
        """RecoveryResult accepts all fields."""
        result = RecoveryResult(
            service_name="shopify",
            processed=5,
            remaining=3,
            errors=["Timeout on op-1", "429 on op-2"],
        )
        assert result.processed == 5
        assert result.remaining == 3
        assert len(result.errors) == 2

    def test_frozen_immutability(self):
        """RecoveryResult is frozen — cannot mutate."""
        result = RecoveryResult(service_name="discord")
        with pytest.raises(AttributeError):
            result.processed = 10
