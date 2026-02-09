"""Notification event hooks.

Story 4-6: Discord Approval Notifications (Task 3)
Story 4-7: Discord Publish Notifications (Task 4)

Provides event hooks that trigger notification checks when
content enters the approval queue or is published/fails to publish.

Architecture Compliance:
- Non-blocking notification flow
- Graceful error handling
- Comprehensive logging
- WebSocket event emission for UI updates

Usage:
    from core.notifications.hooks import on_approval_item_created, on_publish_success

    # In content submission flow
    item = await create_approval_item(...)
    await on_approval_item_created(item, notifier)

    # In publishing flow (Story 4-7)
    await on_publish_success(item, instagram_post_id, instagram_url, notifier, event_emitter)
"""

from datetime import datetime, UTC
from typing import TYPE_CHECKING
import logging

from core.notifications.events import (
    notification_events,
    NotificationEvent,
    NotificationEventType,
)

if TYPE_CHECKING:
    from core.approval.models import ApprovalItem
    from core.notifications.approval_notifier import ApprovalNotifierProtocol
    from core.notifications.publish_notifier import (
        PublishNotifierProtocol,
        PublishedPostInfo,
        FailedPublishInfo,
    )
    from core.notifications.events import NotificationEventEmitter

logger = logging.getLogger(__name__)


async def on_approval_item_created(
    item: "ApprovalItem",
    notifier: "ApprovalNotifierProtocol",
) -> None:
    """Hook called when a new item enters the approval queue.

    Triggers notification check asynchronously to avoid blocking
    the content submission flow.

    Story 4-6, Task 3 Implementation:
    - AC #1: Trigger notification check on item creation
    - AC #3: Log compliance warnings for prioritization
    - AC #4: Non-blocking execution

    Args:
        item: The newly created approval item
        notifier: Notification service instance

    Note:
        This hook never raises exceptions - all errors are logged
        but do not block the content submission flow.
    """
    try:
        # Log and emit compliance warnings for visibility (Task 3.6)
        if item.compliance_status == "WARNING":
            logger.info(
                f"Compliance warning on item {item.id}, "
                "checking for immediate notification"
            )
            # Emit WebSocket event for UI notification indicator
            await notification_events.emit(NotificationEvent(
                event_type=NotificationEventType.COMPLIANCE_WARNING,
                data={
                    "item_id": str(item.id),
                    "source_type": item.source_type,
                    "message": "Item requires compliance review",
                },
            ))

        # Trigger notification check (rate limiting handled internally)
        notification_sent = await notifier.check_and_notify()

        # Emit WebSocket event for UI notification indicator (Task 3.6)
        if notification_sent:
            await notification_events.emit(NotificationEvent(
                event_type=NotificationEventType.NOTIFICATION_SENT,
                data={
                    "trigger_item_id": str(item.id),
                    "message": "Approval queue notification sent",
                },
            ))

        logger.debug(f"Notification hook completed for item {item.id}")

    except Exception as e:
        # Never block content submission on notification failure
        logger.error(
            f"Failed to process notification hook for item {item.id}: {e}"
        )


async def on_publish_success(
    item: "ApprovalItem",
    instagram_post_id: str,
    instagram_url: str,
    notifier: "PublishNotifierProtocol",
    event_emitter: "NotificationEventEmitter",
) -> None:
    """Hook called when a post is successfully published to Instagram.

    Story 4-7, Task 4.1: Publish success hook.

    Triggers publish notification (may be batched) and emits
    WebSocket event for real-time UI update.

    Args:
        item: The published approval item
        instagram_post_id: Instagram's post ID
        instagram_url: Direct link to Instagram post
        notifier: Publish notification service
        event_emitter: WebSocket event emitter

    Note:
        This hook never raises exceptions - all errors are logged
        but do not block the publishing flow.
    """
    try:
        # Import here to avoid circular dependency
        from core.notifications.publish_notifier import PublishedPostInfo

        # Create post info from approval item
        caption = item.full_caption or ""
        post_info = PublishedPostInfo(
            item_id=str(item.id),
            title=caption[:50] + "..." if len(caption) > 50 else caption,
            caption_excerpt=caption[:100],
            instagram_url=instagram_url,
            publish_time=datetime.now(UTC),
        )

        # Trigger notification (batching handled internally)
        await notifier.notify_publish_success(post_info)

        # Emit WebSocket event for UI
        await event_emitter.emit(NotificationEvent(
            event_type=NotificationEventType.PUBLISH_SUCCESS,
            data={
                "item_id": str(item.id),
                "instagram_post_id": instagram_post_id,
                "instagram_url": instagram_url,
                "message": "Content published to Instagram",
            },
        ))

        logger.info(f"Published item {item.id}, notification triggered")

    except Exception as e:
        # Never block publishing flow on notification failure
        logger.error(f"Failed to process publish success hook: {e}")


async def on_publish_failed(
    item: "ApprovalItem",
    error_reason: str,
    error_type: str,
    notifier: "PublishNotifierProtocol",
    event_emitter: "NotificationEventEmitter",
) -> None:
    """Hook called when publishing to Instagram fails.

    Story 4-7, Task 4.2: Publish failure hook.

    Triggers immediate failure notification (no batching) and
    emits WebSocket event for real-time UI update.

    Args:
        item: The failed approval item
        error_reason: Human-readable error message
        error_type: Error category (API_ERROR, RATE_LIMIT, etc.)
        notifier: Publish notification service
        event_emitter: WebSocket event emitter

    Note:
        This hook never raises exceptions - all errors are logged
        but do not block the publishing flow.
    """
    try:
        # Import here to avoid circular dependency
        from core.notifications.publish_notifier import FailedPublishInfo

        # Create failure info
        caption = item.full_caption or ""
        failure_info = FailedPublishInfo(
            item_id=str(item.id),
            title=caption[:50] + "..." if len(caption) > 50 else caption,
            error_reason=error_reason,
            error_type=error_type,
            scheduled_time=item.scheduled_publish_time or datetime.now(UTC),
        )

        # Send immediate notification (failures always urgent)
        await notifier.notify_publish_failed(failure_info)

        # Emit WebSocket event for UI
        await event_emitter.emit(NotificationEvent(
            event_type=NotificationEventType.PUBLISH_FAILED,
            data={
                "item_id": str(item.id),
                "error_reason": error_reason,
                "error_type": error_type,
                "message": "Failed to publish to Instagram",
            },
        ))

        logger.warning(f"Publish failed for item {item.id}: {error_reason}")

    except Exception as e:
        logger.error(f"Failed to process publish failure hook: {e}")


__all__ = [
    "on_approval_item_created",
    "on_publish_success",
    "on_publish_failed",
]
