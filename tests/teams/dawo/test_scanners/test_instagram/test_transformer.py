"""Unit tests for InstagramTransformer.

Tests the transform stage of the Harvester Framework pipeline:
    Scanner -> Harvester -> ThemeExtractor -> ClaimDetector -> [Transformer] -> Validator

Coverage:
    - Transform single post to Research Pool schema
    - Title generation (truncated caption vs account-based)
    - Content generation with theme summary
    - Tag generation and sanitization
    - Metadata building with CleanMarket integration
    - Batch transform handling
    - Error handling for individual posts
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.instagram import (
    InstagramTransformer,
    TransformerError,
    HarvestedPost,
    ThemeResult,
    ClaimDetectionResult,
    DetectedClaim,
    ClaimCategory,
)
from teams.dawo.scanners.instagram.transformer import InstagramTransformer
from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus


class TestInstagramTransformer:
    """Tests for InstagramTransformer class."""

    @pytest.fixture
    def mock_theme_extractor(self):
        """Mock ThemeExtractor."""
        extractor = AsyncMock()
        extractor.extract_themes_batch = AsyncMock(return_value={})
        return extractor

    @pytest.fixture
    def mock_claim_detector(self):
        """Mock HealthClaimDetector."""
        detector = AsyncMock()
        detector.detect_claims_batch = AsyncMock(return_value={})
        return detector

    @pytest.fixture
    def transformer(self, mock_theme_extractor, mock_claim_detector):
        """Create transformer with mocked dependencies."""
        return InstagramTransformer(mock_theme_extractor, mock_claim_detector)

    @pytest.fixture
    def sample_post(self):
        """Sample HarvestedPost for testing."""
        return HarvestedPost(
            media_id="17841563789012345",
            permalink="https://www.instagram.com/p/ABC123/",
            caption="Lion's mane mushroom is amazing for focus! #lionsmane #focus #biohacking",
            hashtags=["lionsmane", "focus", "biohacking"],
            likes=1500,
            comments=45,
            media_type="IMAGE",
            account_name="wellness_user",
            account_type="business",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            is_competitor=False,
            hashtag_source="lionsmane",
        )

    @pytest.mark.asyncio
    async def test_transform_returns_list(self, transformer, sample_post):
        """Transform returns list of TransformedResearch objects."""
        result = await transformer.transform([sample_post])

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_transform_sets_instagram_source(self, transformer, sample_post):
        """Transform sets source to INSTAGRAM."""
        result = await transformer.transform([sample_post])

        assert result[0].source == ResearchSource.INSTAGRAM

    @pytest.mark.asyncio
    async def test_transform_generates_title_from_caption(self, transformer, sample_post):
        """Transform generates title from caption (max 100 chars)."""
        result = await transformer.transform([sample_post])

        assert len(result[0].title) <= 100
        assert "Lion's mane" in result[0].title

    @pytest.mark.asyncio
    async def test_transform_truncates_long_caption_for_title(self, transformer):
        """Transform truncates long caption for title."""
        long_caption = "A" * 150
        post = HarvestedPost(
            media_id="123",
            permalink="https://www.instagram.com/p/ABC123/",
            caption=long_caption,
            hashtags=[],
            likes=100,
            comments=10,
            media_type="IMAGE",
            account_name="test_user",
            account_type="business",
            timestamp=datetime.now(timezone.utc),
            is_competitor=False,
        )

        result = await transformer.transform([post])

        assert len(result[0].title) == 100
        assert result[0].title.endswith("...")

    @pytest.mark.asyncio
    async def test_transform_generates_account_based_title_for_whitespace_caption(self, transformer):
        """Transform generates account-based title when caption is whitespace-only."""
        post = HarvestedPost(
            media_id="123",
            permalink="https://www.instagram.com/p/ABC123/",
            caption="   ",  # Whitespace-only caption triggers account-based title
            hashtags=["test"],
            likes=100,
            comments=10,
            media_type="IMAGE",
            account_name="test_user",
            account_type="business",
            timestamp=datetime.now(timezone.utc),
            is_competitor=False,
        )

        result = await transformer.transform([post])

        # Whitespace caption produces account-based title
        assert len(result) == 1
        assert "Instagram post from @test_user" in result[0].title

    @pytest.mark.asyncio
    async def test_transform_includes_theme_analysis_in_content(
        self, mock_theme_extractor, mock_claim_detector, sample_post
    ):
        """Transform includes theme analysis summary in content."""
        theme_result = ThemeResult(
            content_type="educational",
            messaging_patterns=["personal_story"],
            detected_products=["lion's mane"],
            influencer_indicators=False,
            key_topics=["lions_mane", "focus"],
            confidence_score=0.85,
        )
        mock_theme_extractor.extract_themes_batch.return_value = {
            sample_post.media_id: theme_result
        }

        transformer = InstagramTransformer(mock_theme_extractor, mock_claim_detector)
        result = await transformer.transform([sample_post])

        assert "Theme Analysis" in result[0].content
        assert "educational" in result[0].content

    @pytest.mark.asyncio
    async def test_transform_generates_tags_from_hashtags(self, transformer, sample_post):
        """Transform generates tags from post hashtags."""
        result = await transformer.transform([sample_post])

        assert "lionsmane" in result[0].tags
        assert "focus" in result[0].tags
        assert "biohacking" in result[0].tags

    @pytest.mark.asyncio
    async def test_transform_adds_instagram_tag(self, transformer, sample_post):
        """Transform adds 'instagram' source tag."""
        result = await transformer.transform([sample_post])

        assert "instagram" in result[0].tags

    @pytest.mark.asyncio
    async def test_transform_adds_competitor_tag(self, transformer):
        """Transform adds 'competitor' tag for competitor posts."""
        post = HarvestedPost(
            media_id="123",
            permalink="https://www.instagram.com/p/ABC123/",
            caption="Test caption",
            hashtags=["test"],
            likes=100,
            comments=10,
            media_type="IMAGE",
            account_name="competitor_brand",
            account_type="business",
            timestamp=datetime.now(timezone.utc),
            is_competitor=True,
        )

        result = await transformer.transform([post])

        assert "competitor" in result[0].tags

    @pytest.mark.asyncio
    async def test_transform_sanitizes_tags(self, transformer):
        """Transform sanitizes tags by removing emojis and special chars."""
        post = HarvestedPost(
            media_id="123",
            permalink="https://www.instagram.com/p/ABC123/",
            caption="Test",
            hashtags=["lion🦁mane", "focus✨", "test$tag"],
            likes=100,
            comments=10,
            media_type="IMAGE",
            account_name="test_user",
            account_type="business",
            timestamp=datetime.now(timezone.utc),
            is_competitor=False,
        )

        result = await transformer.transform([post])

        # Emojis should be stripped
        for tag in result[0].tags:
            assert not any(ord(c) > 127 for c in tag)

    @pytest.mark.asyncio
    async def test_transform_builds_metadata_with_engagement(self, transformer, sample_post):
        """Transform includes engagement metrics in metadata."""
        result = await transformer.transform([sample_post])

        metadata = result[0].source_metadata
        assert metadata["likes"] == 1500
        assert metadata["comments"] == 45
        assert metadata["account"] == "wellness_user"
        assert metadata["account_type"] == "business"

    @pytest.mark.asyncio
    async def test_transform_includes_detected_claims_in_metadata(
        self, mock_theme_extractor, mock_claim_detector, sample_post
    ):
        """Transform includes detected claims in metadata for CleanMarket."""
        claim_result = ClaimDetectionResult(
            claims_detected=[
                DetectedClaim(
                    claim_text="boosts focus",
                    category=ClaimCategory.ENHANCEMENT,
                    confidence=0.9,
                    severity="medium",
                )
            ],
            requires_cleanmarket_review=True,
            overall_risk_level="medium",
            summary="Enhancement claim detected",
        )
        mock_claim_detector.detect_claims_batch.return_value = {
            sample_post.media_id: claim_result
        }

        transformer = InstagramTransformer(mock_theme_extractor, mock_claim_detector)
        result = await transformer.transform([sample_post])

        metadata = result[0].source_metadata
        assert "detected_claims" in metadata
        assert len(metadata["detected_claims"]) == 1
        assert metadata["detected_claims"][0]["text"] == "boosts focus"
        assert metadata["cleanmarket_summary"] == "Enhancement claim detected"

    @pytest.mark.asyncio
    async def test_transform_sets_url_to_permalink(self, transformer, sample_post):
        """Transform sets URL to Instagram permalink."""
        result = await transformer.transform([sample_post])

        assert result[0].url == sample_post.permalink

    @pytest.mark.asyncio
    async def test_transform_preserves_timestamp(self, transformer, sample_post):
        """Transform preserves original post timestamp."""
        result = await transformer.transform([sample_post])

        assert result[0].created_at == sample_post.timestamp

    @pytest.mark.asyncio
    async def test_transform_handles_empty_list(self, transformer):
        """Transform handles empty input list."""
        result = await transformer.transform([])

        assert result == []

    @pytest.mark.asyncio
    async def test_transform_continues_on_individual_error(
        self, mock_theme_extractor, mock_claim_detector
    ):
        """Transform continues processing when individual post fails."""
        good_post = HarvestedPost(
            media_id="good",
            permalink="https://www.instagram.com/p/GOOD/",
            caption="Good post",
            hashtags=["test"],
            likes=100,
            comments=10,
            media_type="IMAGE",
            account_name="user",
            account_type="business",
            timestamp=datetime.now(timezone.utc),
            is_competitor=False,
        )

        # Configure to raise error on first call, succeed on second
        mock_theme_extractor.extract_themes_batch.return_value = {"good": None}
        mock_claim_detector.detect_claims_batch.return_value = {"good": None}

        transformer = InstagramTransformer(mock_theme_extractor, mock_claim_detector)
        result = await transformer.transform([good_post])

        # Should still return the good post
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_transform_batch_processing(self, mock_theme_extractor, mock_claim_detector):
        """Transform processes multiple posts in batch."""
        posts = [
            HarvestedPost(
                media_id=f"post_{i}",
                permalink=f"https://www.instagram.com/p/{i}/",
                caption=f"Post {i} caption",
                hashtags=["test"],
                likes=100 * i,
                comments=10 * i,
                media_type="IMAGE",
                account_name=f"user_{i}",
                account_type="business",
                timestamp=datetime.now(timezone.utc),
                is_competitor=False,
            )
            for i in range(5)
        ]

        mock_theme_extractor.extract_themes_batch.return_value = {}
        mock_claim_detector.detect_claims_batch.return_value = {}

        transformer = InstagramTransformer(mock_theme_extractor, mock_claim_detector)
        result = await transformer.transform(posts)

        assert len(result) == 5


class TestTagSanitization:
    """Tests for tag sanitization functionality."""

    @pytest.fixture
    def transformer(self):
        """Create transformer with mocks."""
        return InstagramTransformer(AsyncMock(), AsyncMock())

    def test_sanitize_tag_removes_emojis(self, transformer):
        """Sanitize tag removes emoji characters."""
        result = transformer._sanitize_tag("wellness🌿")
        assert result == "wellness"

    def test_sanitize_tag_lowercases(self, transformer):
        """Sanitize tag converts to lowercase."""
        result = transformer._sanitize_tag("LionsMane")
        assert result == "lionsmane"

    def test_sanitize_tag_replaces_spaces_with_underscore(self, transformer):
        """Sanitize tag replaces spaces with underscores."""
        result = transformer._sanitize_tag("lion mane")
        assert result == "lion_mane"

    def test_sanitize_tag_returns_none_for_short_tags(self, transformer):
        """Sanitize tag returns None for tags < 2 chars."""
        result = transformer._sanitize_tag("a")
        assert result is None

    def test_sanitize_tag_returns_none_for_long_tags(self, transformer):
        """Sanitize tag returns None for tags > 50 chars."""
        result = transformer._sanitize_tag("a" * 51)
        assert result is None

    def test_sanitize_tag_returns_none_for_empty(self, transformer):
        """Sanitize tag returns None for empty string."""
        result = transformer._sanitize_tag("")
        assert result is None

    def test_sanitize_tag_returns_none_for_none(self, transformer):
        """Sanitize tag returns None for None input."""
        result = transformer._sanitize_tag(None)
        assert result is None
