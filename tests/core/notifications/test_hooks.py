"""Tests for notification hooks.

Tests the event hooks that trigger notifications including:
- Item creation hook
- Compliance warning prioritization
- Non-blocking execution
- Logging of trigger events
- Publish success/failure hooks (Story 4-7)

Test Coverage:
- AC #1: Threshold triggering on item creation
- AC #3: Compliance warning prioritization
- AC #4: Non-blocking failure handling
- Story 4-7 AC #1: Publish success notifications
- Story 4-7 AC #3: Publish failure notifications
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.notifications.hooks import (
    on_approval_item_created,
    on_publish_success,
    on_publish_failed,
)


@pytest.fixture
def mock_notifier() -> AsyncMock:
    """Create mock notification service."""
    mock = AsyncMock()
    mock.check_and_notify = AsyncMock(return_value=True)
    return mock


def create_mock_approval_item(
    compliance_status: str = "COMPLIANT",
) -> MagicMock:
    """Create a mock approval item for testing."""
    item = MagicMock()
    item.id = uuid4()
    item.source_type = "instagram_post"
    item.source_priority = 3
    item.compliance_status = compliance_status
    return item


class TestOnApprovalItemCreated:
    """Tests for on_approval_item_created hook."""

    @pytest.mark.asyncio
    async def test_triggers_notification_check(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Verify hook triggers notification check."""
        # Arrange
        item = create_mock_approval_item()

        # Act
        await on_approval_item_created(item, mock_notifier)

        # Assert
        mock_notifier.check_and_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_compliance_warning_logged(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Verify compliance warnings are logged (AC #3)."""
        # Arrange
        item = create_mock_approval_item(compliance_status="WARNING")

        # Act - should log compliance warning
        with patch("core.notifications.hooks.logger") as mock_logger:
            await on_approval_item_created(item, mock_notifier)

            # Assert: Info log for compliance warning
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_non_blocking_on_exception(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Verify hook doesn't block on notifier exception (AC #4)."""
        # Arrange: Notifier raises exception
        mock_notifier.check_and_notify = AsyncMock(
            side_effect=Exception("Notification failed")
        )
        item = create_mock_approval_item()

        # Act - should not raise
        await on_approval_item_created(item, mock_notifier)

        # Assert: No exception propagated

    @pytest.mark.asyncio
    async def test_error_logged_on_failure(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Verify errors are logged on failure."""
        # Arrange
        mock_notifier.check_and_notify = AsyncMock(
            side_effect=Exception("Notification failed")
        )
        item = create_mock_approval_item()

        # Act
        with patch("core.notifications.hooks.logger") as mock_logger:
            await on_approval_item_created(item, mock_notifier)

            # Assert: Error logged
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_compliant_item_no_special_logging(
        self,
        mock_notifier: AsyncMock,
    ) -> None:
        """Verify compliant items don't trigger compliance warning log."""
        # Arrange
        item = create_mock_approval_item(compliance_status="COMPLIANT")

        # Act
        with patch("core.notifications.hooks.logger") as mock_logger:
            await on_approval_item_created(item, mock_notifier)

            # Assert: No info log about compliance warning
            for call in mock_logger.info.call_args_list:
                if "compliance warning" in str(call).lower():
                    pytest.fail("Should not log compliance warning for COMPLIANT item")


def create_mock_approval_item_for_publish(
    caption: str = "Test caption for post",
    scheduled_time: datetime = None,
) -> MagicMock:
    """Create a mock approval item for publish testing."""
    item = MagicMock()
    item.id = uuid4()
    item.full_caption = caption
    item.scheduled_publish_time = scheduled_time or datetime.now(UTC)
    return item


@pytest.fixture
def mock_publish_notifier() -> AsyncMock:
    """Create mock publish notification service."""
    mock = AsyncMock()
    mock.notify_publish_success = AsyncMock(return_value=True)
    mock.notify_publish_failed = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_event_emitter() -> AsyncMock:
    """Create mock event emitter."""
    mock = AsyncMock()
    mock.emit = AsyncMock()
    return mock


class TestOnPublishSuccess:
    """Tests for on_publish_success hook (Story 4-7)."""

    @pytest.mark.asyncio
    async def test_triggers_notification(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook triggers publish success notification (AC #1)."""
        # Arrange
        item = create_mock_approval_item_for_publish()

        # Act
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert
        mock_publish_notifier.notify_publish_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_emits_websocket_event(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook emits WebSocket event for UI update."""
        # Arrange
        item = create_mock_approval_item_for_publish()

        # Act
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert
        mock_event_emitter.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_blocking_on_exception(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook doesn't block on notifier exception."""
        # Arrange
        mock_publish_notifier.notify_publish_success = AsyncMock(
            side_effect=Exception("Notification failed")
        )
        item = create_mock_approval_item_for_publish()

        # Act - should not raise
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert: No exception propagated

    @pytest.mark.asyncio
    async def test_truncates_long_caption(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify long captions are truncated for title."""
        # Arrange
        long_caption = "A" * 100
        item = create_mock_approval_item_for_publish(caption=long_caption)

        # Act
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert: Title should be truncated
        call_args = mock_publish_notifier.notify_publish_success.call_args
        post_info = call_args[0][0]  # First positional argument
        assert len(post_info.title) <= 53  # 50 + "..."


class TestOnPublishFailed:
    """Tests for on_publish_failed hook (Story 4-7)."""

    @pytest.mark.asyncio
    async def test_triggers_failure_notification(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook triggers publish failure notification (AC #3)."""
        # Arrange
        item = create_mock_approval_item_for_publish()

        # Act
        await on_publish_failed(
            item=item,
            error_reason="API connection failed",
            error_type="API_ERROR",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert
        mock_publish_notifier.notify_publish_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_emits_failure_event(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook emits WebSocket failure event."""
        # Arrange
        item = create_mock_approval_item_for_publish()

        # Act
        await on_publish_failed(
            item=item,
            error_reason="Rate limit exceeded",
            error_type="RATE_LIMIT",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert
        mock_event_emitter.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_blocking_on_exception(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook doesn't block on notifier exception."""
        # Arrange
        mock_publish_notifier.notify_publish_failed = AsyncMock(
            side_effect=Exception("Notification failed")
        )
        item = create_mock_approval_item_for_publish()

        # Act - should not raise
        await on_publish_failed(
            item=item,
            error_reason="API error",
            error_type="API_ERROR",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert: No exception propagated

    @pytest.mark.asyncio
    async def test_includes_error_details(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify failure info includes error details."""
        # Arrange
        item = create_mock_approval_item_for_publish()

        # Act
        await on_publish_failed(
            item=item,
            error_reason="Instagram API rate limit hit",
            error_type="RATE_LIMIT",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert
        call_args = mock_publish_notifier.notify_publish_failed.call_args
        failure_info = call_args[0][0]  # First positional argument
        assert failure_info.error_type == "RATE_LIMIT"
        assert "rate limit" in failure_info.error_reason.lower()


class TestEdgeCases:
    """Edge case tests for notification hooks (Code Review Fix)."""

    @pytest.mark.asyncio
    async def test_publish_success_with_none_caption(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook handles None caption gracefully (LOW #6)."""
        # Arrange: Item with None caption
        item = MagicMock()
        item.id = uuid4()
        item.full_caption = None
        item.scheduled_publish_time = datetime.now(UTC)

        # Act - should not raise
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert: Notification triggered with empty title
        mock_publish_notifier.notify_publish_success.assert_called_once()
        call_args = mock_publish_notifier.notify_publish_success.call_args
        post_info = call_args[0][0]
        assert post_info.title == ""
        assert post_info.caption_excerpt == ""

    @pytest.mark.asyncio
    async def test_publish_failed_with_none_caption(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify failure hook handles None caption gracefully (LOW #6)."""
        # Arrange: Item with None caption
        item = MagicMock()
        item.id = uuid4()
        item.full_caption = None
        item.scheduled_publish_time = datetime.now(UTC)

        # Act - should not raise
        await on_publish_failed(
            item=item,
            error_reason="API error",
            error_type="API_ERROR",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert: Notification triggered with empty title
        mock_publish_notifier.notify_publish_failed.assert_called_once()
        call_args = mock_publish_notifier.notify_publish_failed.call_args
        failure_info = call_args[0][0]
        assert failure_info.title == ""

    @pytest.mark.asyncio
    async def test_publish_success_with_empty_string_caption(
        self,
        mock_publish_notifier: AsyncMock,
        mock_event_emitter: AsyncMock,
    ) -> None:
        """Verify hook handles empty string caption gracefully."""
        # Arrange: Item with empty caption
        item = MagicMock()
        item.id = uuid4()
        item.full_caption = ""
        item.scheduled_publish_time = datetime.now(UTC)

        # Act
        await on_publish_success(
            item=item,
            instagram_post_id="123456789",
            instagram_url="https://instagram.com/p/abc123",
            notifier=mock_publish_notifier,
            event_emitter=mock_event_emitter,
        )

        # Assert
        mock_publish_notifier.notify_publish_success.assert_called_once()
