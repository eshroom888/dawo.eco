"""Tests for ServiceHealthRegistry.

Story 7-10, Task 1.6: Redis-backed health tracking tests.
"""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from core.config import DegradationConfig
from core.degradation.models import ServiceHealthStatus
from core.degradation.registry import ServiceHealthRegistry


@pytest.fixture
def config():
    """Default degradation config."""
    return DegradationConfig()


@pytest.fixture
def redis_mock():
    """Mock Redis client with async methods."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.hgetall = AsyncMock(return_value={})
    mock.hlen = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def registry(config, redis_mock):
    """ServiceHealthRegistry with mocked Redis."""
    return ServiceHealthRegistry(config, redis_mock)


class TestRecordSuccess:
    """Tests for record_success method."""

    @pytest.mark.asyncio
    async def test_resets_consecutive_failures(self, registry, redis_mock):
        """record_success resets consecutive_failures to 0."""
        # Simulate existing degraded status
        existing = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=5,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_success("instagram")

        assert result.consecutive_failures == 0
        assert result.status == "healthy"
        assert result.last_success is not None

    @pytest.mark.asyncio
    async def test_transitions_from_degraded_to_healthy(self, registry, redis_mock):
        """record_success transitions from degraded to healthy."""
        existing = ServiceHealthStatus(
            service_name="shopify",
            status="degraded",
            consecutive_failures=5,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_success("shopify")

        assert result.status == "healthy"
        assert result.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_transitions_from_unhealthy_to_healthy(self, registry, redis_mock):
        """record_success transitions from unhealthy to healthy."""
        existing = ServiceHealthStatus(
            service_name="instagram",
            status="unhealthy",
            consecutive_failures=15,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_success("instagram")

        assert result.status == "healthy"
        assert result.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_healthy_stays_healthy(self, registry, redis_mock):
        """record_success on already healthy service stays healthy."""
        redis_mock.get.return_value = None  # No existing state = healthy

        result = await registry.record_success("discord")

        assert result.status == "healthy"
        assert result.consecutive_failures == 0


class TestRecordFailure:
    """Tests for record_failure method."""

    @pytest.mark.asyncio
    async def test_increments_consecutive_failures(self, registry, redis_mock):
        """record_failure increments consecutive_failures."""
        redis_mock.get.return_value = None  # Fresh service

        result = await registry.record_failure("instagram", "Connection refused")

        assert result.consecutive_failures == 1
        assert result.last_error == "Connection refused"
        assert result.last_failure is not None

    @pytest.mark.asyncio
    async def test_transitions_healthy_to_degraded_at_threshold(
        self, registry, redis_mock
    ):
        """record_failure transitions healthy → degraded at failure_threshold (3)."""
        existing = ServiceHealthStatus(
            service_name="instagram",
            status="healthy",
            consecutive_failures=2,  # One more → degraded
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_failure("instagram", "Timeout")

        assert result.consecutive_failures == 3
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_transitions_degraded_to_unhealthy_at_threshold(
        self, registry, redis_mock
    ):
        """record_failure transitions degraded → unhealthy at unhealthy_threshold (10)."""
        existing = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=9,  # One more → unhealthy
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_failure("instagram", "Server error")

        assert result.consecutive_failures == 10
        assert result.status == "unhealthy"

    @pytest.mark.asyncio
    async def test_stays_below_threshold(self, registry, redis_mock):
        """record_failure stays healthy when below failure_threshold."""
        existing = ServiceHealthStatus(
            service_name="shopify",
            status="healthy",
            consecutive_failures=1,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_failure("shopify", "Timeout")

        assert result.consecutive_failures == 2
        assert result.status == "healthy"


class TestGetStatus:
    """Tests for get_status method."""

    @pytest.mark.asyncio
    async def test_returns_healthy_default_when_no_data(self, registry, redis_mock):
        """get_status returns healthy default when Redis has no data."""
        redis_mock.get.return_value = None

        result = await registry.get_status("instagram")

        assert result.service_name == "instagram"
        assert result.status == "healthy"
        assert result.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_returns_stored_status(self, registry, redis_mock):
        """get_status returns stored status from Redis."""
        stored = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=5,
            last_error="Timeout",
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(stored))

        result = await registry.get_status("instagram")

        assert result.status == "degraded"
        assert result.consecutive_failures == 5


class TestGetAllStatuses:
    """Tests for get_all_statuses method."""

    @pytest.mark.asyncio
    async def test_returns_all_monitored_services(self, registry, redis_mock):
        """get_all_statuses returns status for all monitored services."""
        redis_mock.get.return_value = None  # All fresh/healthy

        result = await registry.get_all_statuses()

        assert len(result) == 4  # instagram, shopify, discord, google_calendar
        names = {s.service_name for s in result}
        assert names == {"instagram", "shopify", "discord", "google_calendar"}


class TestGetQueuedCount:
    """Tests for get_queued_count method."""

    @pytest.mark.asyncio
    async def test_returns_queued_count(self, registry, redis_mock):
        """get_queued_count returns pending operation count from Redis."""
        redis_mock.hlen.return_value = 3

        count = await registry.get_queued_count("instagram")

        assert count == 3


class TestRedisFailureResilience:
    """Tests that Redis failures don't raise."""

    @pytest.mark.asyncio
    async def test_record_success_redis_failure_returns_healthy(
        self, registry, redis_mock
    ):
        """Redis failure in record_success returns healthy default."""
        redis_mock.get.side_effect = ConnectionError("Redis down")

        result = await registry.record_success("instagram")

        assert result.status == "healthy"
        assert result.service_name == "instagram"

    @pytest.mark.asyncio
    async def test_get_status_redis_failure_returns_healthy(
        self, registry, redis_mock
    ):
        """Redis failure in get_status returns healthy default."""
        redis_mock.get.side_effect = ConnectionError("Redis down")

        result = await registry.get_status("discord")

        assert result.status == "healthy"
        assert result.service_name == "discord"

    @pytest.mark.asyncio
    async def test_record_failure_redis_failure_returns_default(
        self, registry, redis_mock
    ):
        """Redis failure in record_failure returns sensible default."""
        redis_mock.get.side_effect = ConnectionError("Redis down")

        result = await registry.record_failure("shopify", "API error")

        assert result.service_name == "shopify"


