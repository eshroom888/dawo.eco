"""Discord webhook client for sending notifications.

This module provides a Discord webhook client that can be injected
into other components like DiscordAlertManager.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design
- Graceful error handling

Enhanced for Epic 4:
- Rich embeds for approval notifications
- Publish notifications with links
- Daily summary embeds
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)


class DiscordRateLimitError(Exception):
    """Raised when Discord rate limit is hit.

    Story 4-6, Task 5.5: Handle Discord-specific rate limit errors.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)
        is_global: Whether this is a global rate limit
    """

    def __init__(
        self,
        message: str,
        retry_after: float = 0,
        is_global: bool = False,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.is_global = is_global


class DiscordAuthError(Exception):
    """Raised when Discord authentication fails.

    Story 4-6, Task 5.5: Handle Discord auth errors (401, 403).
    """

    pass


class EmbedColor(Enum):
    """Standard colors for Discord embeds."""

    SUCCESS = 0x00FF00  # Green
    WARNING = 0xFFAA00  # Orange
    ERROR = 0xFF0000  # Red
    INFO = 0x0099FF  # Blue
    APPROVAL = 0x9B59B6  # Purple
    PUBLISH = 0x2ECC71  # Emerald
    PUBLISH_SUCCESS = 0x4CAF50  # Green (Material Design)
    PUBLISH_FAILED = 0xF44336  # Red (Material Design)
    DAILY_SUMMARY = 0x2196F3  # Blue (Material Design)


@dataclass
class EmbedField:
    """Discord embed field.

    Attributes:
        name: Field title
        value: Field content
        inline: Whether to display inline
    """

    name: str
    value: str
    inline: bool = False

    def to_dict(self) -> dict:
        """Convert to Discord API format."""
        return {
            "name": self.name,
            "value": self.value,
            "inline": self.inline,
        }


@dataclass
class DiscordEmbed:
    """Discord rich embed for notifications.

    Attributes:
        title: Embed title
        description: Main content
        color: Sidebar color (EmbedColor or int)
        fields: List of EmbedField objects
        url: Optional URL for the title
        thumbnail_url: Optional thumbnail image
        footer_text: Optional footer text
        timestamp: Optional ISO timestamp
    """

    title: str
    description: str = ""
    color: int = EmbedColor.INFO.value
    fields: list[EmbedField] = field(default_factory=list)
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    footer_text: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to Discord API format."""
        embed = {
            "title": self.title,
            "color": self.color if isinstance(self.color, int) else self.color.value,
        }

        if self.description:
            embed["description"] = self.description
        if self.url:
            embed["url"] = self.url
        if self.thumbnail_url:
            embed["thumbnail"] = {"url": self.thumbnail_url}
        if self.fields:
            embed["fields"] = [f.to_dict() for f in self.fields]
        if self.footer_text:
            embed["footer"] = {"text": self.footer_text}
        if self.timestamp:
            embed["timestamp"] = self.timestamp

        return embed


@runtime_checkable
class DiscordClientProtocol(Protocol):
    """Protocol defining the Discord client interface.

    Any class implementing this protocol can be used as a Discord client.
    This allows for easy mocking and alternative implementations.
    """

    async def send_webhook(self, message: str) -> bool:
        """Send a message via Discord webhook.

        Args:
            message: The message content to send

        Returns:
            True if sent successfully, False otherwise
        """
        ...

    async def send_embed(self, embed: DiscordEmbed, content: Optional[str] = None) -> bool:
        """Send a rich embed via Discord webhook.

        Args:
            embed: DiscordEmbed object with rich content
            content: Optional plain text to accompany embed

        Returns:
            True if sent successfully, False otherwise
        """
        ...


