"""Tests for InstagramHarvester.

Tests the harvest stage of the Harvester Framework pipeline.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.instagram import (
    InstagramHarvester,
    HarvesterError,
    RawInstagramPost,
    HarvestedPost,
    InstagramAPIError,
)


class TestInstagramHarvester:
    """Test suite for InstagramHarvester."""

    @pytest.fixture
    def mock_client(self):
        """Mock InstagramClient for testing."""
        client = AsyncMock()
        client.get_media_details.return_value = {
            "id": "17841563789012345",
            "caption": "Lion's mane for focus! #lionsmane #focus #biohacking",
            "permalink": "https://www.instagram.com/p/ABC123/",
            "like_count": 1500,
            "comments_count": 45,
            "media_type": "IMAGE",
            "username": "wellness_user",
        }
        return client

    @pytest.fixture
    def harvester(self, mock_client):
        """Create harvester with mocked client."""
        return InstagramHarvester(client=mock_client)

    @pytest.fixture
    def raw_posts(self):
        """Sample raw posts for testing."""
        return [
            RawInstagramPost(
                media_id="17841563789012345",
                permalink="https://www.instagram.com/p/ABC123/",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
                caption="Lion's mane!",
                media_type="IMAGE",
                hashtag_source="lionsmane",
                is_competitor=False,
            ),
            RawInstagramPost(
                media_id="17841563789012346",
                permalink="https://www.instagram.com/p/ABC124/",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
                caption="Adaptogens!",
                media_type="IMAGE",
                hashtag_source="adaptogens",
                is_competitor=True,
            ),
        ]

    @pytest.mark.asyncio
    async def test_harvest_returns_list(self, harvester, raw_posts):
        """Test that harvest returns a list of HarvestedPost."""
        result = await harvester.harvest(raw_posts)

        assert isinstance(result, list)
        for post in result:
            assert isinstance(post, HarvestedPost)

    @pytest.mark.asyncio
    async def test_harvest_extracts_hashtags(self, harvester, raw_posts, mock_client):
        """Test that harvest extracts hashtags from caption."""
        result = await harvester.harvest(raw_posts[:1])

        assert len(result) == 1
        assert "lionsmane" in result[0].hashtags
        assert "focus" in result[0].hashtags

    @pytest.mark.asyncio
    async def test_harvest_preserves_metadata(self, harvester, raw_posts):
        """Test that harvest preserves original metadata."""
        result = await harvester.harvest(raw_posts[:1])

        assert result[0].media_id == "17841563789012345"
        assert result[0].hashtag_source == "lionsmane"
        assert result[0].is_competitor == False

    @pytest.mark.asyncio
    async def test_harvest_fetches_engagement(self, harvester, raw_posts):
        """Test that harvest fetches engagement metrics."""
        result = await harvester.harvest(raw_posts[:1])

        assert result[0].likes == 1500
        assert result[0].comments == 45

    @pytest.mark.asyncio
    async def test_harvest_continues_on_api_error(self, harvester, raw_posts, mock_client):
        """Test that harvest continues if one post fails."""
        # First post fails, second succeeds
        mock_client.get_media_details.side_effect = [
            InstagramAPIError("API error"),
            {
                "id": "17841563789012346",
                "caption": "Adaptogens!",
                "permalink": "https://www.instagram.com/p/ABC124/",
                "like_count": 800,
                "comments_count": 20,
                "media_type": "IMAGE",
                "username": "other_user",
            },
        ]

        result = await harvester.harvest(raw_posts)

        # Should have one successful result
        assert len(result) == 1
        assert result[0].media_id == "17841563789012346"

    @pytest.mark.asyncio
    async def test_harvest_single(self, harvester, raw_posts):
        """Test harvest_single method."""
        result = await harvester.harvest_single(raw_posts[0])

        assert isinstance(result, HarvestedPost)
        assert result.media_id == "17841563789012345"

    @pytest.mark.asyncio
    async def test_harvest_no_image_storage(self, harvester, raw_posts):
        """Test that harvest does NOT store image URLs."""
        result = await harvester.harvest(raw_posts[:1])

        # HarvestedPost should not have image_url attribute
        assert not hasattr(result[0], "image_url")
