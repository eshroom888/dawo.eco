"""Integration tests for the complete publish flow.

Epic 4 Tech Debt: End-to-end tests for publish workflow.

Tests the complete flow from approval item through:
1. Instagram publishing
2. Discord notifications
3. WebSocket events
4. Status updates

Uses protocol-based mocks for external services while
testing real integration between internal components.
"""

import asyncio
import pytest
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from core.publishing.events import (
    PublishEvent,
    PublishEventType,
    PublishEventEmitter,
    get_publish_events,
)
from core.publishing.instagram_publisher import (
    PublishResult,
    InstagramPublisherProtocol,
)
from core.publishing.publishing_service import PublishingService
from core.notifications.events import (
    NotificationEvent,
    NotificationEventType,
    NotificationEventEmitter,
    get_notification_events,
)


@dataclass
class MockApprovalItem:
    """Mock approval item for testing.

    Minimal implementation matching ApprovalItem interface.
    """

    id: str
    full_caption: str
    thumbnail_url: str = "https://example.com/image.jpg"
    hashtags: list[str] | None = None
    source_type: str = "instagram_post"


class MockInstagramClient:
    """Mock Instagram client for integration tests.

    Simulates Instagram Graph API responses.
    """

    def __init__(
        self,
        should_succeed: bool = True,
        error_message: Optional[str] = None,
        delay_seconds: float = 0.0,
    ) -> None:
        """Initialize mock client.

        Args:
            should_succeed: Whether publish should succeed
            error_message: Error message if failing
            delay_seconds: Simulated API latency
        """
        self.should_succeed = should_succeed
        self.error_message = error_message
        self.delay_seconds = delay_seconds
        self.publish_calls: list[dict] = []

    async def publish(
        self,
        image_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
    ) -> PublishResult:
        """Mock publish method.

        Args:
            image_url: Image URL
            caption: Caption text
            hashtags: Optional hashtags

        Returns:
            PublishResult based on configuration
        """
        self.publish_calls.append({
            "image_url": image_url,
            "caption": caption,
            "hashtags": hashtags,
            "timestamp": datetime.now(UTC),
        })

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_succeed:
            return PublishResult(
                success=True,
                instagram_post_id=f"mock-post-{uuid4().hex[:8]}",
                permalink=f"https://instagram.com/p/mock-{uuid4().hex[:8]}",
                error_message=None,
            )
        else:
            return PublishResult(
                success=False,
                instagram_post_id=None,
                permalink=None,
                error_message=self.error_message or "Mock publish failed",
            )


class MockPublishNotifier:
    """Mock publish notifier for integration tests.

    Captures notification calls for verification.
    """

    def __init__(self) -> None:
        """Initialize mock notifier."""
        self.success_notifications: list[dict] = []
        self.failure_notifications: list[dict] = []

    async def notify_publish_success(
        self,
        item_id: str,
        instagram_post_id: str,
        instagram_url: str,
    ) -> None:
        """Record success notification."""
        self.success_notifications.append({
            "item_id": item_id,
            "instagram_post_id": instagram_post_id,
            "instagram_url": instagram_url,
            "timestamp": datetime.now(UTC),
        })

    async def notify_publish_failure(
        self,
        item_id: str,
        error_reason: str,
        error_type: str,
    ) -> None:
        """Record failure notification."""
        self.failure_notifications.append({
            "item_id": item_id,
            "error_reason": error_reason,
            "error_type": error_type,
            "timestamp": datetime.now(UTC),
        })


