"""Reddit Harvester - enriches raw posts with full details.

Implements the harvest stage of the Harvester Framework pipeline:
    Scanner → [Harvester] → Transformer → Validator → Publisher → Research Pool

The harvester takes raw post data from the scanner and fetches complete
post details from the Reddit API, including full body text and engagement metrics.

Usage:
    harvester = RedditHarvester(client)
    enriched = await harvester.harvest(raw_posts)
"""

import logging
from typing import Optional

from .schemas import RawRedditPost, HarvestedPost
from .tools import RedditClient, RedditAPIError


# Module logger
logger = logging.getLogger(__name__)


class HarvesterError(Exception):
    """Exception raised for harvester-level errors.

    Attributes:
        message: Error description
        post_id: ID of post being harvested when error occurred
    """

    def __init__(self, message: str, post_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.post_id = post_id


class RedditHarvester:
    """Reddit Harvester - fetches full post details.

    Takes raw posts from the scanner stage and retrieves complete
    information including full body text, author, and engagement metrics.

    Features:
        - Batch processing of raw posts
        - Graceful handling of deleted/removed posts
        - Rate limiting via underlying client
        - Detailed logging of harvest progress

    Configuration is injected via constructor - NEVER loads files directly.

    Attributes:
        _client: Reddit API client for fetching details
    """

    def __init__(self, client: RedditClient):
        """Initialize harvester with injected client.

        Args:
            client: Reddit API client with authentication
        """
        self._client = client

    async def harvest(
        self,
        raw_posts: list[RawRedditPost],
    ) -> list[HarvestedPost]:
        """Harvest full details for raw posts.

        Fetches complete post data including body text, author,
        and engagement metrics for each raw post.

        Handles deleted/removed posts gracefully by skipping them
        with a log message.

        Args:
            raw_posts: List of raw posts from scanner stage

        Returns:
            List of HarvestedPost objects with full details

        Raises:
            HarvesterError: If critical error prevents harvesting
        """
        logger.info("Starting harvest for %d posts", len(raw_posts))

        harvested: list[HarvestedPost] = []
        skipped = 0

        for raw_post in raw_posts:
            try:
                post = await self._harvest_single(raw_post)
                if post:
                    harvested.append(post)
                else:
                    skipped += 1

            except RedditAPIError as e:
                logger.error(
                    "Failed to harvest post %s: %s",
                    raw_post.id,
                    e,
                )
                skipped += 1
                # Continue with remaining posts

        logger.info(
            "Harvest complete: %d posts harvested, %d skipped",
            len(harvested),
            skipped,
        )

        return harvested

    async def _harvest_single(
        self,
        raw_post: RawRedditPost,
    ) -> Optional[HarvestedPost]:
        """Harvest details for a single post.

        Args:
            raw_post: Raw post to harvest

        Returns:
            HarvestedPost with full details, or None if unavailable
        """
        logger.debug("Harvesting post %s from r/%s", raw_post.id, raw_post.subreddit)

        try:
            details = await self._client.get_post_details(raw_post.id)

            if not details:
                logger.warning("No details returned for post %s", raw_post.id)
                return None

            # Check for deleted/removed posts
            if self._is_deleted_or_removed(details):
                logger.debug("Skipping deleted/removed post %s", raw_post.id)
                return None

            return HarvestedPost(
                id=details.get("id", raw_post.id),
                subreddit=details.get("subreddit", raw_post.subreddit),
                title=details.get("title", raw_post.title),
                selftext=details.get("selftext", ""),
                author=details.get("author", "[unknown]"),
                score=details.get("score", raw_post.score),
                upvote_ratio=details.get("upvote_ratio", 1.0),
                num_comments=details.get("num_comments", 0),
                permalink=details.get("permalink", raw_post.permalink),
                url=self._build_full_url(details.get("permalink", raw_post.permalink)),
                created_utc=details.get("created_utc", raw_post.created_utc),
                is_self=details.get("is_self", raw_post.is_self),
            )

        except RedditAPIError:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error harvesting post %s: %s",
                raw_post.id,
                e,
            )
            return None

    def _is_deleted_or_removed(self, details: dict) -> bool:
        """Check if post is deleted or removed.

        Args:
            details: Post details from API

        Returns:
            True if post is deleted or removed
        """
        # Reddit marks deleted posts with these indicators
        if details.get("author") == "[deleted]":
            return True
        if details.get("selftext") == "[removed]":
            return True
        if details.get("removed_by_category"):
            return True
        return False

    def _build_full_url(self, permalink: str) -> str:
        """Build full Reddit URL from permalink.

        Args:
            permalink: Relative permalink (e.g., /r/Sub/comments/123/)

        Returns:
            Full URL (e.g., https://reddit.com/r/Sub/comments/123/)
        """
        if permalink.startswith("https://"):
            return permalink
        return f"https://reddit.com{permalink}"
