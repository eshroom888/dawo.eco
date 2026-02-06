"""Tests for Discord error alerting functionality (AC #2).

Tests verify:
- DiscordAlertManager sends alerts on API errors
- Rate-limiting prevents alert spam (max 1 per API per 5 minutes)
- Discord failures don't propagate (graceful degradation)
- Alert messages contain actionable information
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from teams.dawo.middleware import DiscordAlertManager


class TestDiscordAlertManagerInit:
    """Test DiscordAlertManager initialization."""

    def test_accepts_discord_client_via_injection(self) -> None:
        """Should accept Discord client via constructor injection."""
        mock_discord = MagicMock()
        mock_redis = MagicMock()
        manager = DiscordAlertManager(mock_discord, mock_redis)
        assert manager is not None

    def test_alert_cooldown_is_5_minutes(self) -> None:
        """Alert cooldown should be 5 minutes (300 seconds)."""
        mock_discord = MagicMock()
        mock_redis = MagicMock()
        manager = DiscordAlertManager(mock_discord, mock_redis)
        assert manager.ALERT_COOLDOWN == 300


class TestSendApiErrorAlert:
    """Test send_api_error_alert method."""

    @pytest.mark.asyncio
    async def test_sends_alert_when_not_rate_limited(self) -> None:
        """Should send Discord alert when not rate-limited."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False  # Not rate-limited

        manager = DiscordAlertManager(mock_discord, mock_redis)
        result = await manager.send_api_error_alert(
            api_name="instagram",
            error="Connection timeout",
            attempts=3,
            queued_for_retry=True,
        )

        assert result is True
        mock_discord.send_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_send_when_rate_limited(self) -> None:
        """Should NOT send alert when rate-limited."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = True  # Rate-limited

        manager = DiscordAlertManager(mock_discord, mock_redis)
        result = await manager.send_api_error_alert(
            api_name="instagram",
            error="Connection timeout",
            attempts=3,
            queued_for_retry=True,
        )

        assert result is False
        mock_discord.send_webhook.assert_not_called()

    @pytest.mark.asyncio
    async def test_sets_cooldown_after_sending(self) -> None:
        """Should set rate-limit cooldown after sending alert."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        await manager.send_api_error_alert(
            api_name="discord",
            error="Server error",
            attempts=2,
            queued_for_retry=True,
        )

        # Verify cooldown was set
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "dawo:alert_cooldown:discord" in str(call_args)
        assert 300 in call_args[0]  # 5 minute cooldown

    @pytest.mark.asyncio
    async def test_checks_per_api_rate_limit(self) -> None:
        """Rate limiting should be per-API."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        await manager.send_api_error_alert(
            api_name="orshot",
            error="Timeout",
            attempts=3,
            queued_for_retry=False,
        )

        # Verify correct cache key was checked
        mock_redis.exists.assert_called_with("dawo:alert_cooldown:orshot")


class TestAlertMessage:
    """Test alert message formatting."""

    @pytest.mark.asyncio
    async def test_message_contains_api_name(self) -> None:
        """Alert message should contain the API name."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        await manager.send_api_error_alert(
            api_name="shopify",
            error="Connection refused",
            attempts=3,
            queued_for_retry=True,
        )

        call_args = mock_discord.send_webhook.call_args
        message = call_args[0][0]
        assert "shopify" in message.lower()

    @pytest.mark.asyncio
    async def test_message_contains_error_info(self) -> None:
        """Alert message should contain error details."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        await manager.send_api_error_alert(
            api_name="instagram",
            error="HTTP 503 Service Unavailable",
            attempts=3,
            queued_for_retry=True,
        )

        call_args = mock_discord.send_webhook.call_args
        message = call_args[0][0]
        assert "503" in message or "Service Unavailable" in message

    @pytest.mark.asyncio
    async def test_message_contains_attempt_count(self) -> None:
        """Alert message should contain number of attempts."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        await manager.send_api_error_alert(
            api_name="discord",
            error="Timeout",
            attempts=3,
            queued_for_retry=True,
        )

        call_args = mock_discord.send_webhook.call_args
        message = call_args[0][0]
        assert "3" in message

    @pytest.mark.asyncio
    async def test_message_shows_queued_status(self) -> None:
        """Alert message should indicate if operation was queued."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        await manager.send_api_error_alert(
            api_name="orshot",
            error="Error",
            attempts=3,
            queued_for_retry=True,
        )

        call_args = mock_discord.send_webhook.call_args
        message = call_args[0][0]
        assert "queued" in message.lower() or "retry" in message.lower()


class TestGracefulDegradation:
    """Test that Discord failures don't propagate."""

    @pytest.mark.asyncio
    async def test_discord_failure_returns_false(self) -> None:
        """Discord failure should return False, not raise."""
        mock_discord = AsyncMock()
        mock_discord.send_webhook.side_effect = Exception("Discord is down")
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = False

        manager = DiscordAlertManager(mock_discord, mock_redis)
        result = await manager.send_api_error_alert(
            api_name="instagram",
            error="Error",
            attempts=3,
            queued_for_retry=True,
        )

        # Should return False, not raise exception
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_failure_returns_false(self) -> None:
        """Redis failure should return False, not raise."""
        mock_discord = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.exists.side_effect = Exception("Redis connection lost")

        manager = DiscordAlertManager(mock_discord, mock_redis)
        result = await manager.send_api_error_alert(
            api_name="shopify",
            error="Error",
            attempts=2,
            queued_for_retry=True,
        )

        # Should return False, not raise exception
        assert result is False


class TestModuleExports:
    """Test module exports."""

    def test_discord_alert_manager_exported(self) -> None:
        """DiscordAlertManager should be importable from middleware."""
        from teams.dawo.middleware import DiscordAlertManager
        assert DiscordAlertManager is not None