class DiscordWebhookClient:
    """Discord webhook client for sending messages.

    Implements DiscordClientProtocol for type-safe injection.

    Attributes:
        _webhook_url: The Discord webhook URL
        _timeout: Request timeout in seconds
    """

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
    ) -> None:
        """Initialize Discord webhook client.

        Args:
            webhook_url: Discord webhook URL
            timeout: Request timeout in seconds (default: 10.0)

        Raises:
            ValueError: If webhook_url is empty or invalid
        """
        if not webhook_url or not webhook_url.startswith("http"):
            raise ValueError(
                "webhook_url must be a valid URL starting with http/https"
            )

        self._webhook_url = webhook_url
        self._timeout = timeout
        self._client = httpx.AsyncClient()

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle Discord error responses with specific error types.

        Story 4-6, Task 5.5: Handle Discord-specific error codes.

        Args:
            response: The HTTP response to check

        Raises:
            DiscordRateLimitError: If rate limited (429)
            DiscordAuthError: If auth failed (401, 403)
        """
        status = response.status_code

        # Rate limit handling (429)
        if status == 429:
            retry_after = 0.0
            is_global = False

            # Try to get Retry-After from header
            if "Retry-After" in response.headers:
                try:
                    retry_after = float(response.headers["Retry-After"])
                except ValueError:
                    retry_after = 60.0  # Default to 60 seconds

            # Check if global rate limit
            if "X-RateLimit-Global" in response.headers:
                is_global = response.headers["X-RateLimit-Global"].lower() == "true"

            # Also check response body for retry_after
            try:
                data = response.json()
                if "retry_after" in data:
                    retry_after = float(data["retry_after"])
                if data.get("global", False):
                    is_global = True
            except Exception:
                pass

            logger.warning(
                f"Discord rate limit hit, retry after {retry_after}s (global: {is_global})"
            )
            raise DiscordRateLimitError(
                f"Rate limited, retry after {retry_after}s",
                retry_after=retry_after,
                is_global=is_global,
            )

        # Auth errors (401, 403)
        if status in (401, 403):
            logger.error(f"Discord auth error: {status} - {response.text}")
            raise DiscordAuthError(f"Discord authentication failed: {status}")

    async def send_webhook(self, message: str) -> bool:
        """Send a message via Discord webhook.

        Story 4-6, Task 5.5: Handle Discord-specific error codes.

        Args:
            message: The message content to send

        Returns:
            True if sent successfully, False otherwise

        Raises:
            DiscordRateLimitError: If rate limited (429) - caller can retry after delay
            DiscordAuthError: If authentication failed (401, 403)
        """
        try:
            response = await self._client.post(
                self._webhook_url,
                json={"content": message},
                timeout=self._timeout,
            )

            if response.status_code in (200, 204):
                logger.debug("Discord webhook sent successfully")
                return True

            # Check for Discord-specific errors
            self._handle_error_response(response)

            # Other non-success status
            logger.warning(
                f"Discord webhook returned {response.status_code}: {response.text}"
            )
            return False

        except (DiscordRateLimitError, DiscordAuthError):
            # Re-raise Discord-specific errors for caller handling
            raise
        except httpx.TimeoutException:
            logger.warning("Discord webhook timed out")
            return False
        except httpx.RequestError as e:
            logger.warning(f"Discord webhook request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord webhook: {e}")
            return False

    async def send_embed(
        self,
        embed: DiscordEmbed,
        content: Optional[str] = None,
    ) -> bool:
        """Send a rich embed via Discord webhook.

        Story 4-6, Task 5.5: Handle Discord-specific error codes.

        Args:
            embed: DiscordEmbed object with rich content
            content: Optional plain text to accompany embed

        Returns:
            True if sent successfully, False otherwise

        Raises:
            DiscordRateLimitError: If rate limited (429) - caller can retry after delay
            DiscordAuthError: If authentication failed (401, 403)
        """
        try:
            payload: dict[str, Any] = {"embeds": [embed.to_dict()]}
            if content:
                payload["content"] = content

            response = await self._client.post(
                self._webhook_url,
                json=payload,
                timeout=self._timeout,
            )

            if response.status_code in (200, 204):
                logger.debug("Discord embed sent successfully")
                return True

            # Check for Discord-specific errors
            self._handle_error_response(response)

            # Other non-success status
            logger.warning(
                f"Discord embed returned {response.status_code}: {response.text}"
            )
            return False

        except (DiscordRateLimitError, DiscordAuthError):
            # Re-raise Discord-specific errors for caller handling
            raise
        except httpx.TimeoutException:
            logger.warning("Discord embed timed out")
            return False
        except httpx.RequestError as e:
            logger.warning(f"Discord embed request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord embed: {e}")
            return False

    async def send_approval_notification(
        self,
        pending_count: int,
        high_priority_count: int = 0,
        compliance_warnings: int = 0,
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """Send approval queue notification (Epic 4, Story 4.6).

        Args:
            pending_count: Total items pending approval
            high_priority_count: Items marked as high priority
            compliance_warnings: Items with compliance warnings
            dashboard_url: URL to the approval dashboard

        Returns:
            True if sent successfully, False otherwise
        """
        fields = [
            EmbedField(name="Pending Items", value=str(pending_count), inline=True),
        ]

        if high_priority_count > 0:
            fields.append(
                EmbedField(name="High Priority", value=str(high_priority_count), inline=True)
            )

        if compliance_warnings > 0:
            fields.append(
                EmbedField(
                    name="Compliance Warnings",
                    value=f"⚠️ {compliance_warnings}",
                    inline=True,
                )
            )

        embed = DiscordEmbed(
            title="🔔 DAWO Approval Queue",
            description=f"{pending_count} items ready for review",
            color=EmbedColor.APPROVAL.value,
            fields=fields,
            url=dashboard_url,
            footer_text="DAWO Content Pipeline",
        )

        return await self.send_embed(embed)

    async def send_publish_notification(
        self,
        post_title: str,
        instagram_url: Optional[str] = None,
        publish_time: Optional[datetime] = None,
        caption_excerpt: str = "",
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """Send publish result notification (Epic 4, Story 4.7).

        Args:
            post_title: Title or excerpt of the published post
            instagram_url: URL to the Instagram post if successful
            publish_time: When the post was published
            caption_excerpt: First 100 chars of caption
            success: Whether publish succeeded
            error_message: Error description if failed

        Returns:
            True if sent successfully, False otherwise
        """
        if success:
            fields = []
            if publish_time:
                fields.append(
                    EmbedField(
                        name="Published",
                        value=publish_time.strftime("%Y-%m-%d %H:%M UTC"),
                        inline=True,
                    )
                )

            description = post_title[:200]
            if caption_excerpt:
                description = f"{post_title[:100]}\n\n_{caption_excerpt[:100]}_"

            embed = DiscordEmbed(
                title="✅ Published to Instagram",
                description=description,
                color=EmbedColor.PUBLISH_SUCCESS.value,
                url=instagram_url,
                fields=fields,
                footer_text="DAWO Auto-Publisher",
            )
        else:
            fields = []
            if error_message:
                fields.append(EmbedField(name="Error", value=error_message[:500]))

            embed = DiscordEmbed(
                title="❌ Publish Failed",
                description=post_title[:200],
                color=EmbedColor.PUBLISH_FAILED.value,
                fields=fields,
                footer_text="DAWO Auto-Publisher - Manual retry needed",
            )

        return await self.send_embed(embed)

    async def send_publish_failed_notification(
        self,
        post_title: str,
        error_reason: str,
        error_type: str,
        dashboard_url: str,
        scheduled_time: datetime,
    ) -> bool:
        """Send notification when a publish fails (Story 4.7, AC #3).

        Args:
            post_title: Title/excerpt of the failed post
            error_reason: Human-readable error message
            error_type: Error category (API_ERROR, RATE_LIMIT, etc.)
            dashboard_url: Link to retry in dashboard
            scheduled_time: Original scheduled publish time

        Returns:
            True if sent successfully, False otherwise
        """
        fields = [
            EmbedField(
                name="Error Type",
                value=error_type.replace("_", " ").title(),
                inline=True,
            ),
            EmbedField(
                name="Scheduled Time",
                value=scheduled_time.strftime("%Y-%m-%d %H:%M UTC"),
                inline=True,
            ),
            EmbedField(
                name="Details",
                value=error_reason[:500],
                inline=False,
            ),
            EmbedField(
                name="Action Required",
                value=f"[Retry in Dashboard]({dashboard_url})",
                inline=False,
            ),
        ]

        embed = DiscordEmbed(
            title="❌ Publish Failed",
            description=post_title[:200],
            color=EmbedColor.PUBLISH_FAILED.value,
            fields=fields,
            footer_text="DAWO Auto-Publisher - Manual intervention required",
        )

        return await self.send_embed(embed)

    async def send_batch_publish_notification(
        self,
        posts: list[dict],
    ) -> bool:
        """Send batched notification for multiple publishes (Story 4.7, AC #2).

        Args:
            posts: List of published post details [{title, instagram_url, publish_time}]

        Returns:
            True if sent successfully, False otherwise
        """
        post_count = len(posts)

        # Build post list with links
        post_links = []
        for i, post in enumerate(posts[:10], 1):  # Limit to 10 to avoid embed limits
            title = post.get("title", "Untitled")[:50]
            url = post.get("instagram_url", "")
            if url:
                post_links.append(f"{i}. [{title}]({url})")
            else:
                post_links.append(f"{i}. {title}")

        description = "\n".join(post_links)
        if post_count > 10:
            description += f"\n\n_...and {post_count - 10} more_"

        embed = DiscordEmbed(
            title=f"✅ Published {post_count} Posts",
            description=description,
            color=EmbedColor.PUBLISH_SUCCESS.value,
            footer_text="DAWO Auto-Publisher - Batch notification",
        )

        return await self.send_embed(embed)

    async def send_daily_summary_notification(
        self,
        published_count: int,
        pending_count: int,
        failed_count: int = 0,
        top_post: Optional[dict] = None,
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """Send daily publishing summary notification (Story 4.7, AC #4).

        Args:
            published_count: Posts published today
            pending_count: Posts still pending
            failed_count: Posts that failed to publish
            top_post: Optional top performing post info {title, engagement}
            dashboard_url: URL to the dashboard

        Returns:
            True if sent successfully, False otherwise
        """
        # Determine overall status color
        if failed_count > 0:
            color = EmbedColor.WARNING.value
            status_emoji = "⚠️"
        elif published_count > 0:
            color = EmbedColor.DAILY_SUMMARY.value
            status_emoji = "📊"
        else:
            color = EmbedColor.INFO.value
            status_emoji = "📋"

        fields = [
            EmbedField(name="Published", value=f"✅ {published_count}", inline=True),
            EmbedField(name="Pending", value=f"⏳ {pending_count}", inline=True),
        ]

        if failed_count > 0:
            fields.append(
                EmbedField(name="Failed", value=f"❌ {failed_count}", inline=True)
            )

        if top_post:
            title = top_post.get("title", "")[:50]
            engagement = top_post.get("engagement", 0)
            fields.append(
                EmbedField(
                    name="Top Performer",
                    value=f"🏆 {title} ({engagement} engagements)",
                    inline=False,
                )
            )

        embed = DiscordEmbed(
            title=f"{status_emoji} DAWO Daily Summary",
            description="Today's content publishing results",
            color=color,
            fields=fields,
            url=dashboard_url,
            footer_text="End of day report",
        )

        return await self.send_embed(embed)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "DiscordWebhookClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        try:
            await self.close()
        except Exception as e:
            logger.warning(f"Error closing Discord client: {e}")
