"""Execution Event System for Real-Time Dashboard Updates.

Story 7-8, Task 6.1: WebSocket event emission for execution status changes.

Follows exact pattern from core/publishing/events.py (PublishEventEmitter).
Provides asyncio-based pub/sub for execution status updates.

Usage:
    from core.scheduling.execution_events import execution_events, ExecutionEvent

    # Emit an event
    await execution_events.emit(ExecutionEvent(
        event_type=ExecutionEventType.STARTED,
        agent_name="health_claims_monitor",
        execution_id="uuid",
        data={"trigger_type": "scheduled"},
    ))

    # Subscribe to events (in WebSocket handler)
    async for event in execution_events.subscribe():
        await websocket.send_json(event.to_dict())
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import AsyncGenerator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionEventType(str, Enum):
    """Types of execution events.

    Values:
        STARTED: Agent execution started
        COMPLETED: Agent execution completed successfully
        FAILED: Agent execution failed
    """

    STARTED = "execution_started"
    COMPLETED = "execution_completed"
    FAILED = "execution_failed"


@dataclass(frozen=True)
class ExecutionEvent:
    """Event emitted when execution status changes.

    Story 7-8, Task 6.1: Event structure for WebSocket updates.

    Attributes:
        event_type: Type of execution event
        agent_name: Name of the agent
        execution_id: Execution log UUID
        data: Event-specific data payload
        timestamp: When event occurred
        event_id: Unique event identifier
    """

    event_type: ExecutionEventType
    agent_name: str
    execution_id: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "agent_name": self.agent_name,
            "execution_id": self.execution_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionEventEmitter:
    """Event emitter for execution status changes.

    Story 7-8, Task 6.1: Emit WebSocket events on execution start/complete/fail.

    Thread-safe asyncio-based pub/sub for execution events.
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

    async def emit(self, event: ExecutionEvent) -> None:
        """Emit an event to all subscribers.

        Args:
            event: Event to emit
        """
        async with self._lock:
            dead_queues = []

            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(
                        "Subscriber queue full, dropping execution event %s",
                        event.event_id,
                    )
                except Exception as e:
                    logger.warning("Failed to emit to subscriber: %s", e)
                    dead_queues.append(queue)

            for queue in dead_queues:
                self._subscribers.remove(queue)

        logger.debug(
            "Emitted %s event for %s to %d subscribers",
            event.event_type.value,
            event.agent_name,
            len(self._subscribers),
        )

    async def subscribe(self) -> AsyncGenerator[ExecutionEvent, None]:
        """Subscribe to execution events.

        Yields:
            ExecutionEvent objects as they are emitted
        """
        if len(self._subscribers) >= self.MAX_SUBSCRIBERS:
            logger.warning("Max subscribers reached, rejecting new subscription")
            return

        queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue(
            maxsize=self.MAX_QUEUE_SIZE
        )

        async with self._lock:
            self._subscribers.append(queue)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)

    @property
    def subscriber_count(self) -> int:
        """Get current subscriber count."""
        return len(self._subscribers)


# Singleton instance
_execution_events: Optional[ExecutionEventEmitter] = None


def get_execution_events() -> ExecutionEventEmitter:
    """Get the global execution events emitter.

    Returns:
        ExecutionEventEmitter singleton instance
    """
    global _execution_events
    if _execution_events is None:
        _execution_events = ExecutionEventEmitter()
    return _execution_events


# Convenience alias
execution_events = get_execution_events()


__all__ = [
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionEventEmitter",
    "get_execution_events",
    "execution_events",
]
