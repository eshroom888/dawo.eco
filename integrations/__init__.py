"""DAWO Integrations Module.

Contains external service integrations used by DAWO teams.
All integrations follow the dependency injection pattern.

Note: Imports are lazy to avoid circular imports with teams.dawo.middleware.
Import directly from submodules: `from integrations.shopify.client import ...`
"""


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    # Discord
    if name in ("DiscordWebhookClient", "DiscordClientProtocol", "DiscordEmbed", "EmbedField", "EmbedColor"):
        from integrations.discord import DiscordWebhookClient, DiscordClientProtocol, DiscordEmbed, EmbedField, EmbedColor
        return {"DiscordWebhookClient": DiscordWebhookClient, "DiscordClientProtocol": DiscordClientProtocol,
                "DiscordEmbed": DiscordEmbed, "EmbedField": EmbedField, "EmbedColor": EmbedColor}[name]

    # Instagram (Epic 4)
    if name in ("InstagramPublishClient", "InstagramPublishClientProtocol", "PublishResult", "ContainerStatus", "InstagramPublishError"):
        from integrations.instagram import InstagramPublishClient, InstagramPublishClientProtocol, PublishResult, ContainerStatus, InstagramPublishError
        return {"InstagramPublishClient": InstagramPublishClient, "InstagramPublishClientProtocol": InstagramPublishClientProtocol,
                "PublishResult": PublishResult, "ContainerStatus": ContainerStatus, "InstagramPublishError": InstagramPublishError}[name]

    # Shopify
    if name in ("ShopifyClient", "ShopifyClientProtocol", "ShopifyProduct", "ProductPlaceholder"):
        from integrations.shopify.client import ShopifyClient, ShopifyClientProtocol, ShopifyProduct, ProductPlaceholder
        return {"ShopifyClient": ShopifyClient, "ShopifyClientProtocol": ShopifyClientProtocol,
                "ShopifyProduct": ShopifyProduct, "ProductPlaceholder": ProductPlaceholder}[name]

    # Google Drive
    if name in ("GoogleDriveClient", "GoogleDriveClientProtocol", "DriveAsset", "AssetType"):
        from integrations.google_drive.client import GoogleDriveClient, GoogleDriveClientProtocol, DriveAsset, AssetType
        return {"GoogleDriveClient": GoogleDriveClient, "GoogleDriveClientProtocol": GoogleDriveClientProtocol,
                "DriveAsset": DriveAsset, "AssetType": AssetType}[name]

    # Orshot
    if name in ("OrshotClient", "OrshotClientProtocol", "OrshotTemplate", "GeneratedGraphic"):
        from integrations.orshot.client import OrshotClient, OrshotClientProtocol, OrshotTemplate, GeneratedGraphic
        return {"OrshotClient": OrshotClient, "OrshotClientProtocol": OrshotClientProtocol,
                "OrshotTemplate": OrshotTemplate, "GeneratedGraphic": GeneratedGraphic}[name]

    # Gemini
    if name in ("GeminiImageClient", "GeminiImageClientProtocol", "GeneratedImage", "ImageStyle"):
        from integrations.gemini.client import GeminiImageClient, GeminiImageClientProtocol, GeneratedImage, ImageStyle
        return {"GeminiImageClient": GeminiImageClient, "GeminiImageClientProtocol": GeminiImageClientProtocol,
                "GeneratedImage": GeneratedImage, "ImageStyle": ImageStyle}[name]

    raise AttributeError(f"module 'integrations' has no attribute '{name}'")


__all__ = [
    # Discord
    "DiscordWebhookClient",
    "DiscordClientProtocol",
    "DiscordEmbed",
    "EmbedField",
    "EmbedColor",
    # Instagram (Epic 4)
    "InstagramPublishClient",
    "InstagramPublishClientProtocol",
    "PublishResult",
    "ContainerStatus",
    "InstagramPublishError",
    # Shopify
    "ShopifyClient",
    "ShopifyClientProtocol",
    "ShopifyProduct",
    "ProductPlaceholder",
    # Google Drive
    "GoogleDriveClient",
    "GoogleDriveClientProtocol",
    "DriveAsset",
    "AssetType",
    # Orshot
    "OrshotClient",
    "OrshotClientProtocol",
    "OrshotTemplate",
    "GeneratedGraphic",
    # Gemini (Nano Banana)
    "GeminiImageClient",
    "GeminiImageClientProtocol",
    "GeneratedImage",
    "ImageStyle",
]
