"""Publishing Service - Orchestrates publishing with notifications.

Story 4-7: Discord Publish Notifications (Task 4.3)

This module provides a high-level PublishingService that wraps
InstagramPublisher and integrates notification hooks for publish
success/failure events.

Architecture Compliance:
- Orchestrates InstagramPublisher and notification hooks
- Protocol-based dependency injection
- Non-blocking notification execution
- Never fails publishing due to notification errors

Usage:
    from core.publishing import PublishingService
    from core.notifications import (
        PublishNotificationService,
        on_publish_success,
        on_publish_failed,
    )

    service = PublishingService(
        publisher=instagram_publisher,
        notifier=publish_notifier,
        event_emitter=notification_events,
    )

    result = await service.publish_approval_item(item, image_url)
"""

import logging
from datetime import datetime, UTC
from typing import Optional, Protocol, TYPE_CHECKING

from core.publishing.instagram_publisher import (
    InstagramPublisher,
    InstagramPublisherProtocol,
    PublishResult,
)
from core.notifications.error_mapping import get_error_type

if TYPE_CHECKING:
    from core.approval.models import ApprovalItem
    from core.notifications.publish_notifier import PublishNotifierProtocol
    from core.notifications.events import NotificationEventEmitter

logger = logging.getLogger(__name__)


class PublishingServiceProtocol(Protocol):
    """Protocol for publishing service.

    Story 4-7, Task 4.3: Integration protocol.
    """

    async def publish_approval_item(
        self,
        item: "ApprovalItem",
        image_url: str,
        hashtags: Optional[list[str]] = None,
    ) -> PublishResult:
        """Publish an approval item to Instagram with notifications.

        Args:
            item: Approval item to publish
            image_url: Publicly accessible image URL
            hashtags: Optional list of hashtags

        Returns:
            PublishResult with success status and post details
        """
        ...


class PublishingService:
    """Service that orchestrates publishing with notifications.

    Story 4-7, Task 4.3: Integrate hooks into PublishingService.

    Wraps InstagramPublisher and calls notification hooks on
    publish success or failure. Notification failures never
    block the publishing flow.

    Attributes:
        _publisher: Instagram publisher service
        _notifier: Publish notification service
        _event_emitter: WebSocket event emitter
    """

    def __init__(
        self,
        publisher: InstagramPublisherProtocol,
        notifier: Optional["PublishNotifierProtocol"] = None,
        event_emitter: Optional["NotificationEventEmitter"] = None,
    ) -> None:
        """Initialize publishing service.

        Args:
            publisher: Instagram publisher (required)
            notifier: Publish notification service (optional)
            event_emitter: WebSocket event emitter (optional)
        """
        self._publisher = publisher
        self._notifier = notifier
        self._event_emitter = event_emitter

    async def publish_approval_item(
        self,
        item: "ApprovalItem",
        image_url: str,
        hashtags: Optional[list[str]] = None,
    ) -> PublishResult:
        """Publish an approval item to Instagram with notifications.

        Story 4-7, Task 4.3: Full integration of hooks.

        Flow:
        1. Extract caption from approval item
        2. Call InstagramPublisher.publish()
        3. On success: Call on_publish_success hook
        4. On failure: Call on_publish_failed hook
        5. Return result (notifications never block)

        Args:
            item: Approval item containing caption and metadata
            image_url: Publicly accessible image URL
            hashtags: Optional list of hashtags (without #)

        Returns:
            PublishResult with success status and post details
        """
        caption = item.full_caption or ""

        # Publish to Instagram
        result = await self._publisher.publish(
            image_url=image_url,
            caption=caption,
            hashtags=hashtags,
        )

        # Trigger notification hooks (non-blocking)
        await self._handle_publish_result(item, result)

        return result

    async def _handle_publish_result(
        self,
        item: "ApprovalItem",
        result: PublishResult,
    ) -> None:
        """Handle publish result by triggering appropriate hooks.

        Story 4-7, Task 4.4-4.7: Hook integration.

        Args:
            item: The published approval item
            result: Result from InstagramPublisher
        """
        if self._notifier is None and self._event_emitter is None:
            logger.debug("No notifier or event emitter configured, skipping hooks")
            return

        try:
            if result.success:
                await self._on_success(item, result)
            else:
                await self._on_failure(item, result)
        except Exception as e:
            # Task 4.7: Non-blocking execution - never fail publishing flow
            logger.error(f"Notification hook failed (non-blocking): {e}")

    async def _on_success(
        self,
        item: "ApprovalItem",
        result: PublishResult,
    ) -> None:
        """Handle successful publish.

        Story 4-7, Task 4.1, 4.4, 4.6: Success hook integration.

        Args:
            item: The published approval item
            result: Successful publish result
        """
        from core.notifications.hooks import on_publish_success

        if self._notifier is not None and self._event_emitter is not None:
            await on_publish_success(
                item=item,
                instagram_post_id=result.instagram_post_id or "",
                instagram_url=result.permalink or "",
                notifier=self._notifier,
                event_emitter=self._event_emitter,
            )
            logger.info(f"Publish success hook triggered for item {item.id}")
        else:
            logger.debug("Notifier or event emitter not configured, skipping success hook")

    async def _on_failure(
        self,
        item: "ApprovalItem",
        result: PublishResult,
    ) -> None:
        """Handle failed publish.

        Story 4-7, Task 4.2, 4.5, 4.6: Failure hook integration.

        Args:
            item: The failed approval item
            result: Failed publish result
        """
        from core.notifications.hooks import on_publish_failed

        if self._notifier is not None and self._event_emitter is not None:
            # Determine error type from error message
            error_type = get_error_type(Exception(result.error_message or "Unknown"))

            await on_publish_failed(
                item=item,
                error_reason=result.error_message or "Unknown error",
                error_type=error_type,
                notifier=self._notifier,
                event_emitter=self._event_emitter,
            )
            logger.warning(f"Publish failure hook triggered for item {item.id}")
        else:
            logger.debug("Notifier or event emitter not configured, skipping failure hook")


__all__ = [
    "PublishingService",
    "PublishingServiceProtocol",
]
