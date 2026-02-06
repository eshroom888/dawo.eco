"""Tests for Reddit Scanner configuration classes.

Tests:
    - RedditClientConfig validation
    - RedditScannerConfig validation
    - Default values
    - Invalid configuration rejection
"""

import pytest

from teams.dawo.scanners.reddit import (
    RedditClientConfig,
    RedditScannerConfig,
    DEFAULT_MIN_UPVOTES,
    DEFAULT_TIME_FILTER,
    DEFAULT_SUBREDDITS,
    DEFAULT_KEYWORDS,
)


class TestRedditClientConfig:
    """Tests for RedditClientConfig dataclass."""

    def test_valid_config_creation(self) -> None:
        """Config with all required fields should be created successfully."""
        config = RedditClientConfig(
            client_id="test_id",
            client_secret="test_secret",
            username="test_user",
            password="test_pass",
        )

        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.username == "test_user"
        assert config.password == "test_pass"
        assert config.user_agent == "DAWO.ECO/1.0.0 (by /u/dawo_bot)"

    def test_custom_user_agent(self) -> None:
        """Custom user agent should be accepted."""
        config = RedditClientConfig(
            client_id="test_id",
            client_secret="test_secret",
            username="test_user",
            password="test_pass",
            user_agent="CustomAgent/2.0",
        )

        assert config.user_agent == "CustomAgent/2.0"

    def test_empty_client_id_raises_error(self) -> None:
        """Empty client_id should raise ValueError."""
        with pytest.raises(ValueError, match="client_id is required"):
            RedditClientConfig(
                client_id="",
                client_secret="secret",
                username="user",
                password="pass",
            )

    def test_empty_client_secret_raises_error(self) -> None:
        """Empty client_secret should raise ValueError."""
        with pytest.raises(ValueError, match="client_secret is required"):
            RedditClientConfig(
                client_id="id",
                client_secret="",
                username="user",
                password="pass",
            )

    def test_empty_username_raises_error(self) -> None:
        """Empty username should raise ValueError."""
        with pytest.raises(ValueError, match="username is required"):
            RedditClientConfig(
                client_id="id",
                client_secret="secret",
                username="",
                password="pass",
            )

    def test_empty_password_raises_error(self) -> None:
        """Empty password should raise ValueError."""
        with pytest.raises(ValueError, match="password is required"):
            RedditClientConfig(
                client_id="id",
                client_secret="secret",
                username="user",
                password="",
            )

    def test_config_is_frozen(self) -> None:
        """Config should be immutable (frozen dataclass)."""
        config = RedditClientConfig(
            client_id="id",
            client_secret="secret",
            username="user",
            password="pass",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            config.client_id = "new_id"


class TestRedditScannerConfig:
    """Tests for RedditScannerConfig dataclass."""

    def test_default_values(self) -> None:
        """Config with defaults should have expected values."""
        config = RedditScannerConfig()

        assert config.subreddits == DEFAULT_SUBREDDITS
        assert config.keywords == DEFAULT_KEYWORDS
        assert config.min_upvotes == DEFAULT_MIN_UPVOTES
        assert config.time_filter == DEFAULT_TIME_FILTER
        assert config.max_posts_per_subreddit == 100
        assert config.rate_limit_requests_per_minute == 60

    def test_custom_subreddits(self) -> None:
        """Custom subreddits should be accepted."""
        config = RedditScannerConfig(
            subreddits=["TestSub1", "TestSub2"],
        )

        assert config.subreddits == ["TestSub1", "TestSub2"]

    def test_custom_keywords(self) -> None:
        """Custom keywords should be accepted."""
        config = RedditScannerConfig(
            keywords=["test keyword"],
        )

        assert config.keywords == ["test keyword"]

    def test_empty_subreddits_raises_error(self) -> None:
        """Empty subreddits list should raise ValueError."""
        with pytest.raises(ValueError, match="subreddits list cannot be empty"):
            RedditScannerConfig(subreddits=[])

    def test_empty_keywords_raises_error(self) -> None:
        """Empty keywords list should raise ValueError."""
        with pytest.raises(ValueError, match="keywords list cannot be empty"):
            RedditScannerConfig(keywords=[])

    def test_negative_min_upvotes_raises_error(self) -> None:
        """Negative min_upvotes should raise ValueError."""
        with pytest.raises(ValueError, match="min_upvotes must be >= 0"):
            RedditScannerConfig(min_upvotes=-1)

    def test_invalid_time_filter_raises_error(self) -> None:
        """Invalid time_filter should raise ValueError."""
        with pytest.raises(ValueError, match="invalid time_filter"):
            RedditScannerConfig(time_filter="invalid")

    def test_valid_time_filters(self) -> None:
        """All valid time_filter values should be accepted."""
        for time_filter in ["hour", "day", "week", "month", "year", "all"]:
            config = RedditScannerConfig(time_filter=time_filter)
            assert config.time_filter == time_filter

    def test_max_posts_too_low_raises_error(self) -> None:
        """max_posts_per_subreddit < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="max_posts_per_subreddit must be 1-100"):
            RedditScannerConfig(max_posts_per_subreddit=0)

    def test_max_posts_too_high_raises_error(self) -> None:
        """max_posts_per_subreddit > 100 should raise ValueError."""
        with pytest.raises(ValueError, match="max_posts_per_subreddit must be 1-100"):
            RedditScannerConfig(max_posts_per_subreddit=101)

    def test_negative_rate_limit_raises_error(self) -> None:
        """rate_limit < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="rate_limit must be >= 1"):
            RedditScannerConfig(rate_limit_requests_per_minute=0)
