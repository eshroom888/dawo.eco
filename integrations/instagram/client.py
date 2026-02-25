"""Instagram Graph API client for content publishing and insights.

This module provides publishing and insights functionality via the Instagram Graph API.
Uses a two-step container-based approach: create container -> poll status -> publish.

Architecture Compliance:
- Configuration injected via constructor (NEVER connect directly)
- Async-first design with polling for container status
- Graceful error handling with retries
- All methods return typed results

Usage:
    client = InstagramPublishClient(
        access_token="...",
        business_account_id="...",
    )
    result = await client.publish_image(
        image_url="https://...",
        caption="Post caption with #hashtags",
    )
    if result.success:
        print(f"Published: {result.media_id}")

    # Story 7-1: Collect engagement metrics
    insights = await client.get_media_insights(result.media_id)
    if insights.success:
        print(f"Likes: {insights.likes}, Reach: {insights.reach}")

References:
- Instagram Graph API Content Publishing:
  https://developers.facebook.com/docs/instagram-api/guides/content-publishing
- Instagram Graph API Insights:
  https://developers.facebook.com/docs/instagram-api/reference/ig-media/insights
- Rate Limits: 25 posts per 24-hour period per account
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Instagram media container status codes."""

    EXPIRED = "EXPIRED"
    ERROR = "ERROR"
    FINISHED = "FINISHED"
    IN_PROGRESS = "IN_PROGRESS"
    PUBLISHED = "PUBLISHED"


@dataclass(frozen=True)
class InstagramComment:
    """A single Instagram comment.

    Story 7-4, Task 3.1: Frozen dataclass for comment data.

    Attributes:
        comment_id: Instagram comment ID
        text: Comment text content
        username: Author username
        timestamp: When the comment was posted
    """

    comment_id: str
    text: str
    username: str
    timestamp: datetime


@dataclass(frozen=True)
class PublishResult:
    """Result of an Instagram publish operation.

    Attributes:
        success: Whether the publish succeeded
        media_id: Instagram media ID if successful
        container_id: Container ID used for publishing
        error_message: Error description if failed
        error_code: Instagram error code if failed
    """

    success: bool
    media_id: Optional[str] = None
    container_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[int] = None


@dataclass(frozen=True)
class MediaInsightsResult:
    """Result of an Instagram media insights collection.

    Story 7-1, Task 3.5: Structured result instead of raw dict.

    Stores cumulative lifetime values from the Instagram Insights API.
    Reel-specific fields (plays, avg_watch_time_ms) are None for image posts.

    Attributes:
        success: Whether the insights collection succeeded
        media_id: Instagram media ID
        impressions: Total number of times the post was displayed
        reach: Number of unique accounts that saw the post
        likes: Number of likes
        comments: Number of comments
        saved: Number of saves
        shares: Number of shares
        total_interactions: Sum of all engagement actions
        plays: Total plays (reels/video only)
        avg_watch_time_ms: Average watch time in ms (reels/video only)
        raw_response: Raw API response for debugging
        error_message: Error description if failed
    """

    success: bool
    media_id: str = ""
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    saved: int = 0
    shares: int = 0
    total_interactions: int = 0
    plays: Optional[int] = None
    avg_watch_time_ms: Optional[int] = None
    raw_response: Optional[dict] = field(default=None, repr=False)
    error_message: Optional[str] = None


# Image post metrics (Graph API v19.0+, replacing deprecated 'engagement')
IMAGE_METRICS = (
    "impressions,reach,likes,comments,saved,shares,total_interactions"
)

# Additional reel/video metrics
REEL_METRICS = (
    "ig_reels_aggregated_all_plays_count,ig_reels_avg_watch_time"
)


