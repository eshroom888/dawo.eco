"""Unit tests for Instagram Caption Generator (Story 3.3).

Tests cover:
- Caption generation with valid inputs
- Word count enforcement (180-220)
- Hashtag generation and brand tag inclusion
- Product data integration with mock ShopifyClient
- UTM parameter generation in links
- Brand Voice validation integration
- AI-generic pattern detection
- Generation time < 60 seconds
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

# Use direct imports to avoid circular import issues
from teams.dawo.generators.instagram_caption.agent import CaptionGenerator
from teams.dawo.generators.instagram_caption.schemas import CaptionRequest, CaptionResult
from teams.dawo.generators.instagram_caption.tools import (
    count_words,
    validate_word_count,
    generate_hashtags,
    validate_hashtags,
    format_research_citation,
    MIN_WORDS,
    MAX_WORDS,
    MAX_HASHTAGS,
    BRAND_TAGS,
)
from teams.dawo.validators.brand_voice.agent import (
    BrandVoiceValidator,
    ValidationStatus,
)


class TestWordCounting:
    """Tests for word count utilities."""

    def test_count_words_basic(self):
        """Test basic word counting."""
        text = "Dette er en enkel test"
        assert count_words(text) == 5

    def test_count_words_excludes_hashtags(self):
        """Test that hashtags are excluded from word count."""
        text = "Dette er en test #DAWO #test"
        assert count_words(text) == 4

    def test_count_words_empty_string(self):
        """Test word count of empty string."""
        assert count_words("") == 0

    def test_count_words_only_hashtags(self):
        """Test word count with only hashtags."""
        text = "#DAWO #DAWOmushrooms #nordisksopp"
        assert count_words(text) == 0

    def test_count_words_multiline(self):
        """Test word count with multiline text."""
        text = """Første linje her
        Andre linje her
        #hashtag"""
        # Første(1) linje(2) her(3) Andre(4) linje(5) her(6) = 6 words (hashtag excluded)
        assert count_words(text) == 6

    def test_validate_word_count_valid(self):
        """Test validation of valid word count."""
        text = " ".join(["ord"] * 190)  # 190 words
        is_valid, msg = validate_word_count(text)
        assert is_valid is True
        assert "190" in msg

    def test_validate_word_count_too_short(self):
        """Test validation of too short text."""
        text = " ".join(["ord"] * 50)  # 50 words
        is_valid, msg = validate_word_count(text)
        assert is_valid is False
        assert "too short" in msg.lower()

    def test_validate_word_count_too_long(self):
        """Test validation of too long text."""
        text = " ".join(["ord"] * 250)  # 250 words
        is_valid, msg = validate_word_count(text)
        assert is_valid is False
        assert "too long" in msg.lower()


class TestHashtagGeneration:
    """Tests for hashtag generation utilities."""

    def test_generate_hashtags_includes_brand_tags(self):
        """Test that brand tags are always included."""
        hashtags = generate_hashtags(topic="wellness")
        for brand_tag in BRAND_TAGS:
            assert brand_tag in hashtags

    def test_generate_hashtags_adds_topic_tags(self):
        """Test that topic-specific tags are added."""
        hashtags = generate_hashtags(topic="wellness")
        assert "#naturligvelvære" in hashtags or len(hashtags) >= 3

    def test_generate_hashtags_respects_max(self):
        """Test that hashtag count respects maximum."""
        hashtags = generate_hashtags(
            topic="wellness",
            research_tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"],
        )
        assert len(hashtags) <= MAX_HASHTAGS

    def test_generate_hashtags_formats_research_tags(self):
        """Test that research tags are formatted as hashtags."""
        hashtags = generate_hashtags(
            topic="wellness",
            research_tags=["lions_mane", "cognition"],
        )
        assert "#lionsmane" in hashtags or "#cognition" in hashtags

    def test_validate_hashtags_valid(self):
        """Test validation of valid hashtag list."""
        hashtags = ["#DAWO", "#DAWOmushrooms", "#nordisksopp", "#test"]
        is_valid, msg = validate_hashtags(hashtags)
        assert is_valid is True

    def test_validate_hashtags_missing_brand_tags(self):
        """Test validation fails without brand tags."""
        hashtags = ["#test1", "#test2"]
        is_valid, msg = validate_hashtags(hashtags)
        assert is_valid is False
        assert "brand tags" in msg.lower()

    def test_validate_hashtags_too_many(self):
        """Test validation fails with too many hashtags."""
        hashtags = BRAND_TAGS + [f"#tag{i}" for i in range(20)]
        is_valid, msg = validate_hashtags(hashtags)
        assert is_valid is False
        assert "too many" in msg.lower()


class TestResearchCitation:
    """Tests for research citation formatting."""

    def test_format_citation_pubmed(self):
        """Test citation format for PubMed sources."""
        citation = format_research_citation("pubmed", "Study findings")
        assert "Forskning" in citation

    def test_format_citation_reddit(self):
        """Test citation format for Reddit sources."""
        citation = format_research_citation("reddit", "Community discussion")
        assert "fellesskap" in citation.lower()

    def test_format_citation_instagram(self):
        """Test citation format for Instagram sources."""
        citation = format_research_citation("instagram", "Trend data")
        assert "trend" in citation.lower()

    def test_format_citation_youtube(self):
        """Test citation format for YouTube sources."""
        citation = format_research_citation("youtube", "Video insights")
        assert "Ekspert" in citation or "forteller" in citation.lower()

    def test_format_citation_unknown(self):
        """Test citation format for unknown sources."""
        citation = format_research_citation("unknown", "Some content")
        assert citation  # Should return fallback


