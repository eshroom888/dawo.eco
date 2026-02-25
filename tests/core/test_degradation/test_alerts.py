"""Tests for DegradationAlertService.

Story 7-10, Task 3.2: Degradation alert tests.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from core.config import DegradationConfig
from core.degradation.alerts import DegradationAlertService
from core.degradation.models import ServiceHealthStatus


@pytest.fixture
def config():
    """DegradationConfig with fast cooldown for tests."""
    return DegradationConfig(alert_cooldown_seconds=60)


@pytest.fixture
def registry_mock():
    """Mock ServiceHealthRegistry."""
    mock = AsyncMock()
    mock.get_status = AsyncMock()
    mock.get_all_statuses = AsyncMock(return_value=[])
    mock.get_queued_count = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def discord_mock():
    """Mock Discord client (DiscordClientProtocol)."""
    mock = AsyncMock()
    mock.send_webhook = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def redis_mock():
    """Mock Redis client for cooldown tracking."""
    mock = AsyncMock()
    mock.exists = AsyncMock(return_value=False)
    mock.setex = AsyncMock()
    return mock


@pytest.fixture
def alert_service(config, registry_mock, discord_mock, redis_mock):
    """DegradationAlertService with all mocks."""
    return DegradationAlertService(
        config=config,
        registry=registry_mock,
        discord=discord_mock,
        redis=redis_mock,
    )


class TestOnServiceDegraded:
    """Tests for on_service_degraded method."""

    @pytest.mark.asyncio
    async def test_sends_alert_when_degraded(self, alert_service, discord_mock, redis_mock):
        """on_service_degraded sends Discord alert for degraded service."""
        result = await alert_service.on_service_degraded(
            "instagram", "Connection timeout", consecutive_failures=3, queued_count=2
        )

        assert result is True
        discord_mock.send_webhook.assert_awaited_once()
        # Verify the message contains key info
        call_args = discord_mock.send_webhook.call_args[0][0]
        assert "instagram" in call_args.lower() or "INSTAGRAM" in call_args

    @pytest.mark.asyncio
    async def test_respects_cooldown(self, alert_service, discord_mock, redis_mock):
        """on_service_degraded skips alert when cooldown is active."""
        redis_mock.exists.return_value = True  # Cooldown active

        result = await alert_service.on_service_degraded(
            "instagram", "Timeout", consecutive_failures=5, queued_count=0
        )

        assert result is False
        discord_mock.send_webhook.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sets_cooldown_after_send(self, alert_service, redis_mock):
        """on_service_degraded sets cooldown in Redis after sending."""
        await alert_service.on_service_degraded(
            "shopify", "500 error", consecutive_failures=3, queued_count=0
        )

        redis_mock.setex.assert_awaited_once()
        args = redis_mock.setex.call_args
        assert "shopify" in args[0][0]
        assert args[0][1] == 60  # config.alert_cooldown_seconds

    @pytest.mark.asyncio
    async def test_color_orange_for_degraded(self, alert_service, discord_mock):
        """Alert message includes orange indicator for degraded status."""
        await alert_service.on_service_degraded(
            "shopify", "Timeout", consecutive_failures=3, queued_count=0
        )

        call_args = discord_mock.send_webhook.call_args[0][0]
        assert "Degraded" in call_args or "⚠️" in call_args

    @pytest.mark.asyncio
    async def test_color_red_for_unhealthy(self, alert_service, discord_mock):
        """Alert message includes red indicator for unhealthy (10+ failures)."""
        await alert_service.on_service_degraded(
            "instagram", "Connection refused", consecutive_failures=10, queued_count=5
        )

        call_args = discord_mock.send_webhook.call_args[0][0]
        assert "Unhealthy" in call_args or "🔴" in call_args

    @pytest.mark.asyncio
    async def test_includes_queued_count(self, alert_service, discord_mock):
        """Alert message includes queued operations count."""
        await alert_service.on_service_degraded(
            "instagram", "Timeout", consecutive_failures=5, queued_count=7
        )

        call_args = discord_mock.send_webhook.call_args[0][0]
        assert "7" in call_args


class TestOnServiceRecovered:
    """Tests for on_service_recovered method."""

    @pytest.mark.asyncio
    async def test_sends_recovery_alert(self, alert_service, discord_mock):
        """on_service_recovered sends green recovery alert."""
        result = await alert_service.on_service_recovered("instagram", queued_count=3)

        assert result is True
        discord_mock.send_webhook.assert_awaited_once()
        call_args = discord_mock.send_webhook.call_args[0][0]
        assert "Recovered" in call_args or "✅" in call_args

    @pytest.mark.asyncio
    async def test_recovery_ignores_cooldown(self, alert_service, discord_mock, redis_mock):
        """on_service_recovered always sends, even if cooldown is active."""
        redis_mock.exists.return_value = True  # Cooldown active

        result = await alert_service.on_service_recovered("shopify", queued_count=0)

        assert result is True
        discord_mock.send_webhook.assert_awaited_once()


class TestSendStatusSummary:
    """Tests for send_status_summary method."""

    @pytest.mark.asyncio
    async def test_sends_summary_with_all_services(
        self, alert_service, registry_mock, discord_mock
    ):
        """send_status_summary includes all monitored service statuses."""
        now = datetime.now(UTC)
        registry_mock.get_all_statuses.return_value = [
            ServiceHealthStatus(service_name="instagram", status="healthy", updated_at=now),
            ServiceHealthStatus(service_name="shopify", status="degraded", consecutive_failures=5, updated_at=now),
            ServiceHealthStatus(service_name="discord", status="healthy", updated_at=now),
            ServiceHealthStatus(service_name="google_calendar", status="unhealthy", consecutive_failures=12, updated_at=now),
        ]

        result = await alert_service.send_status_summary()

        assert result is True
        discord_mock.send_webhook.assert_awaited_once()
        call_args = discord_mock.send_webhook.call_args[0][0]
        assert "instagram" in call_args.lower() or "Instagram" in call_args
        assert "shopify" in call_args.lower() or "Shopify" in call_args


class TestDiscordFailureResilience:
    """Tests that Discord failures don't raise."""

    @pytest.mark.asyncio
    async def test_degraded_alert_discord_failure(self, alert_service, discord_mock):
        """Discord failure in on_service_degraded returns False, doesn't raise."""
        discord_mock.send_webhook.side_effect = Exception("Discord down")

        result = await alert_service.on_service_degraded(
            "instagram", "Timeout", consecutive_failures=3, queued_count=0
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_recovery_alert_discord_failure(self, alert_service, discord_mock):
        """Discord failure in on_service_recovered returns False, doesn't raise."""
        discord_mock.send_webhook.side_effect = Exception("Discord down")

        result = await alert_service.on_service_recovered("shopify", queued_count=0)

        assert result is False


class TestSelfAlertLoop:
    """Tests for Discord-about-Discord detection."""

    @pytest.mark.asyncio
    async def test_no_discord_alert_about_discord(self, alert_service, discord_mock):
        """on_service_degraded with service_name='discord' logs but doesn't send."""
        result = await alert_service.on_service_degraded(
            "discord", "Webhook failed", consecutive_failures=5, queued_count=0
        )

        assert result is False
        discord_mock.send_webhook.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_discord_recovery_also_skipped(self, alert_service, discord_mock):
        """on_service_recovered for 'discord' also skips sending."""
        result = await alert_service.on_service_recovered("discord", queued_count=0)

        assert result is False
        discord_mock.send_webhook.assert_not_awaited()
