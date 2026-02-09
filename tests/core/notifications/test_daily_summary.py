"""Tests for daily summary notification job.

Story 4-7: Discord Publish Notifications (Task 5)

Tests the daily summary job including:
- Stats aggregation
- Top post inclusion
- Skip on no activity
- Error handling

Test Coverage:
- AC #4: Daily summary notification at end of day
"""

from datetime import date
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest


@dataclass
class MockDailyStats:
    """Mock daily publishing stats."""
    published: int
    pending: int
    failed: int


@pytest.fixture
def mock_discord_client() -> AsyncMock:
    """Create mock Discord client."""
    mock = AsyncMock()
    mock.send_daily_summary_notification = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_approval_repo() -> AsyncMock:
    """Create mock approval repository."""
    mock = AsyncMock()
    mock.get_daily_publishing_stats = AsyncMock(
        return_value=MockDailyStats(published=5, pending=2, failed=1)
    )
    mock.get_top_performing_post = AsyncMock(
        return_value={"title": "Top post", "engagement": 150}
    )
    return mock


class TestSendDailyPublishSummary:
    """Tests for daily summary job."""

    @pytest.mark.asyncio
    async def test_sends_summary_with_stats(
        self,
        mock_discord_client: AsyncMock,
        mock_approval_repo: AsyncMock,
    ) -> None:
        """Verify summary includes all stats (AC #4)."""
        from core.notifications.jobs import send_daily_publish_summary

        ctx = {
            "discord_client": mock_discord_client,
            "approval_repo": mock_approval_repo,
        }

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert "SENT" in result
        mock_discord_client.send_daily_summary_notification.assert_called_once()
        call_kwargs = mock_discord_client.send_daily_summary_notification.call_args.kwargs
        assert call_kwargs["published_count"] == 5
        assert call_kwargs["pending_count"] == 2
        assert call_kwargs["failed_count"] == 1

    @pytest.mark.asyncio
    async def test_includes_top_post(
        self,
        mock_discord_client: AsyncMock,
        mock_approval_repo: AsyncMock,
    ) -> None:
        """Verify top post is included when available (AC #4)."""
        from core.notifications.jobs import send_daily_publish_summary

        ctx = {
            "discord_client": mock_discord_client,
            "approval_repo": mock_approval_repo,
        }

        # Act
        await send_daily_publish_summary(ctx)

        # Assert
        call_kwargs = mock_discord_client.send_daily_summary_notification.call_args.kwargs
        assert call_kwargs["top_post"] is not None
        assert call_kwargs["top_post"]["title"] == "Top post"

    @pytest.mark.asyncio
    async def test_skips_on_no_activity(
        self,
        mock_discord_client: AsyncMock,
        mock_approval_repo: AsyncMock,
    ) -> None:
        """Verify no notification when no publishing activity (AC #4)."""
        from core.notifications.jobs import send_daily_publish_summary

        mock_approval_repo.get_daily_publishing_stats = AsyncMock(
            return_value=MockDailyStats(published=0, pending=0, failed=0)
        )

        ctx = {
            "discord_client": mock_discord_client,
            "approval_repo": mock_approval_repo,
        }

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert result == "NO_ACTIVITY"
        mock_discord_client.send_daily_summary_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_missing_discord_client(self) -> None:
        """Verify graceful handling when Discord client missing."""
        from core.notifications.jobs import send_daily_publish_summary

        ctx = {}

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert result == "DISCORD_MISSING"

    @pytest.mark.asyncio
    async def test_handles_missing_repo(
        self,
        mock_discord_client: AsyncMock,
    ) -> None:
        """Verify graceful handling when approval repo missing."""
        from core.notifications.jobs import send_daily_publish_summary

        ctx = {"discord_client": mock_discord_client}

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert result == "REPO_MISSING"

    @pytest.mark.asyncio
    async def test_handles_discord_failure(
        self,
        mock_discord_client: AsyncMock,
        mock_approval_repo: AsyncMock,
    ) -> None:
        """Verify handling when Discord send fails."""
        from core.notifications.jobs import send_daily_publish_summary

        mock_discord_client.send_daily_summary_notification = AsyncMock(
            return_value=False
        )

        ctx = {
            "discord_client": mock_discord_client,
            "approval_repo": mock_approval_repo,
        }

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert result == "SEND_FAILED"

    @pytest.mark.asyncio
    async def test_sends_without_top_post_when_unavailable(
        self,
        mock_discord_client: AsyncMock,
        mock_approval_repo: AsyncMock,
    ) -> None:
        """Verify summary sent even without top post data."""
        from core.notifications.jobs import send_daily_publish_summary

        mock_approval_repo.get_top_performing_post = AsyncMock(return_value=None)

        ctx = {
            "discord_client": mock_discord_client,
            "approval_repo": mock_approval_repo,
        }

        # Act
        result = await send_daily_publish_summary(ctx)

        # Assert
        assert "SENT" in result
        call_kwargs = mock_discord_client.send_daily_summary_notification.call_args.kwargs
        assert call_kwargs["top_post"] is None


class TestProcessBatchNotifications:
    """Tests for batch notification processing job."""

    @pytest.mark.asyncio
    async def test_no_batches_returns_no_work(self) -> None:
        """Verify returns NO_BATCHES when batch is empty."""
        from core.notifications.jobs import process_batch_notifications

        mock_batcher = AsyncMock()
        mock_batcher.get_batch_count = AsyncMock(return_value=0)

        ctx = {"publish_batcher": mock_batcher}

        # Act
        result = await process_batch_notifications(ctx)

        # Assert
        assert result == "NO_BATCHES"

    @pytest.mark.asyncio
    async def test_handles_missing_batcher(self) -> None:
        """Verify graceful handling when batcher missing."""
        from core.notifications.jobs import process_batch_notifications

        ctx = {}

        # Act
        result = await process_batch_notifications(ctx)

        # Assert
        assert result == "BATCHER_MISSING"
