"""Discord Integration Module.

Provides Discord webhook client for sending notifications and alerts.

Usage:
    from integrations.discord import DiscordWebhookClient, DiscordEmbed

    # Simple message
    client = DiscordWebhookClient(webhook_url="https://discord.com/api/webhooks/...")
    await client.send_webhook("Hello from DAWO!")

    # Rich embed (Epic 4)
    embed = DiscordEmbed(
        title="New Content Ready",
        description="5 items pending approval",
        color=EmbedColor.APPROVAL.value,
    )
    await client.send_embed(embed)

    # Convenience methods (Epic 4)
    await client.send_approval_notification(pending_count=5, compliance_warnings=1)
    await client.send_publish_notification("Post title", instagram_url="https://...")
    await client.send_daily_summary(published_count=3, pending_count=2)
"""

from integrations.discord.client import (
    DiscordWebhookClient,
    DiscordClientProtocol,
    DiscordEmbed,
    EmbedField,
    EmbedColor,
)

__all__ = [
    "DiscordWebhookClient",
    "DiscordClientProtocol",
    "DiscordEmbed",
    "EmbedField",
    "EmbedColor",
]
