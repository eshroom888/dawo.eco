"""Notification services for DAWO.ECO.

Provides notification orchestration for approval queue alerts,
publish notifications, rate limiting, failure handling, and WebSocket events.

Story 4-6: Discord Approval Notifications
Story 4-7: Discord Publish Notifications

Exports:
    - ApprovalNotificationService: Orchestrates approval queue notifications
    - ApprovalNotifierProtocol: Protocol for notification service DI
    - NotificationConfig: Configuration dataclass
    - QueueStatus: Queue state dataclass
    - PublishNotificationService: Orchestrates publish notifications (Story 4-7)
    - PublishNotifierProtocol: Protocol for publish notification DI
    - PublishNotificationConfig: Publish notification config
    - PublishedPostInfo: Published post data
    - FailedPublishInfo: Failed publish data
    - PublishBatcher: Batches publish notifications
    - NotificationRateLimiter: Rate limiting for notifications
    - NotificationQueue: Failed notification retry queue
    - QueuedNotification: Queued notification data
    - on_approval_item_created: Event hook for item creation
    - on_publish_success: Event hook for publish success (Story 4-7)
    - on_publish_failed: Event hook for publish failure (Story 4-7)
    - NotificationEvent: WebSocket event data
    - NotificationEventType: Event type enum
    - notification_events: Global event emitter singleton
    - process_notification_queue: ARQ background job
    - NOTIFICATION_JOB_SETTINGS: ARQ worker settings
"""

from core.notifications.approval_notifier import (
    ApprovalNotificationService,
    ApprovalNotifierProtocol,
    NotificationConfig,
    QueueStatus,
)
from core.notifications.publish_notifier import (
    PublishNotificationService,
    PublishNotifierProtocol,
    PublishNotificationConfig,
    PublishedPostInfo,
    FailedPublishInfo,
)
from core.notifications.publish_batcher import PublishBatcher
from core.notifications.rate_limiter import NotificationRateLimiter
from core.notifications.queue import NotificationQueue, QueuedNotification
from core.notifications.hooks import (
    on_approval_item_created,
    on_publish_success,
    on_publish_failed,
)
from core.notifications.events import (
    NotificationEvent,
    NotificationEventType,
    NotificationEventEmitter,
    notification_events,
    get_notification_events,
)
from core.notifications.jobs import (
    process_notification_queue,
    get_notification_queue_depth,
    send_daily_publish_summary,
    process_batch_notifications,
    NOTIFICATION_JOB_SETTINGS,
)

__all__ = [
    # Core approval services (Story 4-6)
    "ApprovalNotificationService",
    "ApprovalNotifierProtocol",
    "NotificationConfig",
    "QueueStatus",
    # Publish notification services (Story 4-7)
    "PublishNotificationService",
    "PublishNotifierProtocol",
    "PublishNotificationConfig",
    "PublishedPostInfo",
    "FailedPublishInfo",
    "PublishBatcher",
    # Rate limiting
    "NotificationRateLimiter",
    # Queue management
    "NotificationQueue",
    "QueuedNotification",
    # Hooks
    "on_approval_item_created",
    "on_publish_success",
    "on_publish_failed",
    # Events
    "NotificationEvent",
    "NotificationEventType",
    "NotificationEventEmitter",
    "notification_events",
    "get_notification_events",
    # ARQ Jobs
    "process_notification_queue",
    "get_notification_queue_depth",
    "send_daily_publish_summary",
    "process_batch_notifications",
    "NOTIFICATION_JOB_SETTINGS",
]
