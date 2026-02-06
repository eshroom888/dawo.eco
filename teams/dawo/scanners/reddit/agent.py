"""Reddit Research Scanner Agent.

Main scanner class implementing the scan stage of the Harvester Framework:
    [Scanner] → Harvester → Transformer → Validator → Publisher → Research Pool

The RedditScanner discovers research content from configured subreddits
by searching for mushroom/wellness keywords and filtering by engagement.

Registration: team_spec.py with tier="scan" (maps to fast model at runtime)

Usage:
    # Created by Team Builder with injected dependencies
    scanner = RedditScanner(config, client)

    # Execute scan stage
    result = await scanner.scan()
    # result.posts contains RawRedditPost objects
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .config import RedditScannerConfig
from .schemas import RawRedditPost, ScanResult, ScanStatistics
from .tools import RedditClient, RedditAPIError


# Module logger
logger = logging.getLogger(__name__)

# Seconds in 24 hours for time filtering
SECONDS_IN_DAY = 86400


class RedditScanError(Exception):
    """Exception raised for scanner-level errors.

    Attributes:
        message: Error description
        partial_results: Any posts collected before error
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list[RawRedditPost]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class RedditScanner:
    """Reddit Research Scanner - discovers content from subreddits.

    Implements the scan stage of the Harvester Framework pipeline.
    Searches configured subreddits for posts matching mushroom/wellness
    keywords, then filters by minimum upvotes and recency.

    Features:
        - Multi-subreddit scanning
        - Multi-keyword search per subreddit
        - Upvote threshold filtering (default 10+)
        - Time-based filtering (default: last 24 hours)
        - Deduplication by post ID

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _config: Scanner configuration (subreddits, keywords, filters)
        _client: Reddit API client for making requests
    """

    def __init__(
        self,
        config: RedditScannerConfig,
        client: RedditClient,
    ):
        """Initialize scanner with injected dependencies.

        Args:
            config: Scanner configuration from Team Builder
            client: Reddit API client with credentials
        """
        self._config = config
        self._client = client

    async def scan(self) -> ScanResult:
        """Execute the scan stage - discover Reddit posts.

        Iterates through configured subreddits and keywords, collecting
        posts that meet the filtering criteria.

        Returns:
            ScanResult with discovered posts and statistics

        Raises:
            RedditScanError: If critical error prevents scanning
        """
        logger.info(
            "Starting Reddit scan: %d subreddits, %d keywords",
            len(self._config.subreddits),
            len(self._config.keywords),
        )

        stats = ScanStatistics()
        all_posts: dict[str, RawRedditPost] = {}  # Keyed by post ID for deduplication
        errors: list[str] = []

        for subreddit in self._config.subreddits:
            stats.subreddits_scanned += 1

            for keyword in self._config.keywords:
                stats.keywords_searched += 1

                try:
                    posts = await self._search_and_filter(subreddit, keyword)
                    stats.total_posts_found += len(posts)

                    # Filter by upvotes and time
                    filtered = self._apply_filters(posts)
                    stats.posts_after_filter += len(filtered)

                    # Deduplicate by adding to dict (overwrites duplicates)
                    before_count = len(all_posts)
                    for post in filtered:
                        all_posts[post.id] = post
                    stats.duplicates_removed += (
                        before_count + len(filtered) - len(all_posts)
                    )

                except RedditAPIError as e:
                    error_msg = f"Failed to search r/{subreddit} for '{keyword}': {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    # Continue with other subreddits/keywords

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

    async def _search_and_filter(
        self,
        subreddit: str,
        keyword: str,
    ) -> list[RawRedditPost]:
        """Search subreddit for keyword and convert to schema.

        Args:
            subreddit: Subreddit name
            keyword: Search keyword

        Returns:
            List of RawRedditPost objects
        """
        raw_posts = await self._client.search_subreddit(
            subreddit=subreddit,
            query=keyword,
            time_filter=self._config.time_filter,
            limit=self._config.max_posts_per_subreddit,
        )

        return [
            RawRedditPost(
                id=post.get("id", ""),
                subreddit=post.get("subreddit", subreddit),
                title=post.get("title", ""),
                score=post.get("score", 0),
                created_utc=post.get("created_utc", 0),
                permalink=post.get("permalink", ""),
                is_self=post.get("is_self", True),
            )
            for post in raw_posts
            if post.get("id")  # Skip posts without ID
        ]

    def _apply_filters(self, posts: list[RawRedditPost]) -> list[RawRedditPost]:
        """Apply upvote and time filters to posts.

        Args:
            posts: Raw posts to filter

        Returns:
            Posts meeting filter criteria

        Note:
            Local time filtering is only applied for time_filter="day".
            For other time filters (hour, week, month, year, all), we rely
            on Reddit API's 't' parameter which filters server-side.
            This is intentional - Reddit's API is authoritative for these
            longer time windows, and local re-filtering would be redundant.
        """
        now = datetime.now(timezone.utc).timestamp()
        cutoff_time = now - SECONDS_IN_DAY  # 24 hours ago

        filtered = []
        for post in posts:
            # Check upvote threshold
            if post.score < self._config.min_upvotes:
                continue

            # Check time filter for "day" only - other filters rely on Reddit API's 't' param
            # See docstring note above for rationale
            if self._config.time_filter == "day" and post.created_utc < cutoff_time:
                continue

            filtered.append(post)

        return filtered
