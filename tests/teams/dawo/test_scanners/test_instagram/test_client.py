"""Tests for InstagramClient API client.

Tests the Instagram Graph API client with mocked responses.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from teams.dawo.scanners.instagram import (
    InstagramClient,
    InstagramClientConfig,
    InstagramAPIError,
    RateLimitError,
    RateLimitTracker,
    extract_hashtags,
)


class TestInstagramClientConfig:
    """Test suite for InstagramClientConfig validation."""

    def test_config_requires_access_token(self):
        """Test that empty access_token raises ValueError."""
        with pytest.raises(ValueError, match="access_token is required"):
            InstagramClientConfig(access_token="", business_account_id="test_id")

    def test_config_requires_business_account_id(self):
        """Test that empty business_account_id raises ValueError."""
        with pytest.raises(ValueError, match="business_account_id is required"):
            InstagramClientConfig(access_token="test_token", business_account_id="")

    def test_config_valid_credentials(self):
        """Test that valid credentials are accepted."""
        config = InstagramClientConfig(
            access_token="valid_token",
            business_account_id="valid_id",
        )
        assert config.access_token == "valid_token"
        assert config.business_account_id == "valid_id"

    def test_config_is_frozen(self):
        """Test that config is immutable (frozen dataclass)."""
        config = InstagramClientConfig(
            access_token="token",
            business_account_id="id",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            config.access_token = "new_token"


class TestRateLimitTracker:
    """Test suite for RateLimitTracker."""

    def test_tracker_initial_state(self):
        """Test that tracker starts with full quota."""
        tracker = RateLimitTracker()
        assert tracker.get_remaining() == 200  # INSTAGRAM_RATE_LIMIT_PER_HOUR

    def test_tracker_consumes_calls(self):
        """Test that check_and_use reduces remaining quota."""
        tracker = RateLimitTracker()
        initial = tracker.get_remaining()

        tracker.check_and_use(5)

        assert tracker.get_remaining() == initial - 5

    def test_tracker_raises_on_limit_exceeded(self):
        """Test that exceeding limit raises RateLimitError."""
        tracker = RateLimitTracker()

        # Consume most of the quota
        tracker.check_and_use(195)

        # This should fail - would exceed 200
        with pytest.raises(RateLimitError):
            tracker.check_and_use(10)

    def test_tracker_reset_time(self):
        """Test that reset time is approximately 1 hour from start."""
        tracker = RateLimitTracker()
        reset_time = tracker.get_reset_time()

        # Reset should be about 1 hour in the future
        now = datetime.now(timezone.utc)
        diff = (reset_time - now).total_seconds()
        assert 3550 < diff < 3650  # Within 50 seconds of 1 hour


class TestInstagramClient:
    """Test suite for InstagramClient."""

    @pytest.fixture
    def client_setup(self, client_config, mock_retry_middleware):
        """Set up client with mocked dependencies."""
        return InstagramClient(
            config=client_config,
            retry_middleware=mock_retry_middleware,
        )

    @pytest.mark.asyncio
    async def test_client_search_hashtag_calls_api(self, client_setup, mock_hashtag_search_response):
        """Test that search_hashtag makes correct API calls."""
        client = client_setup

        # Mock the _api_call method
        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock_api:
            # First call returns hashtag ID
            mock_api.side_effect = [
                {"data": [{"id": "hashtag_id_123"}]},
                mock_hashtag_search_response,
            ]

            result = await client.search_hashtag("lionsmane", limit=10)

            # Should make 2 API calls: hashtag lookup + media fetch
            assert mock_api.call_count == 2

    @pytest.mark.asyncio
    async def test_client_search_hashtag_returns_list(self, client_setup, mock_hashtag_search_response):
        """Test that search_hashtag returns list of posts."""
        client = client_setup

        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = [
                {"data": [{"id": "hashtag_id_123"}]},
                mock_hashtag_search_response,
            ]

            result = await client.search_hashtag("lionsmane")

            assert isinstance(result, list)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_client_search_hashtag_empty_results(self, client_setup):
        """Test that search_hashtag handles no results gracefully."""
        client = client_setup

        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"data": []}

            result = await client.search_hashtag("nonexistent_hashtag")

            assert result == []

    @pytest.mark.asyncio
    async def test_client_get_user_media_calls_api(self, client_setup, mock_competitor_media_response):
        """Test that get_user_media makes correct API call."""
        client = client_setup

        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_competitor_media_response

            result = await client.get_user_media("competitor_brand", limit=5)

            assert mock_api.call_count == 1

    @pytest.mark.asyncio
    async def test_client_get_user_media_returns_list(self, client_setup, mock_competitor_media_response):
        """Test that get_user_media returns list of posts."""
        client = client_setup

        with patch.object(client, "_api_call", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_competitor_media_response

            result = await client.get_user_media("competitor_brand")

            assert isinstance(result, list)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_client_respects_rate_limit(self, client_config, mock_retry_middleware):
        """Test that client checks rate limit before API calls."""
        # Create tracker with almost exhausted quota
        tracker = RateLimitTracker()
        tracker.check_and_use(199)  # Only 1 call remaining

        client = InstagramClient(
            config=client_config,
            retry_middleware=mock_retry_middleware,
            rate_limit_tracker=tracker,
        )

        # search_hashtag needs 2 calls, should fail
        with pytest.raises(RateLimitError):
            await client.search_hashtag("test")

    def test_client_rate_limit_remaining(self, client_setup):
        """Test rate_limit_remaining property."""
        client = client_setup
        remaining = client.rate_limit_remaining

        assert isinstance(remaining, int)
        assert remaining <= 200


class TestExtractHashtags:
    """Test suite for extract_hashtags utility function."""

    def test_extract_simple_hashtags(self):
        """Test extracting simple hashtags."""
        caption = "Love my morning #lionsmane #coffee routine!"
        result = extract_hashtags(caption)

        assert "lionsmane" in result
        assert "coffee" in result

    def test_extract_removes_duplicates(self):
        """Test that duplicate hashtags are removed."""
        caption = "#lionsmane #LIONSMANE #LionsMane"
        result = extract_hashtags(caption)

        assert len(result) == 1
        assert result[0] == "lionsmane"

    def test_extract_handles_empty_caption(self):
        """Test that empty caption returns empty list."""
        assert extract_hashtags("") == []
        assert extract_hashtags(None) == []

    def test_extract_handles_no_hashtags(self):
        """Test that caption without hashtags returns empty list."""
        caption = "No hashtags here, just text."
        result = extract_hashtags(caption)

        assert result == []

    def test_extract_handles_special_characters(self):
        """Test that hashtags with numbers and underscores work."""
        caption = "#lions_mane_2024 #biohacking101"
        result = extract_hashtags(caption)

        assert "lions_mane_2024" in result
        assert "biohacking101" in result

    def test_extract_preserves_order(self):
        """Test that hashtags are returned in order of appearance."""
        caption = "#first #second #third"
        result = extract_hashtags(caption)

        assert result == ["first", "second", "third"]
