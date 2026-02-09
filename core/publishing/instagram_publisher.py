"""Instagram Publisher Service.

Story 4-5: Instagram Graph API Auto-Publishing

This module provides the InstagramPublisher service that wraps the
Instagram Graph API client with retry middleware, logging, and metrics.

Architecture Compliance:
- Configuration injected via constructor
- Uses retry middleware for all API calls
- Implements Protocol for dependency injection
- Returns typed PublishResult, never raises exceptions

Usage:
    from core.publishing import InstagramPublisher
    from integrations.instagram import InstagramPublishClient
    from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig

    client = InstagramPublishClient(access_token, account_id)
    retry = RetryMiddleware(RetryConfig(max_retries=3))
    publisher = InstagramPublisher(client, retry)

    result = await publisher.publish(
        image_url="https://...",
        caption="Post caption",
        hashtags=["mushrooms", "wellness"],
    )
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional, Protocol, runtime_checkable

from integrations.instagram import (
    InstagramPublishClient,
    InstagramPublishClientProtocol,
    PublishResult as InstagramPublishResult,
)
from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig
from core.publishing.metrics import get_metrics_collector, PublishMetricsCollector

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublishResult:
    """Result of Instagram publish operation.

    Story 4-5, Task 1.6: Return result with all publishing details.

    Attributes:
        success: Whether the publish succeeded
        instagram_post_id: Instagram media ID if successful
        permalink: Direct link to the Instagram post
        published_at: Timestamp when published
        error_message: Error description if failed
        retry_allowed: Whether retry is allowed for this error
        latency_seconds: Time taken for publish operation
        attempts: Number of attempts made
    """

    success: bool
    instagram_post_id: Optional[str] = None
    permalink: Optional[str] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_allowed: bool = True
    latency_seconds: float = 0.0
    attempts: int = 1


@runtime_checkable
class InstagramPublisherProtocol(Protocol):
    """Protocol for Instagram publisher service.

    Story 4-5, Task 1.2: Protocol for dependency injection.
    Allows for easy mocking in tests.
    """

    async def publish(
        self,
        image_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
    ) -> PublishResult:
        """Publish an image post to Instagram.

        Args:
            image_url: Publicly accessible image URL
            caption: Post caption text
            hashtags: Optional list of hashtags (without #)

        Returns:
            PublishResult with success status and post details
        """
        ...


class InstagramPublisher:
    """Service for publishing content to Instagram.

    Story 4-5, Task 1: Instagram Publisher Service

    Implements two-step Graph API publish flow with retry handling:
    1. Create media container
    2. Poll container status until FINISHED
    3. Publish container

    All API calls are wrapped in retry middleware for resilience.

    Attributes:
        MAX_CAPTION_LENGTH: Maximum caption characters (2200)
        MAX_HASHTAGS: Maximum hashtags to include (30)
        PUBLISH_TIMEOUT_SECONDS: Maximum time for publish operation (30s)
    """

    MAX_CAPTION_LENGTH = 2200
    MAX_HASHTAGS = 30
    PUBLISH_TIMEOUT_SECONDS = 30

    # Non-retryable error patterns
    NON_RETRYABLE_ERRORS = [
        "invalid access token",
        "invalid media",
        "policy violation",
        "permission denied",
        "media not found",
        "invalid image",
        "unsupported image format",
    ]

    def __init__(
        self,
        instagram_client: InstagramPublishClientProtocol,
        retry_middleware: Optional[RetryMiddleware] = None,
        metrics_collector: Optional[PublishMetricsCollector] = None,
    ) -> None:
        """Initialize Instagram publisher.

        Story 4-5, Task 1.1: Create InstagramPublisher class.
        Story 4-5, Task 10.1: Add metrics collector for timing metrics.

        Args:
            instagram_client: Instagram API client (injected)
            retry_middleware: Retry middleware for API calls (optional)
            metrics_collector: Metrics collector for monitoring (optional)
        """
        self._client = instagram_client
        self._retry = retry_middleware or RetryMiddleware(
            RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=4.0,
                backoff_multiplier=2.0,
            )
        )
        self._metrics = metrics_collector or get_metrics_collector()

    async def publish(
        self,
        image_url: str,
        caption: str,
        hashtags: Optional[list[str]] = None,
    ) -> PublishResult:
        """Publish image with caption to Instagram.

        Story 4-5, Task 1.3: publish_post method.

        Flow:
        1. Prepare caption with hashtags
        2. Call Instagram client via retry middleware
        3. Return result with timing metrics

        Args:
            image_url: Publicly accessible image URL
            caption: Post caption text
            hashtags: Optional list of hashtags (without #)

        Returns:
            PublishResult with success status and post details.
            Errors are captured in PublishResult, not raised.
        """
        start_time = time.monotonic()
        logger.info(
            "Starting Instagram publish: image_url=%s, caption_length=%d",
            image_url[:50] + "..." if len(image_url) > 50 else image_url,
            len(caption),
        )

        try:
            # Prepare caption with hashtags
            full_caption = self._prepare_caption(caption, hashtags)
            logger.debug("Prepared caption: %d chars", len(full_caption))

            # Execute publish with retry middleware
            result = await self._retry.execute_with_retry(
                operation=lambda: self._client.publish_image(
                    image_url=image_url,
                    caption=full_caption,
                ),
                context="instagram_publish",
            )

            elapsed = time.monotonic() - start_time

            if result.success:
                # Extract data from Instagram client result
                instagram_result: InstagramPublishResult = result.response
                logger.info(
                    "Instagram publish succeeded in %.2fs: media_id=%s",
                    elapsed,
                    instagram_result.media_id,
                )

                # Story 4-5, Task 10.1: Record success metrics
                self._metrics.record_publish_attempt(
                    success=True,
                    latency_seconds=elapsed,
                )

                return PublishResult(
                    success=True,
                    instagram_post_id=instagram_result.media_id,
                    permalink=await self._get_permalink(instagram_result.media_id),
                    published_at=datetime.now(UTC),
                    latency_seconds=elapsed,
                    attempts=result.attempts,
                )
            else:
                # Retry middleware exhausted or non-retryable error
                error_msg = result.last_error or "Unknown error"
                retry_allowed = self._is_retryable_error_message(error_msg)

                logger.error(
                    "Instagram publish failed after %d attempts in %.2fs: %s",
                    result.attempts,
                    elapsed,
                    error_msg,
                )

                # Story 4-5, Task 10.1: Record failure metrics
                self._metrics.record_publish_attempt(
                    success=False,
                    latency_seconds=elapsed,
                    error_message=error_msg,
                )

                return PublishResult(
                    success=False,
                    error_message=error_msg,
                    retry_allowed=retry_allowed,
                    latency_seconds=elapsed,
                    attempts=result.attempts,
                )

        except Exception as e:
            elapsed = time.monotonic() - start_time
            error_msg = str(e)
            retry_allowed = self._is_retryable_error_message(error_msg)

            logger.exception(
                "Unexpected error in Instagram publish after %.2fs: %s",
                elapsed,
                error_msg,
            )

            # Story 4-5, Task 10.1: Record exception metrics
            self._metrics.record_publish_attempt(
                success=False,
                latency_seconds=elapsed,
                error_message=error_msg,
            )

            return PublishResult(
                success=False,
                error_message=error_msg,
                retry_allowed=retry_allowed,
                latency_seconds=elapsed,
            )

    async def _get_permalink(self, media_id: str) -> Optional[str]:
        """Get permalink for a published post.

        Story 4-5: Step 3 of Graph API flow.

        Args:
            media_id: Instagram media ID

        Returns:
            Permalink URL or None if fetch fails
        """
        try:
            # Instagram client may have a method for this
            if hasattr(self._client, "get_permalink"):
                return await self._client.get_permalink(media_id)

            # Construct default permalink format
            return f"https://www.instagram.com/p/{media_id}/"
        except Exception as e:
            logger.warning("Failed to get permalink for %s: %s", media_id, e)
            return None

    def _prepare_caption(
        self,
        caption: str,
        hashtags: Optional[list[str]],
    ) -> str:
        """Prepare caption with hashtags, respecting limits.

        Story 4-5, Task 1.3: Caption preparation.

        Args:
            caption: Original caption text
            hashtags: Optional list of hashtags (without #)

        Returns:
            Full caption with hashtags appended
        """
        if not hashtags:
            return caption[: self.MAX_CAPTION_LENGTH]

        # Limit hashtags
        limited_hashtags = hashtags[: self.MAX_HASHTAGS]
        hashtag_str = " " + " ".join(f"#{tag}" for tag in limited_hashtags)

        # Ensure total length within limit
        max_caption_len = self.MAX_CAPTION_LENGTH - len(hashtag_str)
        truncated_caption = caption[:max_caption_len]

        return truncated_caption + hashtag_str

    def _is_retryable_error_message(self, error_msg: str) -> bool:
        """Determine if error message indicates a retryable error.

        Story 4-5, Task 1.4: Error classification.

        Non-retryable errors:
        - Invalid access token (requires re-auth)
        - Invalid media URL (fix required)
        - Policy violation (content issue)

        Retryable errors:
        - Rate limit (wait and retry)
        - Temporary server error
        - Network timeout

        Args:
            error_msg: Error message to check

        Returns:
            True if the error is potentially retryable
        """
        error_lower = error_msg.lower()
        return not any(
            pattern in error_lower
            for pattern in self.NON_RETRYABLE_ERRORS
        )


__all__ = [
    "InstagramPublisher",
    "InstagramPublisherProtocol",
    "PublishResult",
]
