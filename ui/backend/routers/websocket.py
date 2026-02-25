"""WebSocket Router for Real-Time Events.

Epic 4 Tech Debt: Wire up event emitters to WebSocket connections.
Story 7-8, Task 6.3: Execution events for dashboard real-time updates.

Provides WebSocket endpoints for:
- Publishing events (publish success/failure, status changes)
- Notification events (queue thresholds, compliance warnings)
- Execution events (agent start/complete/fail for dashboard)

Usage:
    Connect to /ws/publish for publishing events
    Connect to /ws/notifications for notification events
    Connect to /ws/executions for execution events
    Connect to /ws/all for all events combined
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.notifications.events import (
    NotificationEvent,
    get_notification_events,
)
from core.publishing.events import (
    PublishEvent,
    get_publish_events,
)
from core.scheduling.execution_events import (
    ExecutionEvent,
    get_execution_events,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manage active WebSocket connections.

    Tracks connected clients and provides utilities for
    broadcasting messages to all or specific clients.
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket connected, total: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket disconnected, total: %d",
            len(self.active_connections),
        )

    async def send_json(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """Send JSON data to a specific connection."""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.warning("Failed to send to WebSocket: %s", e)


# Connection managers for different event streams
publish_manager = ConnectionManager()
notification_manager = ConnectionManager()
execution_manager = ConnectionManager()


@router.websocket("/publish")
async def websocket_publish_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for publishing events.

    Epic 4 Tech Debt: Wire up publish event emitter.

    Streams real-time updates for:
    - PUBLISHING: Publish attempt started
    - PUBLISH_SUCCESS: Post published successfully
    - PUBLISH_FAILED: Publish attempt failed
    - RETRY_SCHEDULED: Retry has been scheduled
    """
    await publish_manager.connect(websocket)
    publish_events = get_publish_events()

    try:
        # Create a task for receiving (to detect disconnect)
        receive_task = asyncio.create_task(websocket.receive_text())

        # Subscribe and forward events
        async for event in publish_events.subscribe():
            await publish_manager.send_json(websocket, event.to_dict())

            # Check if client disconnected
            if receive_task.done():
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from publish events")
    except Exception as e:
        logger.error("Error in publish WebSocket: %s", e)
    finally:
        publish_manager.disconnect(websocket)


@router.websocket("/notifications")
async def websocket_notification_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for notification events.

    Epic 4 Tech Debt: Wire up notification event emitter.

    Streams real-time updates for:
    - QUEUE_THRESHOLD_REACHED: Queue reached notification threshold
    - NOTIFICATION_SENT: Notification was sent successfully
    - NOTIFICATION_FAILED: Notification attempt failed
    - COMPLIANCE_WARNING: Item with compliance warning added
    - PUBLISH_SUCCESS: Content published to Instagram
    - PUBLISH_FAILED: Content publish failed
    """
    await notification_manager.connect(websocket)
    notification_events = get_notification_events()

    try:
        # Create a task for receiving (to detect disconnect)
        receive_task = asyncio.create_task(websocket.receive_text())

        # Subscribe and forward events
        async for event in notification_events.subscribe():
            await notification_manager.send_json(websocket, event.to_dict())

            # Check if client disconnected
            if receive_task.done():
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from notification events")
    except Exception as e:
        logger.error("Error in notification WebSocket: %s", e)
    finally:
        notification_manager.disconnect(websocket)


@router.websocket("/executions")
async def websocket_execution_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for execution events.

    Story 7-8, Task 6.3: Real-time execution dashboard updates.

    Streams real-time updates for:
    - STARTED: Agent execution began
    - COMPLETED: Agent execution succeeded
    - FAILED: Agent execution failed
    """
    await execution_manager.connect(websocket)
    exec_events = get_execution_events()

    try:
        receive_task = asyncio.create_task(websocket.receive_text())

        async for event in exec_events.subscribe():
            await execution_manager.send_json(websocket, event.to_dict())

            if receive_task.done():
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from execution events")
    except Exception as e:
        logger.error("Error in execution WebSocket: %s", e)
    finally:
        execution_manager.disconnect(websocket)


@router.websocket("/all")
async def websocket_all_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for all events combined.

    Streams publishing, notification, and execution events on a single connection.
    Events are tagged with their source for client-side routing.
    """
    await websocket.accept()

    publish_events = get_publish_events()
    notification_events = get_notification_events()
    exec_events = get_execution_events()

    async def forward_publish_events() -> None:
        """Forward publish events to WebSocket."""
        async for event in publish_events.subscribe():
            data = event.to_dict()
            data["source"] = "publish"
            try:
                await websocket.send_json(data)
            except Exception:
                break

    async def forward_notification_events() -> None:
        """Forward notification events to WebSocket."""
        async for event in notification_events.subscribe():
            data = event.to_dict()
            data["source"] = "notification"
            try:
                await websocket.send_json(data)
            except Exception:
                break

    async def forward_execution_events() -> None:
        """Forward execution events to WebSocket."""
        async for event in exec_events.subscribe():
            data = event.to_dict()
            data["source"] = "execution"
            try:
                await websocket.send_json(data)
            except Exception:
                break

    try:
        # Run all forwarders concurrently
        await asyncio.gather(
            forward_publish_events(),
            forward_notification_events(),
            forward_execution_events(),
            return_exceptions=True,
        )
    except WebSocketDisconnect:
        logger.info("Client disconnected from all events")
    except Exception as e:
        logger.error("Error in combined WebSocket: %s", e)


@router.get("/status")
async def websocket_status() -> dict[str, Any]:
    """Get WebSocket connection status.

    Returns:
        Connection counts for each event stream
    """
    publish_events = get_publish_events()
    notification_events = get_notification_events()
    exec_events = get_execution_events()

    return {
        "publish_connections": len(publish_manager.active_connections),
        "notification_connections": len(notification_manager.active_connections),
        "execution_connections": len(execution_manager.active_connections),
        "publish_subscribers": publish_events.subscriber_count,
        "notification_subscribers": notification_events.subscriber_count,
        "execution_subscribers": exec_events.subscriber_count,
    }


__all__ = [
    "router",
    "publish_manager",
    "notification_manager",
    "execution_manager",
]