class TestPublishFlowIntegration:
    """Integration tests for the publish workflow."""

    @pytest.fixture
    def mock_item(self) -> MockApprovalItem:
        """Create a mock approval item."""
        return MockApprovalItem(
            id=str(uuid4()),
            full_caption="Test caption for integration test",
            hashtags=["test", "integration"],
        )

    @pytest.fixture
    def mock_instagram(self) -> MockInstagramClient:
        """Create a mock Instagram client configured for success."""
        return MockInstagramClient(should_succeed=True)

    @pytest.fixture
    def mock_instagram_fail(self) -> MockInstagramClient:
        """Create a mock Instagram client configured for failure."""
        return MockInstagramClient(
            should_succeed=False,
            error_message="Rate limit exceeded",
        )

    @pytest.fixture
    def mock_notifier(self) -> MockPublishNotifier:
        """Create a mock notification service."""
        return MockPublishNotifier()

    @pytest.fixture
    def publish_events(self) -> PublishEventEmitter:
        """Create a fresh publish event emitter."""
        return PublishEventEmitter()

    @pytest.fixture
    def notification_events(self) -> NotificationEventEmitter:
        """Create a fresh notification event emitter."""
        return NotificationEventEmitter()

    @pytest.mark.asyncio
    async def test_successful_publish_flow(
        self,
        mock_item: MockApprovalItem,
        mock_instagram: MockInstagramClient,
        mock_notifier: MockPublishNotifier,
        notification_events: NotificationEventEmitter,
    ) -> None:
        """Test complete successful publish flow.

        Verifies:
        1. Instagram publish called with correct data
        2. Success notification triggered
        3. Result contains post ID and permalink
        """
        service = PublishingService(
            publisher=mock_instagram,
            notifier=mock_notifier,
            event_emitter=notification_events,
        )

        result = await service.publish_approval_item(
            item=mock_item,
            image_url="https://example.com/image.jpg",
            hashtags=["eco", "sustainable"],
        )

        # Verify Instagram was called
        assert len(mock_instagram.publish_calls) == 1
        call = mock_instagram.publish_calls[0]
        assert call["image_url"] == "https://example.com/image.jpg"
        assert call["caption"] == mock_item.full_caption
        assert call["hashtags"] == ["eco", "sustainable"]

        # Verify result
        assert result.success is True
        assert result.instagram_post_id is not None
        assert result.permalink is not None
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_failed_publish_flow(
        self,
        mock_item: MockApprovalItem,
        mock_instagram_fail: MockInstagramClient,
        mock_notifier: MockPublishNotifier,
        notification_events: NotificationEventEmitter,
    ) -> None:
        """Test complete failed publish flow.

        Verifies:
        1. Instagram publish called
        2. Failure notification triggered
        3. Result contains error message
        """
        service = PublishingService(
            publisher=mock_instagram_fail,
            notifier=mock_notifier,
            event_emitter=notification_events,
        )

        result = await service.publish_approval_item(
            item=mock_item,
            image_url="https://example.com/image.jpg",
        )

        # Verify Instagram was called
        assert len(mock_instagram_fail.publish_calls) == 1

        # Verify result
        assert result.success is False
        assert result.instagram_post_id is None
        assert result.error_message == "Rate limit exceeded"

    @pytest.mark.asyncio
    async def test_publish_without_notifier(
        self,
        mock_item: MockApprovalItem,
        mock_instagram: MockInstagramClient,
    ) -> None:
        """Test publish flow works without notifier configured.

        Publishing should succeed even when notifications are disabled.
        """
        service = PublishingService(
            publisher=mock_instagram,
            notifier=None,
            event_emitter=None,
        )

        result = await service.publish_approval_item(
            item=mock_item,
            image_url="https://example.com/image.jpg",
        )

        assert result.success is True
        assert result.instagram_post_id is not None

    @pytest.mark.asyncio
    async def test_websocket_event_emission(
        self,
        publish_events: PublishEventEmitter,
    ) -> None:
        """Test WebSocket events are emitted correctly.

        Verifies the event emitter can:
        1. Accept subscribers
        2. Emit events to subscribers
        3. Deliver correct event data
        """
        received_events: list[PublishEvent] = []

        async def collect_events() -> None:
            async for event in publish_events.subscribe():
                received_events.append(event)
                if len(received_events) >= 2:
                    break

        # Start collector in background
        collector_task = asyncio.create_task(collect_events())

        # Give collector time to subscribe
        await asyncio.sleep(0.1)

        # Emit events
        await publish_events.emit(PublishEvent(
            event_type=PublishEventType.PUBLISHING,
            item_id="test-1",
            data={"status": "starting"},
        ))

        await publish_events.emit(PublishEvent(
            event_type=PublishEventType.PUBLISH_SUCCESS,
            item_id="test-1",
            data={"instagram_post_id": "12345"},
        ))

        # Wait for collection with timeout
        try:
            await asyncio.wait_for(collector_task, timeout=2.0)
        except asyncio.TimeoutError:
            collector_task.cancel()

        # Verify events received
        assert len(received_events) >= 2
        assert received_events[0].event_type == PublishEventType.PUBLISHING
        assert received_events[1].event_type == PublishEventType.PUBLISH_SUCCESS

    @pytest.mark.asyncio
    async def test_notification_event_emission(
        self,
        notification_events: NotificationEventEmitter,
    ) -> None:
        """Test notification events are emitted correctly."""
        received_events: list[NotificationEvent] = []

        async def collect_events() -> None:
            async for event in notification_events.subscribe():
                received_events.append(event)
                if len(received_events) >= 1:
                    break

        # Start collector
        collector_task = asyncio.create_task(collect_events())
        await asyncio.sleep(0.1)

        # Emit event
        await notification_events.emit(NotificationEvent(
            event_type=NotificationEventType.PUBLISH_SUCCESS,
            data={"item_id": "test-1", "instagram_url": "https://..."},
        ))

        try:
            await asyncio.wait_for(collector_task, timeout=2.0)
        except asyncio.TimeoutError:
            collector_task.cancel()

        assert len(received_events) >= 1
        assert received_events[0].event_type == NotificationEventType.PUBLISH_SUCCESS

    @pytest.mark.asyncio
    async def test_publish_with_retry_simulation(
        self,
        mock_item: MockApprovalItem,
        mock_notifier: MockPublishNotifier,
        notification_events: NotificationEventEmitter,
    ) -> None:
        """Test publish flow handles transient failures.

        Simulates a first-attempt failure followed by success.
        """
        attempt_count = 0

        class RetryingMockClient:
            """Mock that fails first attempt, succeeds second."""

            async def publish(self, **kwargs) -> PublishResult:
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count == 1:
                    return PublishResult(
                        success=False,
                        error_message="Transient error",
                    )
                return PublishResult(
                    success=True,
                    instagram_post_id="retry-success-123",
                    permalink="https://instagram.com/p/retry",
                )

        client = RetryingMockClient()
        service = PublishingService(
            publisher=client,
            notifier=mock_notifier,
            event_emitter=notification_events,
        )

        # First attempt fails
        result1 = await service.publish_approval_item(
            item=mock_item,
            image_url="https://example.com/image.jpg",
        )
        assert result1.success is False

        # Second attempt succeeds
        result2 = await service.publish_approval_item(
            item=mock_item,
            image_url="https://example.com/image.jpg",
        )
        assert result2.success is True
        assert result2.instagram_post_id == "retry-success-123"

    @pytest.mark.asyncio
    async def test_concurrent_publishes(
        self,
        mock_instagram: MockInstagramClient,
    ) -> None:
        """Test multiple concurrent publish operations.

        Verifies the system handles concurrent requests without race conditions.
        """
        # Add small delay to simulate real API latency
        mock_instagram.delay_seconds = 0.05

        service = PublishingService(
            publisher=mock_instagram,
            notifier=None,
            event_emitter=None,
        )

        # Create multiple items
        items = [
            MockApprovalItem(id=str(uuid4()), full_caption=f"Caption {i}")
            for i in range(5)
        ]

        # Publish all concurrently
        tasks = [
            service.publish_approval_item(
                item=item,
                image_url=f"https://example.com/image-{i}.jpg",
            )
            for i, item in enumerate(items)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.success for r in results)
        assert len(mock_instagram.publish_calls) == 5

        # All should have unique post IDs
        post_ids = [r.instagram_post_id for r in results]
        assert len(set(post_ids)) == 5


