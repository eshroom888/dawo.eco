"""Tests for PublishBatcher.

Story 4-7: Discord Publish Notifications (Task 3)

Tests the publish batching logic including:
- Adding posts to batch
- Batch window expiry detection
- Clearing batch after send
- Redis state management

Test Coverage:
- AC #2: Batch multiple publishes within window
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import json

import pytest

from core.notifications.publish_batcher import PublishBatcher
from core.notifications.publish_notifier import PublishedPostInfo


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.rpush = AsyncMock()
    mock.lrange = AsyncMock(return_value=[])
    mock.llen = AsyncMock(return_value=0)
    mock.delete = AsyncMock()
    mock.expire = AsyncMock()
    return mock


def create_published_post_info(
    item_id: str = None,
    title: str = "Test post",
    caption_excerpt: str = "Test caption...",
    instagram_url: str = "https://instagram.com/p/test",
    publish_time: datetime = None,
) -> PublishedPostInfo:
    """Create a published post info for testing."""
    return PublishedPostInfo(
        item_id=item_id or str(uuid4()),
        title=title,
        caption_excerpt=caption_excerpt,
        instagram_url=instagram_url,
        publish_time=publish_time or datetime.now(UTC),
    )


class TestPublishBatcher:
    """Tests for publish batching logic."""

    @pytest.mark.asyncio
    async def test_first_publish_starts_batch(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify first publish starts a new batch (AC #2)."""
        # Arrange
        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )
        post_info = create_published_post_info()

        # Act
        should_send = await batcher.add_publish(post_info)

        # Assert: First publish should not trigger send
        assert should_send is False
        mock_redis.setex.assert_called_once()  # Batch start time set
        mock_redis.rpush.assert_called_once()  # Post added to batch

    @pytest.mark.asyncio
    async def test_second_publish_added_to_batch(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify subsequent publishes are added to batch (AC #2)."""
        # Arrange: Batch already started
        batch_start = datetime.now(UTC)
        mock_redis.get = AsyncMock(return_value=batch_start.isoformat().encode())

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )
        post_info = create_published_post_info()

        # Act
        should_send = await batcher.add_publish(post_info)

        # Assert
        assert should_send is False
        mock_redis.rpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_window_expired(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify batch triggers when window expires (AC #2)."""
        # Arrange: Batch started 20 minutes ago (past 15 min window)
        batch_start = datetime.now(UTC) - timedelta(minutes=20)
        mock_redis.get = AsyncMock(return_value=batch_start.isoformat().encode())

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )
        post_info = create_published_post_info()

        # Act
        should_send = await batcher.add_publish(post_info)

        # Assert: Should trigger send
        assert should_send is True

    @pytest.mark.asyncio
    async def test_get_and_clear_batch(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify batch is retrieved and cleared (AC #2)."""
        # Arrange: 2 posts in batch
        now = datetime.now(UTC)
        batch_items = [
            json.dumps({
                "item_id": "post-1",
                "title": "Post 1",
                "caption_excerpt": "Caption 1",
                "instagram_url": "https://instagram.com/p/1",
                "publish_time": now.isoformat(),
            }).encode(),
            json.dumps({
                "item_id": "post-2",
                "title": "Post 2",
                "caption_excerpt": "Caption 2",
                "instagram_url": "https://instagram.com/p/2",
                "publish_time": now.isoformat(),
            }).encode(),
        ]
        mock_redis.lrange = AsyncMock(return_value=batch_items)

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )

        # Act
        posts = await batcher.get_and_clear_batch()

        # Assert
        assert len(posts) == 2
        assert posts[0].item_id == "post-1"
        assert posts[1].item_id == "post-2"
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty_list(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify empty batch returns empty list."""
        # Arrange
        mock_redis.lrange = AsyncMock(return_value=[])

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )

        # Act
        posts = await batcher.get_and_clear_batch()

        # Assert
        assert posts == []

    @pytest.mark.asyncio
    async def test_get_batch_count(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify batch count retrieval."""
        # Arrange
        mock_redis.llen = AsyncMock(return_value=3)

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )

        # Act
        count = await batcher.get_batch_count()

        # Assert
        assert count == 3

    @pytest.mark.asyncio
    async def test_batch_ttl_set(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify batch items have TTL set."""
        # Arrange
        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )
        post_info = create_published_post_info()

        # Act
        await batcher.add_publish(post_info)

        # Assert: Expire should be called on batch list
        mock_redis.expire.assert_called()


class TestRedisFallback:
    """Tests for Redis unavailable fallback (Code Review Fix LOW #7)."""

    @pytest.mark.asyncio
    async def test_add_publish_returns_true_on_redis_error(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify add_publish triggers immediate send on Redis error (LOW #7).

        When Redis is unavailable, batching should fail gracefully and
        trigger immediate notification to prevent losing the notification.
        """
        # Arrange: Redis raises exception
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )
        post_info = create_published_post_info()

        # Act
        should_send = await batcher.add_publish(post_info)

        # Assert: Should trigger immediate send (fallback behavior)
        assert should_send is True

    @pytest.mark.asyncio
    async def test_get_and_clear_batch_returns_empty_on_redis_error(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify get_and_clear_batch returns empty list on Redis error."""
        # Arrange: Redis raises exception on lrange
        mock_redis.lrange = AsyncMock(side_effect=Exception("Redis connection failed"))

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )

        # Act
        posts = await batcher.get_and_clear_batch()

        # Assert: Returns empty list, doesn't raise
        assert posts == []

    @pytest.mark.asyncio
    async def test_get_batch_count_returns_zero_on_redis_error(
        self,
        mock_redis: AsyncMock,
    ) -> None:
        """Verify get_batch_count returns 0 on Redis error."""
        # Arrange: Redis raises exception
        mock_redis.llen = AsyncMock(side_effect=Exception("Redis connection failed"))

        batcher = PublishBatcher(
            redis_client=mock_redis,
            batch_window_minutes=15,
        )

        # Act
        count = await batcher.get_batch_count()

        # Assert: Returns 0, doesn't raise
        assert count == 0
