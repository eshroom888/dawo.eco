"""Discord Integration Module.

Provides Discord webhook client for sending notifications and alerts.

Usage:
    from integrations.discord import DiscordWebhookClient

    client = DiscordWebhookClient(webhook_url="https://discord.com/api/webhooks/...")
    await client.send_webhook("Hello from DAWO!")
"""

from integrations.discord.client import DiscordWebhookClient, DiscordClientProtocol

__all__ = [
    "DiscordWebhookClient",
    "DiscordClientProtocol",
]
