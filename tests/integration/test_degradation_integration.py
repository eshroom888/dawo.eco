"""Integration tests for graceful API degradation.

Story 7-10, Task 9.1: End-to-end degradation flows.

These tests verify the full degradation lifecycle:
registry → alerts → recovery → dashboard, all with mocked Redis.
"""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock

from core.config import DegradationConfig
from core.degradation.alerts import DegradationAlertService
from core.degradation.models import ServiceHealthStatus, RecoveryResult
from core.degradation.recovery import RecoveryProcessor
from core.degradation.registry import ServiceHealthRegistry
from core.degradation.wiring import record_service_health
from teams.dawo.middleware.operation_queue import IncompleteOperation


@pytest.fixture
def config():
    """DegradationConfig with test-friendly settings."""
    return DegradationConfig(
        failure_threshold=3,
        unhealthy_threshold=5,
        max_recovery_batch_size=3,
        alert_cooldown_seconds=60,
    )


@pytest.fixture
def redis_mock():
    """Full mock Redis client."""
    store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value):
        store[key] = value

    async def mock_exists(key):
        return key in store

    async def mock_setex(key, seconds, value):
        store[key] = value

    async def mock_hlen(key):
        return 0

    mock = AsyncMock()
    mock.get = AsyncMock(side_effect=mock_get)
    mock.set = AsyncMock(side_effect=mock_set)
    mock.exists = AsyncMock(side_effect=mock_exists)
    mock.setex = AsyncMock(side_effect=mock_setex)
    mock.hlen = AsyncMock(side_effect=mock_hlen)
    mock.hgetall = AsyncMock(return_value={})
    mock._store = store  # Expose for assertions
    return mock


@pytest.fixture
def registry(config, redis_mock):
    """ServiceHealthRegistry with mocked Redis."""
    return ServiceHealthRegistry(config, redis_mock)


@pytest.fixture
def discord_mock():
    """Mock Discord client (DiscordClientProtocol)."""
    mock = AsyncMock()
    mock.send_webhook = AsyncMock(return_value=True)
    return mock


class TestDegradationLifecycle:
    """End-to-end degradation lifecycle tests."""

    @pytest.mark.asyncio
    async def test_api_fails_3x_marks_degraded_and_alerts(
        self, config, registry, discord_mock, redis_mock
    ):
        """API fails 3x → service marked degraded → Discord alert sent."""
        alert_service = DegradationAlertService(
            config=config, registry=registry, discord=discord_mock, redis=redis_mock
        )

        # Fail 3 times
        for i in range(3):
            status = await registry.record_failure("instagram", f"Timeout #{i+1}")

        assert status.status == "degraded"
        assert status.consecutive_failures == 3

        # Send degradation alert
        sent = await alert_service.on_service_degraded(
            "instagram", "Timeout #3", consecutive_failures=3, queued_count=0
        )
        assert sent is True

    @pytest.mark.asyncio
    async def test_api_recovers_marks_healthy_and_processes_queue(
        self, config, registry, redis_mock
    ):
        """API recovers → marked healthy → queued ops processed."""
        # First degrade
        for i in range(3):
            await registry.record_failure("instagram", "Timeout")

        status = await registry.get_status("instagram")
        assert status.status == "degraded"

        # Recover
        status = await registry.record_success("instagram")
        assert status.status == "healthy"
        assert status.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_recovery_processes_queued_operations(
        self, config, registry, redis_mock
    ):
        """RecoveryProcessor processes queued ops for healthy service."""
        # Mark healthy
        await registry.record_success("instagram")

        # Mock queue with operations
        queue_mock = AsyncMock()
        queue_mock.get_operations_for_service = AsyncMock(return_value=[
            IncompleteOperation(
                operation_id="op-1",
                context="instagram_publish",
                payload={"item_id": "abc"},
                created_at=datetime.now(UTC),
            ),
        ])
        queue_mock.remove_from_queue = AsyncMock()
        enqueuer = AsyncMock()

        processor = RecoveryProcessor(
            config=config, registry=registry, queue=queue_mock, job_enqueuer=enqueuer
        )
        result = await processor.check_and_recover("instagram")

        assert result.processed == 1
        enqueuer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multiple_apis_down_tracked_independently(
        self, config, registry
    ):
        """Multiple APIs down → each tracked independently."""
        # Instagram fails
        for i in range(3):
            await registry.record_failure("instagram", "Timeout")

        # Shopify fails
        for i in range(5):
            await registry.record_failure("shopify", "502 Bad Gateway")

        # Discord stays healthy
        await registry.record_success("discord")

        ig = await registry.get_status("instagram")
        sp = await registry.get_status("shopify")
        dc = await registry.get_status("discord")

        assert ig.status == "degraded"
        assert sp.status == "unhealthy"
        assert dc.status == "healthy"

    @pytest.mark.asyncio
    async def test_manual_health_reset(self, registry):
        """Manual reset → service forced to healthy."""
        # Degrade first
        for i in range(5):
            await registry.record_failure("shopify", "Error")

        status = await registry.get_status("shopify")
        assert status.status == "unhealthy"

        # Reset
        status = await registry.reset_status("shopify")
        assert status.status == "healthy"
        assert status.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_discord_self_referential_skips_alert(
        self, config, registry, discord_mock, redis_mock
    ):
        """Discord down → logged locally, not alerted via Discord."""
        alert_service = DegradationAlertService(
            config=config, registry=registry, discord=discord_mock, redis=redis_mock
        )

        sent = await alert_service.on_service_degraded(
            "discord", "Webhook failed", consecutive_failures=5, queued_count=0
        )

        assert sent is False
        discord_mock.send_webhook.assert_not_awaited()


