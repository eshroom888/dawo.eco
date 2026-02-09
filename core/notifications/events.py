"""Notification Event System.

Story 4-6, Task 3.6: WebSocket/SSE event emission for notification status.

Provides a simple pub/sub event system for notification status changes.
Clients can subscribe via WebSocket or SSE to receive real-time updates.

Usage:
    from core.notifications.events import notification_events, NotificationEvent

    # Emit an event
    await notification_events.emit(NotificationEvent(
        event_type=NotificationEventType.QUEUE_THRESHOLD_REACHED,
        data={"pending_count": 5, "compliance_warnings": 1}
    ))

    # Subscribe to events (in WebSocket handler)
    async for event in notification_events.subscribe():
        await websocket.send_json(event.to_dict())
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class NotificationEventType(str, Enum):
    """Types of notification events.

    Values:
        QUEUE_THRESHOLD_REACHED: Queue reached notification threshold
        NOTIFICATION_SENT: Notification was sent successfully
        NOTIFICATION_FAILED: Notification attempt failed
        NOTIFICATION_QUEUED: Failed notification queued for retry
        COMPLIANCE_WARNING: Item with compliance warning added
        PUBLISH_SUCCESS: Content published to Instagram successfully (Story 4-7)
        PUBLISH_FAILED: Content publish to Instagram failed (Story 4-7)
    """

    QUEUE_THRESHOLD_REACHED = "queue_threshold_reached"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"
    NOTIFICATION_QUEUED = "notification_queued"
    COMPLIANCE_WARNING = "compliance_warning"
    PUBLISH_SUCCESS = "publish_success"
    PUBLISH_FAILED = "publish_failed"


@dataclass
class NotificationEvent:
    """Event emitted for notification status changes.

    Story 4-6, Task 3.6: Event structure for WebSocket updates.

    Attributes:
        event_type: Type of event
        data: Event-specific data payload
        timestamp: When event occurred
        event_id: Unique event identifier
    """

    event_type: NotificationEventType
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationEventEmitter:
    """Event emitter for notification status changes.

    Story 4-6, Task 3.6: Emit WebSocket events for UI notification indicator.

    Thread-safe asyncio-based pub/sub for notification events.
    Subscribers receive events via async generator.

    Attributes:
        MAX_QUEUE_SIZE: Maximum events per subscriber queue (100)
        MAX_SUBSCRIBERS: Maximum concurrent subscribers (100)
    """

    MAX_QUEUE_SIZE = 100
    MAX_SUBSCRIBERS = 100

    def __init__(self) -> None:
        """Initialize event emitter."""
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        logger.info("NotificationEventEmitter initialized")

    async def emit(self, event: NotificationEvent) -> None:
        """Emit an event to all subscribers.

        Story 4-6, Task 3.6: Emit event for UI notification indicator.

        Args:
            event: Event to emit
        """
        async with self._lock:
            dead_queues = []

            for queue in self._subscribers:
                try:
                    # Non-blocking put, drop if queue full
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(
                        "Subscriber queue full, dropping event %s",
                        event.event_id,
                    )
                except Exception as e:
                    logger.warning("Failed to emit to subscriber: %s", e)
                    dead_queues.append(queue)

            # Clean up dead queues
            for queue in dead_queues:
                self._subscribers.remove(queue)

        logger.debug(
            "Emitted %s event to %d subscribers",
            event.event_type.value,
            len(self._subscribers),
        )

    async def subscribe(self) -> AsyncGenerator[NotificationEvent, None]:
        """Subscribe to notification events.

        Yields:
            NotificationEvent objects as they are emitted

        Usage:
            async for event in notification_events.subscribe():
                handle_event(event)
        """
        if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
            logger.warning("Max subscribers reached, rejecting new subscription")
            return

        queue: asyncio.Queue[NotificationEvent] = asyncio.Queue(
            maxsize=self.MAX_QUEUE_SIZE
        )

        async with self._lock:
            self._subscribers.append(queue)

        logger.debug("New subscriber added, total: %d", len(self._subscribers))

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)
            logger.debug("Subscriber removed, total: %d", len(self._subscribers))

    @property
    def subscriber_count(self) -> int:
        """Get current subscriber count."""
        return len(self._subscribers)


# Singleton instance
_notification_events: Optional[NotificationEventEmitter] = None


def get_notification_events() -> NotificationEventEmitter:
    """Get the global notification events emitter.

    Returns:
        NotificationEventEmitter singleton instance
    """
    global _notification_events
    if _notification_events is None:
        _notification_events = NotificationEventEmitter()
    return _notification_events


# Convenience alias
notification_events = get_notification_events()


__all__ = [
    "NotificationEvent",
    "NotificationEventType",
    "NotificationEventEmitter",
    "get_notification_events",
    "notification_events",
]
