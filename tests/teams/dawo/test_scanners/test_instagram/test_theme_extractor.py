"""Tests for ThemeExtractor.

Tests the theme extraction stage with mocked LLM responses.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.instagram import (
    ThemeExtractor,
    ThemeExtractionError,
    ThemeResult,
    HarvestedPost,
)


class TestThemeExtractor:
    """Test suite for ThemeExtractor."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing."""
        client = AsyncMock()
        client.generate.return_value = json.dumps({
            "content_type": "educational",
            "messaging_patterns": ["personal_story", "science_reference"],
            "detected_products": ["lion's mane extract"],
            "influencer_indicators": False,
            "key_topics": ["lions_mane", "cognition", "focus"],
            "confidence_score": 0.85
        })
        return client

    @pytest.fixture
    def extractor(self, mock_llm_client):
        """Create extractor with mocked LLM."""
        return ThemeExtractor(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_extract_themes_returns_theme_result(self, extractor):
        """Test that extract_themes returns ThemeResult."""
        result = await extractor.extract_themes(
            caption="Lion's mane helps with focus!",
            hashtags=["lionsmane", "focus"],
            account_name="wellness_user",
        )

        assert isinstance(result, ThemeResult)

    @pytest.mark.asyncio
    async def test_extract_themes_parses_response(self, extractor):
        """Test that extract_themes correctly parses LLM response."""
        result = await extractor.extract_themes(
            caption="Lion's mane helps with focus!",
            hashtags=["lionsmane", "focus"],
            account_name="wellness_user",
        )

        assert result.content_type == "educational"
        assert "personal_story" in result.messaging_patterns
        assert "lion's mane extract" in result.detected_products
        assert result.influencer_indicators == False
        assert 0.8 <= result.confidence_score <= 0.9

    @pytest.mark.asyncio
    async def test_extract_themes_empty_caption(self, extractor):
        """Test that empty caption returns default result."""
        result = await extractor.extract_themes(
            caption="",
            hashtags=["test"],
            account_name="user",
        )

        assert result.confidence_score == 0.3  # Low confidence for empty

    @pytest.mark.asyncio
    async def test_extract_themes_handles_json_error(self, extractor, mock_llm_client):
        """Test that invalid JSON response returns default result."""
        mock_llm_client.generate.return_value = "Not valid JSON"

        result = await extractor.extract_themes(
            caption="Some content",
            hashtags=["test"],
            account_name="user",
        )

        assert result.confidence_score == 0.3  # Default low confidence

    @pytest.mark.asyncio
    async def test_extract_themes_batch(self, extractor):
        """Test batch theme extraction."""
        posts = [
            HarvestedPost(
                media_id="post1",
                permalink="https://example.com/1",
                caption="Lion's mane!",
                hashtags=["lionsmane"],
                likes=100,
                comments=10,
                media_type="IMAGE",
                account_name="user1",
                account_type="business",
                timestamp=datetime.now(timezone.utc),
                is_competitor=False,
            ),
            HarvestedPost(
                media_id="post2",
                permalink="https://example.com/2",
                caption="Adaptogens!",
                hashtags=["adaptogens"],
                likes=200,
                comments=20,
                media_type="IMAGE",
                account_name="user2",
                account_type="business",
                timestamp=datetime.now(timezone.utc),
                is_competitor=False,
            ),
        ]

        results = await extractor.extract_themes_batch(posts)

        assert "post1" in results
        assert "post2" in results


class TestThemeResult:
    """Test suite for ThemeResult dataclass."""

    def test_valid_theme_result(self):
        """Test creating valid ThemeResult."""
        result = ThemeResult(
            content_type="educational",
            confidence_score=0.85,
        )

        assert result.content_type == "educational"
        assert result.confidence_score == 0.85

    def test_invalid_confidence_score(self):
        """Test that invalid confidence score raises ValueError."""
        with pytest.raises(ValueError, match="confidence_score must be 0-1"):
            ThemeResult(
                content_type="educational",
                confidence_score=1.5,  # Invalid
            )

    def test_default_values(self):
        """Test that default values are set correctly."""
        result = ThemeResult(content_type="educational", confidence_score=0.5)

        assert result.messaging_patterns == []
        assert result.detected_products == []
        assert result.influencer_indicators == False
        assert result.key_topics == []
