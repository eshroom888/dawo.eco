"""UTM parameter builder for Shopify product links.

This module provides utilities for generating UTM tracking parameters
for product links used in social media content.

Architecture Compliance:
- Pure functions, no external dependencies
- All parameters passed explicitly
- URL-safe encoding
"""

from dataclasses import dataclass
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


@dataclass
class UTMParams:
    """UTM tracking parameters.

    Attributes:
        source: Traffic source (e.g., "instagram", "facebook")
        medium: Marketing medium (e.g., "post", "story", "reel")
        campaign: Campaign name (typically content type)
        content: Content identifier (typically post ID)
        term: Optional keyword term
    """

    source: str = "instagram"
    medium: str = "post"
    campaign: str = ""
    content: str = ""
    term: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for URL encoding, excluding empty values."""
        params = {
            "utm_source": self.source,
            "utm_medium": self.medium,
        }
        if self.campaign:
            params["utm_campaign"] = self.campaign
        if self.content:
            params["utm_content"] = self.content
        if self.term:
            params["utm_term"] = self.term
        return params


def build_utm_url(
    base_url: str,
    content_type: str,
    post_id: str,
    source: str = "instagram",
    medium: str = "post",
) -> str:
    """Build URL with UTM tracking parameters.

    Args:
        base_url: Product URL without UTM params
        content_type: Type of content (e.g., "feed_post", "story", "reel")
        post_id: Unique post identifier for attribution
        source: Traffic source (default: "instagram")
        medium: Marketing medium (default: "post")

    Returns:
        URL with UTM parameters appended

    Example:
        >>> build_utm_url("https://dawo.no/products/lions-mane", "feed_post", "abc123")
        'https://dawo.no/products/lions-mane?utm_source=instagram&utm_medium=post&utm_campaign=feed_post&utm_content=abc123'
    """
    params = UTMParams(
        source=source,
        medium=medium,
        campaign=content_type,
        content=post_id,
    )

    parsed = urlparse(base_url)

    # Preserve existing query params if any
    existing_params = parse_qs(parsed.query)
    # Flatten single-value lists from parse_qs
    existing_flat = {k: v[0] if len(v) == 1 else v for k, v in existing_params.items()}

    # Merge: UTM params override any existing UTM params
    merged = {**existing_flat, **params.to_dict()}

    # Encode and build final URL
    new_query = urlencode(merged, safe="")

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def get_product_url_with_utm(
    product_url: str,
    content_type: str,
    post_id: str,
) -> str:
    """Convenience wrapper for build_utm_url with default Instagram source.

    Args:
        product_url: Product URL from ShopifyProduct
        content_type: Type of content (e.g., "feed_post", "story", "reel")
        post_id: Unique post identifier

    Returns:
        Product URL with UTM parameters
    """
    return build_utm_url(
        base_url=product_url,
        content_type=content_type,
        post_id=post_id,
        source="instagram",
        medium="post",
    )
