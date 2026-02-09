"""Publish notification batcher.

Story 4-7: Discord Publish Notifications (Task 3)

Batches publish notifications to prevent spam when multiple posts
publish in quick succession. Uses Redis for state management.

Architecture Compliance:
- Redis for persistent state
- Automatic expiry via TTL
- Non-blocking operations
- Graceful error handling

Behavior:
1. First publish: Start batch timer, store post
2. Subsequent publishes (within window): Add to batch
3. On timer expiry: Trigger batch send
4. Single post after window: Send immediately
"""

from datetime import datetime, timedelta, UTC
from typing import TYPE_CHECKING
import json
import logging

if TYPE_CHECKING:
    import redis.asyncio as redis

from core.notifications.publish_notifier import PublishedPostInfo

logger = logging.getLogger(__name__)


class PublishBatcher:
    """Batches publish notifications to prevent spam.

    When multiple posts publish in quick succession, batches them
    into a single notification. Uses Redis for state management
    with automatic expiry.

    Story 4-7, Task 3 Implementation:
    - AC #2: Batch multiple publishes within window
    - First publish starts timer, don't send immediately
    - On timer expiry: send batch notification
    - Single post after timeout: send individual notification

    Attributes:
        _redis: Redis client (injected)
        _batch_window: Time to wait for additional posts
    """

    KEY_BATCH = "publish:notification:batch"
    KEY_BATCH_START = "publish:notification:batch_start"

    def __init__(
        self,
        redis_client: "redis.Redis",
        batch_window_minutes: int = 15,
    ) -> None:
        """Initialize publish batcher.

        Args:
            redis_client: Async Redis client for state storage
            batch_window_minutes: Time window for batching (default: 15)
        """
        self._redis = redis_client
        self._batch_window = timedelta(minutes=batch_window_minutes)

    async def add_publish(self, post_info: PublishedPostInfo) -> bool:
        """Add a published post to the batch.

        Determines whether to continue batching or trigger send
        based on batch window expiry.

        Args:
            post_info: Information about the published post

        Returns:
            True if batch should be sent now, False to continue batching
        """
        try:
            now = datetime.now(UTC)

            # Check if batch is active
            batch_start = await self._redis.get(self.KEY_BATCH_START)

            if batch_start is None:
                # First post - start new batch
                await self._start_batch(post_info, now)
                return False

            # Add to existing batch
            await self._add_to_batch(post_info)

            # Check if batch window has expired
            batch_start_time = datetime.fromisoformat(batch_start.decode())
            batch_expires = batch_start_time + self._batch_window

            if now >= batch_expires:
                logger.info("Batch window expired, triggering send")
                return True

            return False

        except Exception as e:
            logger.error(f"Error adding publish to batch: {e}")
            # On error, trigger immediate send to avoid losing notification
            return True

    async def get_and_clear_batch(self) -> list[PublishedPostInfo]:
        """Get all batched posts and clear the batch.

        Atomically retrieves all posts and clears the batch state.

        Returns:
            List of PublishedPostInfo objects from the batch
        """
        try:
            # Get all items from batch
            items = await self._redis.lrange(self.KEY_BATCH, 0, -1)

            # Clear batch
            await self._redis.delete(self.KEY_BATCH, self.KEY_BATCH_START)

            # Parse and return
            posts = []
            for item in items:
                try:
                    data = json.loads(item)
                    posts.append(PublishedPostInfo(
                        item_id=data["item_id"],
                        title=data["title"],
                        caption_excerpt=data["caption_excerpt"],
                        instagram_url=data["instagram_url"],
                        publish_time=datetime.fromisoformat(data["publish_time"]),
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse batch item: {e}")
                    continue

            logger.debug(f"Retrieved and cleared batch with {len(posts)} posts")
            return posts

        except Exception as e:
            logger.error(f"Error getting and clearing batch: {e}")
            return []

    async def get_batch_count(self) -> int:
        """Get current number of posts in batch.

        Returns:
            Number of posts currently batched
        """
        try:
            count = await self._redis.llen(self.KEY_BATCH)
            return count or 0
        except Exception as e:
            logger.warning(f"Failed to get batch count: {e}")
            return 0

    async def _start_batch(
        self,
        post_info: PublishedPostInfo,
        start_time: datetime,
    ) -> None:
        """Start a new batch with first post.

        Sets batch start time and adds the first post.

        Args:
            post_info: First post to add to batch
            start_time: When the batch started
        """
        # Set batch start time with TTL
        ttl = int(self._batch_window.total_seconds()) + 60  # Extra minute buffer
        await self._redis.setex(
            self.KEY_BATCH_START,
            ttl,
            start_time.isoformat(),
        )

        # Add first post
        await self._add_to_batch(post_info)

        logger.debug(f"Started new batch with post {post_info.item_id}")

    async def _add_to_batch(self, post_info: PublishedPostInfo) -> None:
        """Add a post to the current batch.

        Serializes post info and appends to Redis list.

        Args:
            post_info: Post to add to batch
        """
        data = {
            "item_id": post_info.item_id,
            "title": post_info.title,
            "caption_excerpt": post_info.caption_excerpt,
            "instagram_url": post_info.instagram_url,
            "publish_time": post_info.publish_time.isoformat(),
        }

        await self._redis.rpush(self.KEY_BATCH, json.dumps(data))

        # Ensure batch expires even if start key is lost
        ttl = int(self._batch_window.total_seconds()) + 60
        await self._redis.expire(self.KEY_BATCH, ttl)

        logger.debug(f"Added post {post_info.item_id} to batch")


__all__ = [
    "PublishBatcher",
]