class InstagramPublishError(Exception):
    """Instagram publishing error with API details."""

    def __init__(
        self,
        message: str,
        error_code: Optional[int] = None,
        error_subcode: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.error_subcode = error_subcode


@runtime_checkable
class InstagramPublishClientProtocol(Protocol):
    """Protocol defining the Instagram publish client interface.

    Any class implementing this protocol can be used as an Instagram client.
    This allows for easy mocking and alternative implementations.
    """

    async def publish_image(
        self,
        image_url: str,
        caption: str,
        location_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish a single image post to Instagram.

        Args:
            image_url: Public URL to the image (must be accessible by Instagram)
            caption: Post caption including hashtags
            location_id: Optional Facebook Page location ID

        Returns:
            PublishResult with media_id if successful
        """
        ...

    async def get_container_status(
        self,
        container_id: str,
    ) -> ContainerStatus:
        """Get the status of a media container.

        Args:
            container_id: The container ID to check

        Returns:
            ContainerStatus enum value
        """
        ...

    async def get_permalink(
        self,
        media_id: str,
    ) -> str:
        """Get the permalink for a published post.

        Story 4-5, Task 2.4: Get permalink for tracking.

        Args:
            media_id: Instagram media ID

        Returns:
            Permalink URL for the post
        """
        ...

    async def get_media_insights(
        self,
        media_id: str,
        media_type: Optional[str] = None,
    ) -> MediaInsightsResult:
        """Get engagement metrics for a published post.

        Story 7-1, Task 3.3: Protocol method for insights collection.

        Args:
            media_id: Instagram media ID
            media_type: Media type (IMAGE, VIDEO, CAROUSEL_ALBUM) for
                        conditional reel metrics

        Returns:
            MediaInsightsResult with engagement metrics
        """
        ...

    async def get_comments(
        self,
        media_id: str,
        limit: int = 100,
    ) -> list[InstagramComment]:
        """Get comments for a published post.

        Story 7-4, Task 3.1: Protocol method for comment retrieval.

        Args:
            media_id: Instagram media ID
            limit: Maximum comments to retrieve

        Returns:
            List of InstagramComment objects
        """
        ...


class InstagramPublishClient:
    """Instagram Graph API client for publishing content.

    Implements two-step container-based publishing:
    1. Create media container with image URL and caption
    2. Poll container status until FINISHED
    3. Publish container to create the post

    Rate Limits:
    - 25 posts per 24-hour rolling window
    - Container creation is rate limited by overall API calls

    Attributes:
        GRAPH_API_BASE: Base URL for Graph API
        DEFAULT_TIMEOUT: Request timeout in seconds
        MAX_POLL_ATTEMPTS: Maximum container status polls
        POLL_INTERVAL: Seconds between status polls
    """

    GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
    DEFAULT_TIMEOUT = 30.0
    MAX_POLL_ATTEMPTS = 30
    POLL_INTERVAL = 2.0

    def __init__(
        self,
        access_token: str,
        business_account_id: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_poll_attempts: int = MAX_POLL_ATTEMPTS,
        poll_interval: float = POLL_INTERVAL,
        rate_limit_tracker: Any = None,
    ) -> None:
        """Initialize Instagram publish client.

        Args:
            access_token: Instagram/Facebook access token with publish permissions
            business_account_id: Instagram Business Account ID
            timeout: Request timeout in seconds
            max_poll_attempts: Max attempts to poll container status
            poll_interval: Seconds between status polls
            rate_limit_tracker: Optional rate limit tracker (duck-typed,
                must have check_and_use(count) method). Story 7-1 Task 3.4.

        Raises:
            ValueError: If access_token or business_account_id is empty
        """
        if not access_token:
            raise ValueError("access_token is required")
        if not business_account_id:
            raise ValueError("business_account_id is required")

        self._access_token = access_token
        self._business_account_id = business_account_id
        self._timeout = timeout
        self._max_poll_attempts = max_poll_attempts
        self._poll_interval = poll_interval
        self._client = httpx.AsyncClient()
        self._rate_limit_tracker = rate_limit_tracker

    async def publish_image(
        self,
        image_url: str,
        caption: str,
        location_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish a single image post to Instagram.

        Workflow:
        1. Create media container
        2. Poll until container status is FINISHED
        3. Publish container

        Args:
            image_url: Public URL to the image (Instagram must be able to fetch it)
            caption: Post caption including hashtags (max 2200 chars)
            location_id: Optional Facebook Page location ID for tagging

        Returns:
            PublishResult with success status and media_id
        """
        try:
            # Step 1: Create media container
            container_id = await self._create_container(
                image_url=image_url,
                caption=caption,
                location_id=location_id,
            )
            logger.info(f"Created Instagram container: {container_id}")

            # Step 2: Poll container status
            status = await self._wait_for_container(container_id)
            if status != ContainerStatus.FINISHED:
                return PublishResult(
                    success=False,
                    container_id=container_id,
                    error_message=f"Container status: {status.value}",
                )

            # Step 3: Publish container
            media_id = await self._publish_container(container_id)
            logger.info(f"Published Instagram post: {media_id}")

            return PublishResult(
                success=True,
                media_id=media_id,
                container_id=container_id,
            )

        except InstagramPublishError as e:
            logger.error(f"Instagram publish failed: {e}")
            return PublishResult(
                success=False,
                error_message=str(e),
                error_code=e.error_code,
            )
        except httpx.TimeoutException:
            logger.error("Instagram API request timed out")
            return PublishResult(
                success=False,
                error_message="Request timed out",
            )
        except Exception as e:
            logger.error(f"Unexpected Instagram publish error: {e}")
            return PublishResult(
                success=False,
                error_message=str(e),
            )

    async def get_container_status(
        self,
        container_id: str,
    ) -> ContainerStatus:
        """Get the status of a media container.

        Args:
            container_id: The container ID to check

        Returns:
            ContainerStatus enum value

        Raises:
            InstagramPublishError: If the API request fails
        """
        url = f"{self.GRAPH_API_BASE}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self._access_token,
        }

        response = await self._client.get(
            url,
            params=params,
            timeout=self._timeout,
        )

        data = response.json()
        self._check_error(data)

        status_code = data.get("status_code", "IN_PROGRESS")
        return ContainerStatus(status_code)

    async def _create_container(
        self,
        image_url: str,
        caption: str,
        location_id: Optional[str] = None,
    ) -> str:
        """Create a media container for the image.

        Args:
            image_url: Public URL to the image
            caption: Post caption
            location_id: Optional location tag

        Returns:
            Container ID

        Raises:
            InstagramPublishError: If container creation fails
        """
        url = f"{self.GRAPH_API_BASE}/{self._business_account_id}/media"

        data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self._access_token,
        }

        if location_id:
            data["location_id"] = location_id

        response = await self._client.post(
            url,
            data=data,
            timeout=self._timeout,
        )

        result = response.json()
        self._check_error(result)

        container_id = result.get("id")
        if not container_id:
            raise InstagramPublishError("No container ID in response")

        return container_id

    async def _wait_for_container(
        self,
        container_id: str,
    ) -> ContainerStatus:
        """Poll container status until FINISHED or error.

        Args:
            container_id: Container to poll

        Returns:
            Final ContainerStatus
        """
        for attempt in range(self._max_poll_attempts):
            status = await self.get_container_status(container_id)

            if status == ContainerStatus.FINISHED:
                return status

            if status in (ContainerStatus.ERROR, ContainerStatus.EXPIRED):
                logger.error(f"Container {container_id} failed: {status.value}")
                return status

            # Still IN_PROGRESS, wait and retry
            logger.debug(f"Container {container_id} status: {status.value}, polling...")
            await asyncio.sleep(self._poll_interval)

        logger.warning(f"Container {container_id} polling timed out")
        return ContainerStatus.IN_PROGRESS

    async def _publish_container(
        self,
        container_id: str,
    ) -> str:
        """Publish a finished container to Instagram.

        Args:
            container_id: Container ID with status FINISHED

        Returns:
            Published media ID

        Raises:
            InstagramPublishError: If publish fails
        """
        url = f"{self.GRAPH_API_BASE}/{self._business_account_id}/media_publish"

        data = {
            "creation_id": container_id,
            "access_token": self._access_token,
        }

        response = await self._client.post(
            url,
            data=data,
            timeout=self._timeout,
        )

        result = response.json()
        self._check_error(result)

        media_id = result.get("id")
        if not media_id:
            raise InstagramPublishError("No media ID in publish response")

        return media_id

    async def get_permalink(
        self,
        media_id: str,
    ) -> str:
        """Get the permalink for a published post.

        Story 4-5, Task 2.4: Get permalink for tracking.

        Args:
            media_id: Instagram media ID

        Returns:
            Permalink URL for the post

        Raises:
            InstagramPublishError: If API request fails
        """
        url = f"{self.GRAPH_API_BASE}/{media_id}"
        params = {
            "fields": "permalink",
            "access_token": self._access_token,
        }

        response = await self._client.get(
            url,
            params=params,
            timeout=self._timeout,
        )

        data = response.json()
        self._check_error(data)

        permalink = data.get("permalink")
        if not permalink:
            # Fallback to constructed URL
            return f"https://www.instagram.com/p/{media_id}/"

        return permalink

    async def get_media_insights(
        self,
        media_id: str,
        media_type: Optional[str] = None,
    ) -> MediaInsightsResult:
        """Get engagement metrics for a published post.

        Story 7-1: Updated to use non-deprecated metrics and return
        structured MediaInsightsResult instead of raw dict.

        Replaces deprecated 'engagement' metric with 'total_interactions'.
        Conditionally requests reel-specific metrics for VIDEO media type.

        Args:
            media_id: Instagram media ID
            media_type: Media type (IMAGE, VIDEO, CAROUSEL_ALBUM).
                        If VIDEO, includes reel-specific metrics.

        Returns:
            MediaInsightsResult with engagement metrics
        """
        # Task 3.4: Count against shared rate limit tracker
        if self._rate_limit_tracker is not None:
            self._rate_limit_tracker.check_and_use(1)

        # Task 3.1: Use non-deprecated metric list
        metrics = IMAGE_METRICS
        # Task 3.2: Add reel-specific metrics for video content
        if media_type and media_type.upper() == "VIDEO":
            metrics = f"{metrics},{REEL_METRICS}"

        url = f"{self.GRAPH_API_BASE}/{media_id}/insights"
        params = {
            "metric": metrics,
            "access_token": self._access_token,
        }

        try:
            response = await self._client.get(
                url,
                params=params,
                timeout=self._timeout,
            )

            data = response.json()
            self._check_error(data)

            # Parse insights into a dict for structured result construction
            parsed: dict[str, int] = {}
            for item in data.get("data", []):
                name = item.get("name")
                values = item.get("values", [])
                if values:
                    parsed[name] = values[0].get("value", 0)

            return MediaInsightsResult(
                success=True,
                media_id=media_id,
                impressions=parsed.get("impressions", 0),
                reach=parsed.get("reach", 0),
                likes=parsed.get("likes", 0),
                comments=parsed.get("comments", 0),
                saved=parsed.get("saved", 0),
                shares=parsed.get("shares", 0),
                total_interactions=parsed.get("total_interactions", 0),
                plays=parsed.get("ig_reels_aggregated_all_plays_count"),
                avg_watch_time_ms=parsed.get("ig_reels_avg_watch_time"),
                raw_response=data,
            )

        except InstagramPublishError as e:
            logger.warning("Failed to get media insights for %s: %s", media_id, e)
            return MediaInsightsResult(
                success=False,
                media_id=media_id,
                error_message=str(e),
            )
        except Exception as e:
            logger.warning("Failed to get media insights for %s: %s", media_id, e)
            return MediaInsightsResult(
                success=False,
                media_id=media_id,
                error_message=str(e),
            )

    async def get_comments(
        self,
        media_id: str,
        limit: int = 100,
    ) -> list[InstagramComment]:
        """Get comments for a published post.

        Story 7-4, Task 3.1: Fetch comments with cursor-based pagination.
        Shares the 200 req/hour rate limit budget with metrics collection.

        Args:
            media_id: Instagram media ID
            limit: Maximum comments to retrieve (default 100)

        Returns:
            List of InstagramComment objects, up to limit
        """
        if self._rate_limit_tracker is not None:
            self._rate_limit_tracker.check_and_use(1)

        comments: list[InstagramComment] = []
        url = f"{self.GRAPH_API_BASE}/{media_id}/comments"
        params: dict[str, Any] = {
            "fields": "id,text,timestamp,username",
            "limit": min(limit, 100),
            "access_token": self._access_token,
        }

        try:
            while len(comments) < limit:
                response = await self._client.get(
                    url,
                    params=params,
                    timeout=self._timeout,
                )
                data = response.json()
                self._check_error(data)

                for item in data.get("data", []):
                    if len(comments) >= limit:
                        break
                    comments.append(
                        InstagramComment(
                            comment_id=item["id"],
                            text=item.get("text", ""),
                            username=item.get("username", ""),
                            timestamp=datetime.fromisoformat(
                                item["timestamp"].replace("Z", "+00:00")
                            )
                            if "timestamp" in item
                            else datetime.now(UTC),
                        )
                    )

                # Cursor-based pagination
                paging = data.get("paging", {})
                cursors = paging.get("cursors", {})
                after = cursors.get("after")
                if not after or not paging.get("next"):
                    break

                params["after"] = after

        except InstagramPublishError as e:
            logger.warning("Failed to get comments for %s: %s", media_id, e)
        except Exception as e:
            logger.warning("Failed to get comments for %s: %s", media_id, e)

        return comments

    def _check_error(self, data: dict) -> None:
        """Check API response for errors.

        Args:
            data: JSON response from API

        Raises:
            InstagramPublishError: If error found in response
        """
        if "error" in data:
            error = data["error"]
            message = error.get("message", "Unknown error")
            code = error.get("code")
            subcode = error.get("error_subcode")
            raise InstagramPublishError(message, code, subcode)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "InstagramPublishClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
