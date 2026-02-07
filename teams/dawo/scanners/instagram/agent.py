"""Instagram Trend Scanner Agent.

Main scanner class implementing the scan stage of the Harvester Framework:
    [Scanner] -> Harvester -> ThemeExtractor -> ClaimDetector -> Transformer -> Validator -> Publisher -> Research Pool

The InstagramScanner discovers research content from Instagram by:
    1. Searching configured hashtags for recent posts
    2. Monitoring configured competitor accounts
    3. Filtering by recency (last 24 hours by default)
    4. Deduplicating by media ID

Registration: team_spec.py with tier="scan" (maps to fast model at runtime)

Usage:
    # Created by Team Builder with injected dependencies
    scanner = InstagramScanner(config, client)

    # Execute scan stage
    result = await scanner.scan()
    # result.posts contains RawInstagramPost objects
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from .config import InstagramScannerConfig
from .schemas import RawInstagramPost, ScanResult, ScanStatistics
from .tools import InstagramClient, InstagramAPIError, InstagramScanError


# Module logger
logger = logging.getLogger(__name__)


class InstagramScanner:
    """Instagram Trend Scanner - discovers content from Instagram.

    Implements the scan stage of the Harvester Framework pipeline.
    Searches Instagram for posts via hashtags and competitor accounts,
    then filters by recency.

    Features:
        - Multi-hashtag search
        - Competitor account monitoring
        - Time-based filtering (configurable hours back)
        - Deduplication by media ID

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _config: Scanner configuration (hashtags, competitors, filters)
        _client: Instagram API client for making requests
    """

    def __init__(
        self,
        config: InstagramScannerConfig,
        client: InstagramClient,
    ):
        """Initialize scanner with injected dependencies.

        Args:
            config: Scanner configuration from Team Builder
            client: Instagram API client with credentials
        """
        self._config = config
        self._client = client

    async def scan(self) -> ScanResult:
        """Execute the scan stage - discover Instagram posts.

        Iterates through configured hashtags and competitor accounts,
        collecting posts that meet the filtering criteria.

        Returns:
            ScanResult with discovered posts and statistics

        Raises:
            InstagramScanError: If critical error prevents scanning
        """
        logger.info(
            "Starting Instagram scan: %d hashtags, %d competitors, hours_back=%d",
            len(self._config.hashtags),
            len(self._config.competitor_accounts),
            self._config.hours_back,
        )

        stats = ScanStatistics()
        all_posts: dict[str, RawInstagramPost] = {}  # Keyed by media_id for deduplication
        errors: list[str] = []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self._config.hours_back)

        # Search hashtags
        for hashtag in self._config.hashtags:
            stats.hashtags_searched += 1

            try:
                posts = await self._search_hashtag(hashtag, cutoff_time)
                stats.total_posts_found += len(posts)

                # Filter by time
                filtered = [p for p in posts if p.timestamp >= cutoff_time]
                stats.posts_after_filter += len(filtered)

                # Deduplicate by media ID
                before_count = len(all_posts)
                for post in filtered:
                    all_posts[post.media_id] = post
                stats.duplicates_removed += before_count + len(filtered) - len(all_posts)

            except InstagramAPIError as e:
                error_msg = f"Failed to search hashtag '#{hashtag}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with other hashtags

        # Monitor competitor accounts
        for account in self._config.competitor_accounts:
            stats.accounts_monitored += 1

            try:
                posts = await self._get_competitor_posts(account, cutoff_time)
                stats.total_posts_found += len(posts)

                # Filter by time
                filtered = [p for p in posts if p.timestamp >= cutoff_time]
                stats.posts_after_filter += len(filtered)

                # Deduplicate by media ID
                before_count = len(all_posts)
                for post in filtered:
                    all_posts[post.media_id] = post
                stats.duplicates_removed += before_count + len(filtered) - len(all_posts)

            except InstagramAPIError as e:
                error_msg = f"Failed to get posts from '@{account}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with other accounts

        logger.info(
            "Scan complete: %d posts found, %d after filtering, %d unique",
            stats.total_posts_found,
            stats.posts_after_filter,
            len(all_posts),
        )

        return ScanResult(
            posts=list(all_posts.values()),
            statistics=stats,
            errors=errors,
        )

    async def _search_hashtag(
        self,
        hashtag: str,
        cutoff_time: datetime,
    ) -> list[RawInstagramPost]:
        """Search Instagram for hashtag and convert to schema.

        Args:
            hashtag: Hashtag to search (without #)
            cutoff_time: Only posts after this time

        Returns:
            List of RawInstagramPost objects
        """
        raw_results = await self._client.search_hashtag(
            hashtag=hashtag,
            limit=self._config.max_posts_per_hashtag,
        )

        posts = []
        for result in raw_results:
            try:
                post = self._parse_api_result(result, hashtag_source=hashtag)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning("Failed to parse post result: %s", e)
                continue

        return posts

    async def _get_competitor_posts(
        self,
        username: str,
        cutoff_time: datetime,
    ) -> list[RawInstagramPost]:
        """Get posts from competitor account.

        Args:
            username: Instagram username (without @)
            cutoff_time: Only posts after this time

        Returns:
            List of RawInstagramPost objects marked as competitor content
        """
        raw_results = await self._client.get_user_media(
            username=username,
            limit=self._config.max_posts_per_account,
        )

        posts = []
        for result in raw_results:
            try:
                post = self._parse_api_result(result, is_competitor=True)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning("Failed to parse competitor post: %s", e)
                continue

        return posts

    def _parse_api_result(
        self,
        result: dict,
        hashtag_source: Optional[str] = None,
        is_competitor: bool = False,
    ) -> Optional[RawInstagramPost]:
        """Parse API result into RawInstagramPost.

        Args:
            result: Raw API response item
            hashtag_source: Which hashtag search found this post
            is_competitor: Whether from competitor account

        Returns:
            RawInstagramPost or None if parsing fails
        """
        media_id = result.get("id")
        if not media_id:
            return None

        # Parse timestamp
        timestamp_str = result.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            timestamp = datetime.now(timezone.utc)

        return RawInstagramPost(
            media_id=media_id,
            permalink=result.get("permalink", f"https://www.instagram.com/p/{media_id}/"),
            timestamp=timestamp,
            caption=result.get("caption", ""),
            media_type=result.get("media_type", "IMAGE"),
            hashtag_source=hashtag_source,
            is_competitor=is_competitor,
        )
