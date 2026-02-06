"""Discord webhook client for sending notifications.

This module provides a Discord webhook client that can be injected
into other components like DiscordAlertManager.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design
- Graceful error handling
"""

import logging
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)


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
