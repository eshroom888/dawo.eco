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
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)


class EmbedColor(Enum):
    """Standard colors for Discord embeds."""

    SUCCESS = 0x00FF00  # Green
    WARNING = 0xFFAA00  # Orange
    ERROR = 0xFF0000  # Red
    INFO = 0x0099FF  # Blue
    APPROVAL = 0x9B59B6  # Purple
    PUBLISH = 0x2ECC71  # Emerald


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

    async def send_webhook(self, message: str) -> bool:
        """Send a message via Discord webhook.

        Args:
            message: The message content to send

        Returns:
            True if sent successfully, False otherwise
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
            else:
                logger.warning(
                    f"Discord webhook returned {response.status_code}: {response.text}"
                )
                return False

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

        Args:
            embed: DiscordEmbed object with rich content
            content: Optional plain text to accompany embed

        Returns:
            True if sent successfully, False otherwise
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
            else:
                logger.warning(
                    f"Discord embed returned {response.status_code}: {response.text}"
                )
                return False

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
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """Send publish result notification (Epic 4, Story 4.7).

        Args:
            post_title: Title or excerpt of the published post
            instagram_url: URL to the Instagram post if successful
            success: Whether publish succeeded
            error_message: Error description if failed

        Returns:
            True if sent successfully, False otherwise
        """
        if success:
            embed = DiscordEmbed(
                title="✅ Published to Instagram",
                description=post_title[:200],
                color=EmbedColor.SUCCESS.value,
                url=instagram_url,
                footer_text="DAWO Auto-Publisher",
            )
        else:
            fields = []
            if error_message:
                fields.append(EmbedField(name="Error", value=error_message[:500]))

            embed = DiscordEmbed(
                title="❌ Publish Failed",
                description=post_title[:200],
                color=EmbedColor.ERROR.value,
                fields=fields,
                footer_text="DAWO Auto-Publisher - Manual retry needed",
            )

        return await self.send_embed(embed)

    async def send_daily_summary(
        self,
        published_count: int,
        pending_count: int,
        failed_count: int = 0,
        dashboard_url: Optional[str] = None,
    ) -> bool:
        """Send daily publishing summary (Epic 4, Story 4.7).

        Args:
            published_count: Posts published today
            pending_count: Posts still pending
            failed_count: Posts that failed to publish
            dashboard_url: URL to the dashboard

        Returns:
            True if sent successfully, False otherwise
        """
        # Determine overall status color
        if failed_count > 0:
            color = EmbedColor.WARNING.value
            status_emoji = "⚠️"
        elif published_count > 0:
            color = EmbedColor.SUCCESS.value
            status_emoji = "✅"
        else:
            color = EmbedColor.INFO.value
            status_emoji = "📊"

        fields = [
            EmbedField(name="Published", value=f"✅ {published_count}", inline=True),
            EmbedField(name="Pending", value=f"⏳ {pending_count}", inline=True),
        ]

        if failed_count > 0:
            fields.append(
                EmbedField(name="Failed", value=f"❌ {failed_count}", inline=True)
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
