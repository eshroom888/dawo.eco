"""Instagram Graph API client for content publishing.

This module provides publishing functionality via the Instagram Graph API.
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

References:
- Instagram Graph API Content Publishing:
  https://developers.facebook.com/docs/instagram-api/guides/content-publishing
- Rate Limits: 25 posts per 24-hour period per account
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

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
    ) -> None:
        """Initialize Instagram publish client.

        Args:
            access_token: Instagram/Facebook access token with publish permissions
            business_account_id: Instagram Business Account ID
            timeout: Request timeout in seconds
            max_poll_attempts: Max attempts to poll container status
            poll_interval: Seconds between status polls

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