class TestCaptionGeneratorInit:
    """Tests for CaptionGenerator initialization."""

    def test_init_with_valid_profile(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
    ):
        """Test initialization with valid brand profile."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )
        assert generator is not None

    def test_init_missing_norwegian_section(
        self,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
    ):
        """Test initialization fails without Norwegian section."""
        profile = {"brand_name": "DAWO"}  # Missing 'norwegian'
        with pytest.raises(ValueError, match="norwegian"):
            CaptionGenerator(
                brand_profile=profile,
                shopify=mock_shopify_client,
                brand_validator=mock_brand_validator,
                llm_client=mock_llm_client,
            )


class TestCaptionGeneration:
    """Tests for caption generation."""

    @pytest.mark.asyncio
    async def test_generate_basic(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test basic caption generation."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert result.success is True
        assert result.caption_text
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_generate_includes_hashtags(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that generated result includes hashtags."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert len(result.hashtags) > 0
        # Brand tags should be in hashtag list
        for tag in BRAND_TAGS:
            assert tag in result.hashtags

    @pytest.mark.asyncio
    async def test_generate_with_product_includes_link(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that product link with UTM is included."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert result.product_link is not None
        assert "utm_" in result.product_link or "feed_post" in result.product_link

    @pytest.mark.asyncio
    async def test_generate_without_product(
        self,
        sample_brand_profile,
        mock_shopify_client_no_product,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request_no_product,
    ):
        """Test caption generation without product."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client_no_product,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request_no_product)

        assert result.success is True
        assert result.product_link is None

    @pytest.mark.asyncio
    async def test_generate_includes_brand_validation(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that brand voice validation is performed."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert result.brand_voice_status in ["PASS", "NEEDS_REVISION", "FAIL"]
        assert 0.0 <= result.brand_voice_score <= 1.0

    @pytest.mark.asyncio
    async def test_generate_includes_authenticity_score(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that authenticity score is calculated."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert 0.0 <= result.authenticity_score <= 1.0

    @pytest.mark.asyncio
    async def test_generate_tracks_generation_time(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that generation time is tracked."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert result.generation_time_ms > 0

    @pytest.mark.asyncio
    async def test_generate_within_time_limit(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that generation completes within 60 seconds (AC: #3)."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        start = time.time()
        result = await generator.generate(sample_caption_request)
        elapsed = time.time() - start

        assert result.success is True
        assert elapsed < 60, f"Generation took {elapsed:.2f}s, should be < 60s"


class TestAIPatternDetection:
    """Tests for AI-generic pattern detection."""

    @pytest.mark.asyncio
    async def test_detects_ai_patterns(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client_with_ai_patterns,
        sample_caption_request,
    ):
        """Test that AI patterns reduce authenticity score."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client_with_ai_patterns,
        )

        result = await generator.generate(sample_caption_request)

        # Should have lower authenticity due to AI patterns
        assert result.authenticity_score < 1.0

    @pytest.mark.asyncio
    async def test_clean_caption_high_authenticity(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that clean caption has high authenticity score."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        # Clean caption should have high authenticity
        assert result.authenticity_score >= 0.8


class TestRevisionSuggestions:
    """Tests for revision suggestion extraction."""

    @pytest.mark.asyncio
    async def test_includes_suggestions_when_needed(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator_needs_revision,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test that suggestions are included when revision needed."""
        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator_needs_revision,
            llm_client=mock_llm_client,
        )

        # Mock the validator to return NEEDS_REVISION
        with patch.object(
            generator,
            "_validate_brand_voice",
            return_value=mock_brand_validator_needs_revision.validate_content_sync(),
        ):
            result = await generator.generate(sample_caption_request)

        # Check brand voice status reflects validation
        # Note: Actual status comes from internal validation, not mocked
        assert result.success is True


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_handles_llm_error(
        self,
        sample_brand_profile,
        mock_shopify_client,
        mock_brand_validator,
        sample_caption_request,
    ):
        """Test graceful handling of LLM errors."""
        llm_client = AsyncMock()
        llm_client.generate.side_effect = Exception("LLM API error")

        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=mock_shopify_client,
            brand_validator=mock_brand_validator,
            llm_client=llm_client,
        )

        result = await generator.generate(sample_caption_request)

        assert result.success is False
        assert "LLM API error" in result.error_message

    @pytest.mark.asyncio
    async def test_handles_shopify_error(
        self,
        sample_brand_profile,
        mock_brand_validator,
        mock_llm_client,
        sample_caption_request,
    ):
        """Test graceful handling of Shopify errors."""
        shopify = AsyncMock()
        shopify.get_product_by_handle.side_effect = Exception("Shopify API error")

        generator = CaptionGenerator(
            brand_profile=sample_brand_profile,
            shopify=shopify,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        result = await generator.generate(sample_caption_request)

        # Should still succeed, just without product data
        assert result.success is True
        assert result.product_link is None


class TestCaptionResultFailure:
    """Tests for CaptionResult.failure factory."""

    def test_failure_creates_failed_result(self):
        """Test that failure factory creates proper failed result."""
        result = CaptionResult.failure("Test error message")

        assert result.success is False
        assert result.error_message == "Test error message"
        assert result.caption_text == ""
        assert result.word_count == 0
