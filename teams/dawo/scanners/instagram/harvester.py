"""Instagram Harvester - enriches raw posts with full metadata.

Implements the harvest stage of the Harvester Framework:
    Scanner -> [Harvester] -> ThemeExtractor -> ClaimDetector -> Transformer -> Validator -> Publisher -> Research Pool

The InstagramHarvester:
    1. Takes raw posts from scanner
    2. Fetches full caption and engagement metrics
    3. Extracts hashtags from caption
    4. Returns HarvestedPost objects with complete metadata

CRITICAL: Does NOT download or store images/videos (privacy/copyright compliance).

Registration: team_spec.py as RegisteredService

Usage:
    # Created by Team Builder with injected dependencies
    harvester = InstagramHarvester(client)

    # Execute harvest stage
    harvested = await harvester.harvest(raw_posts)
    # harvested contains HarvestedPost objects
"""

import logging
from typing import Optional

from .schemas import RawInstagramPost, HarvestedPost
from .tools import InstagramClient, InstagramAPIError, extract_hashtags


# Module logger
logger = logging.getLogger(__name__)


class HarvesterError(Exception):
    """Exception raised for harvester-level errors.

    Attributes:
        message: Error description
        partial_results: Any posts harvested before error
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class InstagramHarvester:
    """Instagram Harvester - enriches raw posts with full metadata.

    Implements the harvest stage of the Harvester Framework pipeline.
    Takes raw posts from scanner and fetches complete metadata including
    full caption, engagement metrics, and account information.

    CRITICAL: Does NOT store images or videos - text and metadata only.
    This is intentional for privacy/copyright compliance with Meta's ToS.

    Features:
        - Full caption retrieval
        - Engagement metrics (likes, comments)
        - Hashtag extraction
        - Account metadata
        - Rate limit aware

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _client: Instagram API client for fetching details
    """

    def __init__(self, client: InstagramClient):
        """Initialize harvester with injected dependencies.

        Args:
            client: Instagram API client with credentials
        """
        self._client = client

    async def harvest(
        self,
        raw_posts: list[RawInstagramPost],
    ) -> list[HarvestedPost]:
        """Harvest full details for raw posts.

        Takes raw posts from scanner and enriches them with
        complete metadata from the Instagram API.

        Args:
            raw_posts: List of raw posts from scanner

        Returns:
            List of HarvestedPost objects with full metadata

        Note:
            - Continues on individual post failures
            - Logs errors but doesn't raise for partial failures
        """
        logger.info("Starting harvest for %d posts", len(raw_posts))

        harvested: list[HarvestedPost] = []
        failed_count = 0

        for raw_post in raw_posts:
            try:
                post = await self._harvest_post(raw_post)
                if post:
                    harvested.append(post)
            except InstagramAPIError as e:
                logger.warning("Failed to harvest post %s: %s", raw_post.media_id, e)
                failed_count += 1
                # Continue with remaining posts
            except Exception as e:
                logger.error("Unexpected error harvesting post %s: %s", raw_post.media_id, e)
                failed_count += 1
                # Continue with remaining posts

        logger.info(
            "Harvest complete: %d successful, %d failed", len(harvested), failed_count
        )

        return harvested

    async def _harvest_post(
        self,
        raw_post: RawInstagramPost,
    ) -> Optional[HarvestedPost]:
        """Harvest full details for a single post.

        Args:
            raw_post: Raw post from scanner

        Returns:
            HarvestedPost with full metadata, or None if failed
        """
        try:
            # Fetch full media details
            details = await self._client.get_media_details(raw_post.media_id)

            # Extract hashtags from caption
            caption = details.get("caption", raw_post.caption) or ""
            hashtags = extract_hashtags(caption)

            # Build harvested post
            return HarvestedPost(
                media_id=raw_post.media_id,
                permalink=details.get("permalink", raw_post.permalink),
                caption=caption,
                hashtags=hashtags,
                likes=details.get("like_count", 0),
                comments=details.get("comments_count", 0),
                media_type=details.get("media_type", raw_post.media_type),
                account_name=details.get("username", ""),
                account_type="business",  # Assumed - only business accounts accessible via API
                timestamp=raw_post.timestamp,
                is_competitor=raw_post.is_competitor,
                hashtag_source=raw_post.hashtag_source,
            )

        except InstagramAPIError:
            # Re-raise API errors for caller to handle
            raise
        except Exception as e:
            logger.error("Error parsing post details for %s: %s", raw_post.media_id, e)
            return None

    async def harvest_single(
        self,
        raw_post: RawInstagramPost,
    ) -> Optional[HarvestedPost]:
        """Harvest a single post - convenience method.

        Args:
            raw_post: Raw post to harvest

        Returns:
            HarvestedPost or None if failed
        """
        return await self._harvest_post(raw_post)