class TestRecoveryCallback:
    """Tests for on_recovery callback (AC5: recovery notification)."""

    @pytest.mark.asyncio
    async def test_callback_fires_on_degraded_to_healthy(self, config, redis_mock):
        """on_recovery fires when service transitions from degraded to healthy."""
        callback = AsyncMock()
        registry = ServiceHealthRegistry(config, redis_mock, on_recovery=callback)

        existing = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=5,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        await registry.record_success("instagram")

        callback.assert_awaited_once_with("instagram", 0)

    @pytest.mark.asyncio
    async def test_callback_fires_on_unhealthy_to_healthy(self, config, redis_mock):
        """on_recovery fires when service transitions from unhealthy to healthy."""
        callback = AsyncMock()
        registry = ServiceHealthRegistry(config, redis_mock, on_recovery=callback)

        existing = ServiceHealthStatus(
            service_name="shopify",
            status="unhealthy",
            consecutive_failures=15,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        await registry.record_success("shopify")

        callback.assert_awaited_once_with("shopify", 0)

    @pytest.mark.asyncio
    async def test_callback_not_fired_when_already_healthy(self, config, redis_mock):
        """on_recovery does NOT fire when service was already healthy."""
        callback = AsyncMock()
        registry = ServiceHealthRegistry(config, redis_mock, on_recovery=callback)

        redis_mock.get.return_value = None  # No existing state = healthy

        await registry.record_success("discord")

        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_callback_not_fired_when_no_callback_set(self, registry, redis_mock):
        """No crash when on_recovery is None (backward compat)."""
        existing = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=5,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_success("instagram")

        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_callback_failure_doesnt_block(self, config, redis_mock):
        """on_recovery callback failure doesn't prevent record_success."""
        callback = AsyncMock(side_effect=Exception("Alert service down"))
        registry = ServiceHealthRegistry(config, redis_mock, on_recovery=callback)

        existing = ServiceHealthStatus(
            service_name="instagram",
            status="degraded",
            consecutive_failures=5,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        result = await registry.record_success("instagram")

        assert result.status == "healthy"
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_callback_receives_queued_count(self, config, redis_mock):
        """on_recovery callback receives the queued operation count."""
        callback = AsyncMock()
        registry = ServiceHealthRegistry(config, redis_mock, on_recovery=callback)
        redis_mock.hlen.return_value = 7

        existing = ServiceHealthStatus(
            service_name="instagram",
            status="unhealthy",
            consecutive_failures=12,
            updated_at=datetime.now(UTC),
        )
        redis_mock.get.return_value = json.dumps(_status_to_dict(existing))

        await registry.record_success("instagram")

        callback.assert_awaited_once_with("instagram", 7)


# === Helper ===

def _status_to_dict(status: ServiceHealthStatus) -> dict:
    """Convert ServiceHealthStatus to JSON-serializable dict."""
    return {
        "service_name": status.service_name,
        "status": status.status,
        "consecutive_failures": status.consecutive_failures,
        "last_success": status.last_success.isoformat() if status.last_success else None,
        "last_failure": status.last_failure.isoformat() if status.last_failure else None,
        "last_error": status.last_error,
        "queued_operations": status.queued_operations,
        "updated_at": status.updated_at.isoformat() if status.updated_at else None,
    }