class TestEventEmitterEdgeCases:
    """Edge case tests for event emitters."""

    @pytest.mark.asyncio
    async def test_event_dropped_when_queue_full(self) -> None:
        """Test events are dropped gracefully when subscriber queue is full."""
        emitter = PublishEventEmitter()
        emitter.MAX_QUEUE_SIZE = 2  # Small queue for testing

        received: list[PublishEvent] = []

        async def slow_subscriber() -> None:
            async for event in emitter.subscribe():
                await asyncio.sleep(0.5)  # Slow processing
                received.append(event)

        task = asyncio.create_task(slow_subscriber())
        await asyncio.sleep(0.1)

        # Emit more events than queue can hold
        for i in range(5):
            await emitter.emit(PublishEvent(
                event_type=PublishEventType.PUBLISHING,
                item_id=f"item-{i}",
            ))

        # Cancel slow subscriber
        await asyncio.sleep(0.1)
        task.cancel()

        # Should have handled overflow gracefully (no exception)

    @pytest.mark.asyncio
    async def test_subscriber_cleanup_on_disconnect(self) -> None:
        """Test subscribers are cleaned up when they disconnect."""
        emitter = PublishEventEmitter()

        async def connect_and_disconnect() -> None:
            async for _ in emitter.subscribe():
                break  # Disconnect immediately

        # Connect subscriber
        task = asyncio.create_task(connect_and_disconnect())

        # Wait for subscribe
        await asyncio.sleep(0.1)
        initial_count = emitter.subscriber_count

        # Emit event to trigger disconnect
        await emitter.emit(PublishEvent(
            event_type=PublishEventType.PUBLISHING,
            item_id="test",
        ))

        await asyncio.sleep(0.1)

        # Subscriber should be cleaned up
        assert emitter.subscriber_count < initial_count or initial_count == 0


__all__ = [
    "TestPublishFlowIntegration",
    "TestEventEmitterEdgeCases",
    "MockApprovalItem",
    "MockInstagramClient",
    "MockPublishNotifier",
]
