"""Tests for Orshot usage tracking.

Tests the OrshotUsageTracker for monthly render limits per FR10.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.orshot import OrshotUsageTracker


@pytest.fixture
def mock_redis():
    """Mock Redis client for usage tracking tests."""
    client = AsyncMock()
    client.get.return_value = None
    client.incr.return_value = 1
    client.expire.return_value = True
    client.exists.return_value = 0
    client.set.return_value = True
    return client


@pytest.fixture
def mock_discord():
    """Mock Discord client for alert tests."""
    client = AsyncMock()
    client.send_webhook.return_value = True
    return client


@pytest.fixture
def usage_tracker(mock_redis):
    """Create usage tracker with mock Redis."""
    return OrshotUsageTracker(redis_client=mock_redis)


@pytest.fixture
def usage_tracker_with_discord(mock_redis, mock_discord):
    """Create usage tracker with mock Redis and Discord."""
    return OrshotUsageTracker(
        redis_client=mock_redis,
        discord_client=mock_discord,
    )


class TestUsageTrackerInit:
    """Tests for usage tracker initialization."""

    def test_init_with_defaults(self, mock_redis):
        """Should initialize with default limits."""
        tracker = OrshotUsageTracker(redis_client=mock_redis)

        assert tracker._monthly_limit == 3000
        assert tracker._warning_threshold == 0.80

    def test_init_with_custom_limits(self, mock_redis):
        """Should accept custom limits."""
        tracker = OrshotUsageTracker(
            redis_client=mock_redis,
            monthly_limit=1000,
            warning_threshold=0.90,
        )

        assert tracker._monthly_limit == 1000
        assert tracker._warning_threshold == 0.90

    def test_init_without_discord(self, mock_redis):
        """Should work without Discord client."""
        tracker = OrshotUsageTracker(redis_client=mock_redis)
        assert tracker._discord is None


class TestGetUsage:
    """Tests for getting current usage count."""

    @pytest.mark.asyncio
    async def test_get_usage_returns_zero_when_no_key(self, usage_tracker, mock_redis):
        """Should return 0 when no usage recorded."""
        mock_redis.get.return_value = None

        count = await usage_tracker.get_usage()

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_usage_returns_count(self, usage_tracker, mock_redis):
        """Should return current count from Redis."""
        mock_redis.get.return_value = b"42"

        count = await usage_tracker.get_usage()

        assert count == 42

    @pytest.mark.asyncio
    async def test_get_usage_handles_redis_error(self, usage_tracker, mock_redis):
        """Should return 0 on Redis error."""
        mock_redis.get.side_effect = Exception("Redis connection failed")

        count = await usage_tracker.get_usage()

        assert count == 0


class TestCanRender:
    """Tests for checking render permission."""

    @pytest.mark.asyncio
    async def test_can_render_under_limit(self, usage_tracker, mock_redis):
        """Should allow rendering under limit."""
        mock_redis.get.return_value = b"100"

        can_render = await usage_tracker.can_render()

        assert can_render is True

    @pytest.mark.asyncio
    async def test_can_render_at_limit(self, usage_tracker, mock_redis):
        """Should deny rendering at limit."""
        mock_redis.get.return_value = b"3000"

        can_render = await usage_tracker.can_render()

        assert can_render is False

    @pytest.mark.asyncio
    async def test_can_render_over_limit(self, usage_tracker, mock_redis):
        """Should deny rendering over limit."""
        mock_redis.get.return_value = b"3500"

        can_render = await usage_tracker.can_render()

        assert can_render is False


class TestIncrement:
    """Tests for incrementing usage count."""

    @pytest.mark.asyncio
    async def test_increment_first_usage(self, usage_tracker, mock_redis):
        """Should set expiry on first increment."""
        mock_redis.incr.return_value = 1

        count, is_warning, is_limit = await usage_tracker.increment()

        assert count == 1
        assert is_warning is False
        assert is_limit is False
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_not_first_usage(self, usage_tracker, mock_redis):
        """Should not set expiry after first increment."""
        mock_redis.incr.return_value = 100

        await usage_tracker.increment()

        mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_increment_returns_warning_at_threshold(self, mock_redis):
        """Should return warning at 80% threshold."""
        tracker = OrshotUsageTracker(redis_client=mock_redis)
        mock_redis.incr.return_value = 2400  # Exactly 80%

        count, is_warning, is_limit = await tracker.increment()

        assert count == 2400
        assert is_warning is True
        assert is_limit is False

    @pytest.mark.asyncio
    async def test_increment_returns_limit_at_max(self, mock_redis):
        """Should return limit reached at 100%."""
        tracker = OrshotUsageTracker(redis_client=mock_redis)
        mock_redis.incr.return_value = 3000

        count, is_warning, is_limit = await tracker.increment()

        assert count == 3000
        assert is_warning is True
        assert is_limit is True

    @pytest.mark.asyncio
    async def test_increment_handles_redis_error(self, usage_tracker, mock_redis):
        """Should return safe defaults on error."""
        mock_redis.incr.side_effect = Exception("Redis error")

        count, is_warning, is_limit = await usage_tracker.increment()

        assert count == 0
        assert is_warning is False
        assert is_limit is False


class TestWarningAlert:
    """Tests for Discord warning alerts."""

    @pytest.mark.asyncio
    async def test_sends_alert_at_warning_threshold(
        self, usage_tracker_with_discord, mock_redis, mock_discord
    ):
        """Should send Discord alert at 80% threshold."""
        mock_redis.incr.return_value = 2400
        mock_redis.exists.return_value = 0  # No alert sent yet

        await usage_tracker_with_discord.increment()

        mock_discord.send_webhook.assert_called_once()
        alert_msg = mock_discord.send_webhook.call_args[0][0]
        assert "Warning" in alert_msg
        assert "2,400" in alert_msg

    @pytest.mark.asyncio
    async def test_does_not_repeat_alert(
        self, usage_tracker_with_discord, mock_redis, mock_discord
    ):
        """Should not repeat alert if already sent."""
        mock_redis.incr.return_value = 2400
        mock_redis.exists.return_value = 1  # Alert already sent

        await usage_tracker_with_discord.increment()

        mock_discord.send_webhook.assert_not_called()

    @pytest.mark.asyncio
    async def test_sets_alert_sent_flag(
        self, usage_tracker_with_discord, mock_redis, mock_discord
    ):
        """Should mark alert as sent in Redis."""
        mock_redis.incr.return_value = 2400
        mock_redis.exists.return_value = 0

        await usage_tracker_with_discord.increment()

        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_handles_discord_error_gracefully(
        self, usage_tracker_with_discord, mock_redis, mock_discord
    ):
        """Should not fail on Discord error."""
        mock_redis.incr.return_value = 2400
        mock_redis.exists.return_value = 0
        mock_discord.send_webhook.side_effect = Exception("Discord error")

        # Should not raise
        count, is_warning, is_limit = await usage_tracker_with_discord.increment()

        assert count == 2400
        assert is_warning is True


class TestGetRemaining:
    """Tests for getting remaining renders."""

    @pytest.mark.asyncio
    async def test_get_remaining(self, usage_tracker, mock_redis):
        """Should return remaining render count."""
        mock_redis.get.return_value = b"1000"

        remaining = await usage_tracker.get_remaining()

        assert remaining == 2000

    @pytest.mark.asyncio
    async def test_get_remaining_at_limit(self, usage_tracker, mock_redis):
        """Should return 0 at limit."""
        mock_redis.get.return_value = b"3000"

        remaining = await usage_tracker.get_remaining()

        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_remaining_over_limit(self, usage_tracker, mock_redis):
        """Should return 0 when over limit."""
        mock_redis.get.return_value = b"3500"

        remaining = await usage_tracker.get_remaining()

        assert remaining == 0


class TestGetPercentage:
    """Tests for getting usage percentage."""

    @pytest.mark.asyncio
    async def test_get_percentage(self, usage_tracker, mock_redis):
        """Should return usage as percentage."""
        mock_redis.get.return_value = b"1500"

        percentage = await usage_tracker.get_percentage()

        assert percentage == 50.0

    @pytest.mark.asyncio
    async def test_get_percentage_at_warning(self, usage_tracker, mock_redis):
        """Should return correct percentage at warning."""
        mock_redis.get.return_value = b"2400"

        percentage = await usage_tracker.get_percentage()

        assert percentage == 80.0


class TestMonthlyKeyGeneration:
    """Tests for monthly key generation."""

    def test_monthly_key_format(self, usage_tracker):
        """Should generate key with year-month format."""
        key = usage_tracker._get_monthly_key()

        assert key.startswith("orshot:usage:")
        # Should have format like 2026-02
        parts = key.split(":")
        date_part = parts[-1]
        assert len(date_part) == 7  # YYYY-MM format
        assert "-" in date_part

    def test_alert_key_format(self, usage_tracker):
        """Should generate alert key with year-month format."""
        key = usage_tracker._get_alert_key()

        assert key.startswith("orshot:alert:")