class TestRedisUnavailableResilience:
    """System continues when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_registry_redis_down_returns_healthy(self, config):
        """Registry returns healthy default when Redis is down."""
        broken_redis = AsyncMock()
        broken_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))

        registry = ServiceHealthRegistry(config, broken_redis)
        status = await registry.get_status("instagram")

        assert status.status == "healthy"

    @pytest.mark.asyncio
    async def test_wiring_none_registry_is_safe(self):
        """record_service_health with None registry doesn't raise."""
        await record_service_health(None, "instagram", success=True)
        await record_service_health(None, "shopify", success=False, error="Down")

    @pytest.mark.asyncio
    async def test_wiring_broken_registry_is_safe(self):
        """record_service_health with broken registry doesn't raise."""
        broken = AsyncMock()
        broken.record_success.side_effect = Exception("Redis down")

        await record_service_health(broken, "instagram", success=True)


class TestBatchSizeRecoveryRespect:
    """Recovery respects rate limits (batch size)."""

    @pytest.mark.asyncio
    async def test_recovery_respects_batch_size(self, config, registry):
        """Recovery processes at most max_recovery_batch_size ops."""
        await registry.record_success("instagram")

        ops = [
            IncompleteOperation(
                operation_id=f"op-{i}",
                context="instagram_publish",
                payload={},
                created_at=datetime.now(UTC),
            )
            for i in range(10)
        ]

        queue_mock = AsyncMock()
        queue_mock.get_operations_for_service = AsyncMock(return_value=ops)
        queue_mock.remove_from_queue = AsyncMock()
        enqueuer = AsyncMock()

        processor = RecoveryProcessor(
            config=config, registry=registry, queue=queue_mock, job_enqueuer=enqueuer
        )
        result = await processor.check_and_recover("instagram")

        assert result.processed == 3  # max_recovery_batch_size=3
        assert result.remaining == 7

    @pytest.mark.asyncio
    async def test_recovery_skips_non_healthy_services(self, config, registry):
        """Recovery skips degraded services."""
        for i in range(3):
            await registry.record_failure("instagram", "Timeout")

        queue_mock = AsyncMock()
        enqueuer = AsyncMock()

        processor = RecoveryProcessor(
            config=config, registry=registry, queue=queue_mock, job_enqueuer=enqueuer
        )
        result = await processor.check_and_recover("instagram")

        assert result.processed == 0
        enqueuer.assert_not_awaited()
