"""Discord alert manager for API error notifications.

This module provides rate-limited Discord alerting for API errors
that occur after retry attempts are exhausted.

Architecture Compliance:
- Discord client is injected via constructor (NEVER connect directly)
- Redis used for rate-limiting cooldowns
- Failures don't propagate - graceful degradation

Usage:
    from integrations.discord import DiscordWebhookClient

    discord_client = DiscordWebhookClient(webhook_url="...")
    redis_client = await get_redis()
    manager = DiscordAlertManager(discord_client, redis_client, cooldown_seconds=300)
    await manager.send_api_error_alert("instagram", "Timeout", 3, True)
"""

import logging
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class DiscordClientProtocol(Protocol):
    """Protocol for Discord client interface (L1 fix)."""

    async def send_webhook(self, message: str) -> bool:
        """Send a message via webhook."""
        ...


@runtime_checkable
class RedisClientProtocol(Protocol):
    """Protocol for Redis client interface (L1 fix)."""

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

    async def setex(self, key: str, seconds: int, value: str) -> None:
        """Set key with expiration."""
        ...


class DiscordAlertManager:
    """Rate-limited Discord alerting for API errors.

    Sends alerts to Discord when external API calls fail after
    all retry attempts. Rate-limits alerts to prevent spam.

    Attributes:
        ALERT_COOLDOWN: Default seconds between alerts (300 = 5 minutes)
    """

    ALERT_COOLDOWN = 300  # 5 minutes per API (default)

    def __init__(
        self,
        discord_client: DiscordClientProtocol,
        redis_client: RedisClientProtocol,
        cooldown_seconds: Optional[int] = None,
    ) -> None:
        """Initialize alert manager with injected clients.

        Args:
            discord_client: Discord webhook client (from integrations/)
            redis_client: Async Redis client for rate-limiting
            cooldown_seconds: Override default cooldown (from config)
        """
        self._discord = discord_client
        self._redis = redis_client
        self._cooldown = cooldown_seconds if cooldown_seconds is not None else self.ALERT_COOLDOWN

    async def send_api_error_alert(
        self,
        api_name: str,
        error: str,
        attempts: int,
        queued_for_retry: bool,
    ) -> bool:
        """Send Discord alert if not rate-limited.

        Graceful degradation: Discord/Redis failures return False,
        they don't raise exceptions.

        Args:
            api_name: Name of the failed API (instagram, discord, orshot, shopify)
            error: Error message from last attempt
            attempts: Number of retry attempts made
            queued_for_retry: Whether operation was queued for later retry

        Returns:
            True if alert was sent, False if rate-limited or failed
        """
        cache_key = f"dawo:alert_cooldown:{api_name}"

        try:
            # Check rate limit
            if await self._redis.exists(cache_key):
                logger.debug(f"Alert for {api_name} is rate-limited, skipping")
                return False

            # Format and send alert
            message = self._format_alert(api_name, error, attempts, queued_for_retry)
            await self._discord.send_webhook(message)

            # Set cooldown (using injected or default value)
            await self._redis.setex(cache_key, self._cooldown, "1")
            logger.info(f"Sent Discord alert for {api_name} API error")
            return True

        except Exception as e:
            # Graceful degradation - don't fail the pipeline for alert errors
            logger.warning(f"Failed to send Discord alert: {e}")
            return False

    def _format_alert(
        self,
        api_name: str,
        error: str,
        attempts: int,
        queued_for_retry: bool,
    ) -> str:
        """Format the alert message with actionable information.

        Args:
            api_name: Name of the failed API
            error: Error message
            attempts: Number of attempts made
            queued_for_retry: Whether operation is queued

        Returns:
            Formatted alert message
        """
        status = "Queued for retry" if queued_for_retry else "Manual intervention needed"
        status_emoji = "✅" if queued_for_retry else "❌"

        return f"""❌ **API Error: {api_name.upper()}**

• **Error:** {error}
• **Attempts:** {attempts}
• **Status:** {status_emoji} {status}

---
_DAWO External API Retry Middleware_"""
