"""Pytest fixtures for Reddit Scanner tests.

Provides mock objects and test data for Reddit scanner testing:
    - Mock Reddit API responses
    - Mock RedditClient
    - Test configurations
    - Sample post data
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.reddit import (
    RedditClient,
    RedditClientConfig,
    RedditScannerConfig,
    RawRedditPost,
    HarvestedPost,
)
from teams.dawo.middleware.retry import RetryConfig, RetryMiddleware


# Test timestamps (within last 24 hours)
NOW = datetime.now(timezone.utc)
RECENT_TIMESTAMP = NOW.timestamp() - 3600  # 1 hour ago
OLD_TIMESTAMP = NOW.timestamp() - 172800  # 2 days ago


@pytest.fixture
def mock_reddit_post_data() -> dict:
    """Single mock Reddit post from API response."""
    return {
        "id": "abc123",
        "title": "My experience with lion's mane for brain fog",
        "selftext": "Been taking lion's mane for 3 months and noticed significant improvements in focus and clarity...",
        "author": "user123",
        "subreddit": "Nootropics",
        "score": 150,
        "upvote_ratio": 0.95,
        "num_comments": 45,
        "permalink": "/r/Nootropics/comments/abc123/my_experience/",
        "url": "https://reddit.com/r/Nootropics/comments/abc123/my_experience/",
        "created_utc": RECENT_TIMESTAMP,
        "is_self": True,
    }


@pytest.fixture
def mock_reddit_search_response(mock_reddit_post_data: dict) -> dict:
    """Mock Reddit API search response."""
    return {
        "kind": "Listing",
        "data": {
            "children": [
                {"kind": "t3", "data": mock_reddit_post_data},
                {
                    "kind": "t3",
                    "data": {
                        "id": "def456",
                        "title": "Chaga tea recipe and benefits",
                        "selftext": "I've been brewing chaga tea every morning...",
                        "author": "mushroom_lover",
                        "subreddit": "Supplements",
                        "score": 75,
                        "upvote_ratio": 0.92,
                        "num_comments": 23,
                        "permalink": "/r/Supplements/comments/def456/chaga_tea/",
                        "url": "https://reddit.com/r/Supplements/comments/def456/chaga_tea/",
                        "created_utc": RECENT_TIMESTAMP - 7200,  # 3 hours ago
                        "is_self": True,
                    },
                },
                {
                    "kind": "t3",
                    "data": {
                        "id": "ghi789",
                        "title": "Low upvote post",
                        "selftext": "This post has few upvotes",
                        "author": "newbie",
                        "subreddit": "Nootropics",
                        "score": 5,  # Below threshold
                        "upvote_ratio": 0.80,
                        "num_comments": 2,
                        "permalink": "/r/Nootropics/comments/ghi789/low_upvote/",
                        "url": "https://reddit.com/r/Nootropics/comments/ghi789/low_upvote/",
                        "created_utc": RECENT_TIMESTAMP,
                        "is_self": True,
                    },
                },
            ],
        },
    }


@pytest.fixture
def mock_reddit_client_config() -> RedditClientConfig:
    """Test Reddit API credentials config."""
    return RedditClientConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        username="test_username",
        password="test_password",
        user_agent="DAWO.ECO/1.0.0 (test)",
    )


@pytest.fixture
def scanner_config() -> RedditScannerConfig:
    """Test scanner configuration with reduced scope for faster tests."""
    return RedditScannerConfig(
        subreddits=["Nootropics"],
        keywords=["lion's mane"],
        min_upvotes=10,
        time_filter="day",
        max_posts_per_subreddit=100,
        rate_limit_requests_per_minute=60,
    )


@pytest.fixture
def retry_config() -> RetryConfig:
    """Test retry configuration."""
    return RetryConfig(
        max_retries=3,
        base_delay=0.1,  # Fast for tests
        max_delay=1.0,
        backoff_multiplier=2.0,
        timeout=5.0,
    )


@pytest.fixture
def mock_retry_middleware(retry_config: RetryConfig) -> RetryMiddleware:
    """Real retry middleware with test config."""
    return RetryMiddleware(retry_config)


@pytest.fixture
def mock_reddit_client(
    mock_reddit_client_config: RedditClientConfig,
    mock_retry_middleware: RetryMiddleware,
    mock_reddit_search_response: dict,
) -> AsyncMock:
    """Mock RedditClient for testing without API calls."""
    client = AsyncMock(spec=RedditClient)

    # Mock search_subreddit to return posts
    client.search_subreddit.return_value = [
        child["data"] for child in mock_reddit_search_response["data"]["children"]
    ]

    # Mock get_post_details
    client.get_post_details.return_value = mock_reddit_search_response["data"][
        "children"
    ][0]["data"]

    return client


@pytest.fixture
def raw_reddit_post() -> RawRedditPost:
    """Sample RawRedditPost for testing."""
    return RawRedditPost(
        id="abc123",
        subreddit="Nootropics",
        title="My experience with lion's mane for brain fog",
        score=150,
        created_utc=RECENT_TIMESTAMP,
        permalink="/r/Nootropics/comments/abc123/my_experience/",
        is_self=True,
    )


@pytest.fixture
def harvested_post() -> HarvestedPost:
    """Sample HarvestedPost for testing."""
    return HarvestedPost(
        id="abc123",
        subreddit="Nootropics",
        title="My experience with lion's mane for brain fog",
        selftext="Been taking lion's mane for 3 months and noticed significant improvements...",
        author="user123",
        score=150,
        upvote_ratio=0.95,
        num_comments=45,
        permalink="/r/Nootropics/comments/abc123/my_experience/",
        url="https://reddit.com/r/Nootropics/comments/abc123/my_experience/",
        created_utc=RECENT_TIMESTAMP,
        is_self=True,
    )
