"""UTM integration orchestrator.

Epic 7, Story 7-2: UTM Click-Through Tracking.
Task 6.2: Orchestrates UTMParams + ShortLinkService to generate
post short links with proper UTM parameters.

This does NOT modify the caption generator -- short link generation
is a standalone service callable from anywhere.
"""

import logging

from integrations.shopify.utm import UTMParams
from core.analytics.utm_models import ShortLink
from core.analytics.utm_service import ShortLinkService

logger = logging.getLogger(__name__)


async def generate_post_short_link(
    service: ShortLinkService,
    post_id: str,
    destination_url: str,
    content_type: str,
    source_type: str = "instagram",
) -> ShortLink:
    """Generate a short link for a post with UTM tracking parameters.

    Task 6.2: Orchestrates UTMParams construction + ShortLinkService call.

    Args:
        service: ShortLinkService for link creation
        post_id: Instagram post ID
        destination_url: Product/landing page URL
        content_type: Content type (e.g., "feed_post", "story", "reel")
        source_type: Source platform (default: "instagram")

    Returns:
        Created ShortLink with UTM params
    """
    utm_params = UTMParams(
        source="instagram",
        medium="post",
        campaign=content_type,
        content=post_id,
    )

    link = await service.create_short_link(
        destination_url=destination_url,
        utm_params=utm_params,
        post_id=post_id,
        source_type=source_type,
    )

    logger.info(
        "Generated short link for post %s: code=%s",
        post_id,
        link.code,
    )
    return link


__all__ = [
    "generate_post_short_link",
]
