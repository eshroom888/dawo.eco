"""Short link service for UTM click-through tracking.

Epic 7, Story 7-2: UTM Click-Through Tracking.
Task 3: ShortLinkService — link generation, resolution, and click tracking.

Generates short link codes, resolves them to destination URLs,
and records click events with GDPR-compliant IP hashing.
"""

import asyncio
import hashlib
import logging
import re
import secrets
from datetime import UTC, datetime
from typing import Optional

from integrations.shopify.utm import UTMParams, build_utm_url
from core.analytics.click_analytics import PostClickAnalytics
from core.analytics.utm_models import LinkClick, ShortLink
from core.analytics.utm_repository import UTMRepository
from core.config import UTMConfig

logger = logging.getLogger(__name__)

MAX_COLLISION_RETRIES = 3

# Device type detection patterns (simple regex, no external deps)
_MOBILE_PATTERN = re.compile(r"(?i)(iphone|android|mobile|phone)")
_TABLET_PATTERN = re.compile(r"(?i)(ipad|tablet|kindle)")
_BOT_PATTERN = re.compile(r"(?i)(bot|crawl|spider|slurp|facebook|facebot)")


class ShortLinkService:
    """Service for short link generation, resolution, and click tracking.

    Story 7-2, Task 3.1: Manages the lifecycle of short redirect links.

    Constructor injection: UTMRepository, UTMConfig.

    Attributes:
        _repository: UTM repository for persistence
        _config: UTM configuration
    """

    def __init__(self, repository: UTMRepository, config: UTMConfig) -> None:
        """Initialize service.

        Args:
            repository: UTM repository for data access
            config: UTM configuration (UTMConfig frozen dataclass)
        """
        self._repository = repository
        self._config = config

    async def create_short_link(
        self,
        destination_url: str,
        utm_params: UTMParams,
        post_id: Optional[str] = None,
        source_type: str = "instagram",
    ) -> ShortLink:
        """Create a short link with UTM parameters.

        Task 3.3: Generates a short code, builds destination URL with UTM params,
        and persists the link.

        Task 3.4: Uses secrets.token_urlsafe(6) with collision retry (max 3).

        Args:
            destination_url: Base URL without UTM params
            utm_params: UTM tracking parameters
            post_id: Optional Instagram post ID
            source_type: Source platform (default: "instagram")

        Returns:
            Created ShortLink

        Raises:
            ValueError: If short code collision persists after max retries
        """
        # Build destination URL with UTM params
        full_url = build_utm_url(
            base_url=destination_url,
            content_type=utm_params.campaign,
            post_id=utm_params.content,
            source=utm_params.source,
            medium=utm_params.medium,
        )

        # Generate unique code with collision retry
        code = await self._generate_unique_code()

        link = ShortLink(
            code=code,
            destination_url=full_url,
            utm_source=utm_params.source,
            utm_medium=utm_params.medium,
            utm_campaign=utm_params.campaign,
            utm_content=utm_params.content,
            post_id=post_id,
            source_type=source_type,
        )

        return await self._repository.create_short_link(link)

    async def resolve_and_track(
        self,
        code: str,
        ip: str,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve a short code and record the click.

        Task 3.5: Returns destination_url or None if not found.
        Task 3.6: IP is hashed with SHA-256 (GDPR).
        Task 3.7: Device type parsed from user-agent.

        Click recording is fire-and-forget (AC #4): uses asyncio.create_task()
        so the redirect is not blocked by the database write.

        Args:
            code: Short link code
            ip: Client IP address (will be hashed)
            user_agent: HTTP User-Agent header
            referer: HTTP Referer header

        Returns:
            Destination URL or None if code not found
        """
        link = await self._repository.get_by_code(code)
        if link is None:
            return None

        # Record click with hashed IP (GDPR) -- fire-and-forget (AC #4)
        click = LinkClick(
            short_link_id=link.id,
            clicked_at=datetime.now(UTC),
            ip_hash=self._hash_ip(ip),
            user_agent=user_agent,
            device_type=self._parse_device_type(user_agent),
            referer=referer,
        )
        asyncio.create_task(self._record_click_safe(click))

        return link.destination_url

    async def _record_click_safe(self, click: LinkClick) -> None:
        """Record click in fire-and-forget mode.

        Errors are logged but never raised to avoid blocking the redirect.
        """
        try:
            await self._repository.record_click(click)
        except Exception:
            logger.error(
                "Failed to record click for link %s",
                click.short_link_id,
                exc_info=True,
            )

    async def get_post_click_analytics(self, post_id: str) -> PostClickAnalytics:
        """Get aggregated click analytics for a post.

        Task 3.8: Aggregated stats across all links for a post.

        Args:
            post_id: Instagram post ID

        Returns:
            PostClickAnalytics with aggregated stats
        """
        links = await self._repository.get_by_post_id(post_id)

        if not links:
            return PostClickAnalytics(post_id=post_id)

        total_clicks = 0
        total_unique = 0
        all_by_day = []
        all_device = []

        for link in links:
            if link.id is None:
                continue
            stats = await self._repository.get_click_stats(link.id)
            total_clicks += stats["total_clicks"]
            total_unique += stats["unique_clicks"]
            all_by_day.extend(stats["clicks_by_day"])
            all_device.extend(stats["device_breakdown"])

        return PostClickAnalytics(
            post_id=post_id,
            total_clicks=total_clicks,
            unique_clicks=total_unique,
            clicks_by_day=tuple(all_by_day),
            device_breakdown=tuple(all_device),
        )

    async def _generate_unique_code(self) -> str:
        """Generate a unique short code with collision retry.

        Task 3.4: Uses secrets.token_urlsafe(6) with max 3 retries.

        Returns:
            Unique short code

        Raises:
            ValueError: After 3 consecutive collisions
        """
        for attempt in range(MAX_COLLISION_RETRIES):
            code = secrets.token_urlsafe(6)
            existing = await self._repository.get_by_code(code)
            if existing is None:
                return code
            logger.warning(
                "Short code collision on attempt %d: code=%s",
                attempt + 1,
                code,
            )

        raise ValueError(
            f"Short code collision after {MAX_COLLISION_RETRIES} attempts"
        )

    @staticmethod
    def _hash_ip(ip: str) -> str:
        """Hash an IP address with SHA-256.

        Task 3.6: NEVER store raw IP addresses (GDPR).

        Args:
            ip: Raw IP address

        Returns:
            SHA-256 hex digest (64 characters)
        """
        return hashlib.sha256(ip.encode()).hexdigest()

    @staticmethod
    def _parse_device_type(user_agent: Optional[str]) -> Optional[str]:
        """Parse device type from user-agent string.

        Task 3.7: Simple regex categorization (no external deps).

        Args:
            user_agent: HTTP User-Agent header

        Returns:
            "mobile", "tablet", "desktop", "bot", or None
        """
        if not user_agent:
            return None

        if _BOT_PATTERN.search(user_agent):
            return "bot"
        if _TABLET_PATTERN.search(user_agent):
            return "tablet"
        if _MOBILE_PATTERN.search(user_agent):
            return "mobile"

        # Default to desktop if none of the above match
        return "desktop"


__all__ = [
    "ShortLinkService",
]
