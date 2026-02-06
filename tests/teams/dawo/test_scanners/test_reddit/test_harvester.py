"""Tests for Reddit Harvester.

Tests:
    - Harvester initialization
    - Batch harvesting
    - Deleted/removed post handling
    - Error handling
"""

import pytest
from unittest.mock import AsyncMock

from teams.dawo.scanners.reddit import (
    RawRedditPost,
    HarvestedPost,
    RedditAPIError,
)
from teams.dawo.scanners.reddit.harvester import RedditHarvester


class TestRedditHarvesterInit:
    """Tests for RedditHarvester initialization."""

    def test_harvester_creation(self, mock_reddit_client: AsyncMock) -> None:
        """Harvester should be created with injected client."""
        harvester = RedditHarvester(mock_reddit_client)
        assert harvester._client == mock_reddit_client


class TestRedditHarvesterHarvest:
    """Tests for harvest() method."""

    @pytest.mark.asyncio
    async def test_harvest_returns_posts(
        self,
        mock_reddit_client: AsyncMock,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Harvest should return HarvestedPost objects."""
        harvester = RedditHarvester(mock_reddit_client)
        result = await harvester.harvest([raw_reddit_post])

        assert len(result) == 1
        assert isinstance(result[0], HarvestedPost)
        assert result[0].id == raw_reddit_post.id

    @pytest.mark.asyncio
    async def test_harvest_empty_list(
        self,
        mock_reddit_client: AsyncMock,
    ) -> None:
        """Harvest with empty list should return empty list."""
        harvester = RedditHarvester(mock_reddit_client)
        result = await harvester.harvest([])

        assert result == []

    @pytest.mark.asyncio
    async def test_harvest_enriches_data(
        self,
        mock_reddit_client: AsyncMock,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Harvested post should have additional details."""
        harvester = RedditHarvester(mock_reddit_client)
        result = await harvester.harvest([raw_reddit_post])

        post = result[0]
        assert post.selftext  # Body text should be populated
        assert post.author  # Author should be populated
        assert post.upvote_ratio > 0
        assert post.num_comments >= 0

    @pytest.mark.asyncio
    async def test_harvest_builds_full_url(
        self,
        mock_reddit_client: AsyncMock,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Harvested post should have full URL."""
        harvester = RedditHarvester(mock_reddit_client)
        result = await harvester.harvest([raw_reddit_post])

        post = result[0]
        assert post.url.startswith("https://reddit.com")


class TestRedditHarvesterDeletedPosts:
    """Tests for deleted/removed post handling."""

    @pytest.mark.asyncio
    async def test_skip_deleted_post(
        self,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Deleted posts should be skipped."""
        mock_client = AsyncMock()
        mock_client.get_post_details.return_value = {
            "id": "abc123",
            "author": "[deleted]",
            "title": "Deleted post",
            "selftext": "[deleted]",
        }

        harvester = RedditHarvester(mock_client)
        result = await harvester.harvest([raw_reddit_post])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_skip_removed_post(
        self,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Removed posts should be skipped."""
        mock_client = AsyncMock()
        mock_client.get_post_details.return_value = {
            "id": "abc123",
            "author": "user123",
            "title": "Removed post",
            "selftext": "[removed]",
        }

        harvester = RedditHarvester(mock_client)
        result = await harvester.harvest([raw_reddit_post])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_skip_mod_removed_post(
        self,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Moderator-removed posts should be skipped."""
        mock_client = AsyncMock()
        mock_client.get_post_details.return_value = {
            "id": "abc123",
            "author": "user123",
            "title": "Mod removed post",
            "selftext": "Some content",
            "removed_by_category": "moderator",
        }

        harvester = RedditHarvester(mock_client)
        result = await harvester.harvest([raw_reddit_post])

        assert len(result) == 0


class TestRedditHarvesterErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_api_error_skips_post(
        self,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """API error should skip post and continue."""
        mock_client = AsyncMock()
        mock_client.get_post_details.side_effect = RedditAPIError("API error")

        harvester = RedditHarvester(mock_client)
        result = await harvester.harvest([raw_reddit_post])

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self) -> None:
        """Failure on one post should not stop others."""
        mock_client = AsyncMock()

        # First call fails, second succeeds
        mock_client.get_post_details.side_effect = [
            RedditAPIError("API error"),
            {
                "id": "def456",
                "subreddit": "Test",
                "title": "Success post",
                "selftext": "Content",
                "author": "user",
                "score": 100,
                "upvote_ratio": 0.95,
                "num_comments": 10,
                "permalink": "/r/Test/comments/def456/",
                "created_utc": 1707177600,
                "is_self": True,
            },
        ]

        posts = [
            RawRedditPost(
                id="abc123",
                subreddit="Test",
                title="Fail post",
                score=100,
                created_utc=1707177600,
                permalink="/r/Test/comments/abc123/",
            ),
            RawRedditPost(
                id="def456",
                subreddit="Test",
                title="Success post",
                score=100,
                created_utc=1707177600,
                permalink="/r/Test/comments/def456/",
            ),
        ]

        harvester = RedditHarvester(mock_client)
        result = await harvester.harvest(posts)

        # Should have one successful harvest
        assert len(result) == 1
        assert result[0].id == "def456"

    @pytest.mark.asyncio
    async def test_empty_details_skips_post(
        self,
        raw_reddit_post: RawRedditPost,
    ) -> None:
        """Empty API response should skip post."""
        mock_client = AsyncMock()
        mock_client.get_post_details.return_value = {}

        harvester = RedditHarvester(mock_client)
        result = await harvester.harvest([raw_reddit_post])

        assert len(result) == 0
