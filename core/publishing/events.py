"""Publishing Event System.

Story 4-5, Task 3.6: WebSocket/SSE event emission for publish status updates.

Provides a simple pub/sub event system for publishing status changes.
Clients can subscribe via WebSocket or SSE to receive real-time updates.

Usage:
    from core.publishing.events import publish_events, PublishEvent

    # Emit an event
    await publish_events.emit(PublishEvent(
        event_type="publish_success",
        item_id="uuid",
        data={"instagram_post_id": "123", "permalink": "..."}
    ))

    # Subscribe to events (in WebSocket handler)
    async for event in publish_events.subscribe():
        await websocket.send_json(event.to_dict())
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class PublishEventType(str, Enum):
    """Types of publishing events.

    Values:
        PUBLISHING: Publish attempt started
        PUBLISH_SUCCESS: Post published successfully
        PUBLISH_FAILED: Publish attempt failed
        RETRY_SCHEDULED: Retry has been scheduled
    """

    PUBLISHING = "publishing"
    PUBLISH_SUCCESS = "publish_success"
    PUBLISH_FAILED = "publish_failed"
    RETRY_SCHEDULED = "retry_scheduled"


@dataclass
class PublishEvent:
    """Event emitted when publish status changes.

    Story 4-5, Task 3.6: Event structure for WebSocket updates.

    Attributes:
        event_type: Type of event
        item_id: Approval item ID
        data: Event-specific data payload
        timestamp: When event occurred
        event_id: Unique event identifier
    """

    event_type: PublishEventType
    item_id: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "item_id": self.item_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class PublishEventEmitter:
    """Event emitter for publishing status changes.

    Story 4-5, Task 3.6: Emit WebSocket events on publish success.

    Thread-safe asyncio-based pub/sub for publishing events.
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
        logger.info("PublishEventEmitter initialized")

    async def emit(self, event: PublishEvent) -> None:
        """Emit an event to all subscribers.

        Story 4-5, Task 3.6: Emit event on publish success/failure.

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
            "Emitted %s event for item %s to %d subscribers",
            event.event_type.value,
            event.item_id,
            len(self._subscribers),
        )

    async def subscribe(self) -> AsyncGenerator[PublishEvent, None]:
        """Subscribe to publishing events.

        Yields:
            PublishEvent objects as they are emitted

        Usage:
            async for event in publish_events.subscribe():
                handle_event(event)
        """
        if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
            logger.warning("Max subscribers reached, rejecting new subscription")
            return

        queue: asyncio.Queue[PublishEvent] = asyncio.Queue(
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
_publish_events: Optional[PublishEventEmitter] = None


def get_publish_events() -> PublishEventEmitter:
    """Get the global publish events emitter.

    Returns:
        PublishEventEmitter singleton instance
    """
    global _publish_events
    if _publish_events is None:
        _publish_events = PublishEventEmitter()
    return _publish_events


# Convenience alias
publish_events = get_publish_events()


__all__ = [
    "PublishEvent",
    "PublishEventType",
    "PublishEventEmitter",
    "get_publish_events",
    "publish_events",
]
