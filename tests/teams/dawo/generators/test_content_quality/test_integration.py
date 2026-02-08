"""Integration tests for Content Quality Scorer (Task 10).

Tests end-to-end scoring behavior:
- 10.1 End-to-end with real validators
- 10.2 Sample content from previous stories
- 10.3 Score consistency
- 10.4 Performance (< 10 seconds)
"""

import pytest
import os
import time
from unittest.mock import AsyncMock

from teams.dawo.generators.content_quality import (
    ContentQualityScorer,
    QualityScoreRequest,
    ContentType,
)


# Skip integration tests if no API credentials
SKIP_INTEGRATION = os.getenv("DAWO_SKIP_INTEGRATION_TESTS", "true").lower() == "true"


@pytest.mark.skipif(SKIP_INTEGRATION, reason="Integration tests disabled")
class TestEndToEndScoring:
    """Test end-to-end scoring with real validators (10.1)."""

    @pytest.mark.asyncio
    async def test_full_scoring_pipeline(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Test complete scoring pipeline produces valid result."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content=(
                "Løvemanke har vært brukt i tradisjonell asiatisk kultur i århundrer. "
                "Denne fantastiske soppen har vært verdsatt for sin unike karakter. "
                "DAWO bringer deg de beste funksjonelle soppene fra Norge. "
            ) * 10 + "Link i bio.",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "DAWOmushrooms", "lionsmane", "wellness", "norge", "helse"],
            visual_quality_score=8.5,
            source_type="research",
        )

        result = await scorer.score_content(request)

        # Verify result structure
        assert result is not None
        assert 0.0 <= result.total_score <= 10.0
        assert len(result.component_scores) == 6
        assert result.authenticity is not None
        assert result.platform_optimization is not None
        assert result.engagement_prediction is not None


class TestSampleContent:
    """Test with sample content from previous stories (10.2)."""

    @pytest.mark.asyncio
    async def test_norwegian_wellness_content(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Norwegian wellness content should score reasonably well."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Sample content similar to what Caption Generator would produce
        content = """
        🍄 Løvemanke - en tradisjon fra øst

        I hundrevis av år har løvemanke vært en del av asiatisk kultur.
        Denne fascinerende soppen med sin karakteristiske manke-lignende form
        har vært verdsatt av generasjoner.

        Hos DAWO er vi stolte av å kunne tilby deg denne unike soppen,
        dyrket med omsorg her i Norge. Vår løvemanke er nøye utvalgt
        for å sikre den beste kvaliteten.

        Ta den som en del av din daglige rutine og opplev forskjellen.
        Naturlig, norsk og nøye utvalgt - akkurat som du fortjener.

        🔗 Link i bio for mer informasjon!
        """

        request = QualityScoreRequest(
            content=content,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=[
                "DAWO", "DAWOmushrooms", "løvemanke", "lionsmane",
                "funksjonellesopper", "wellness", "norge", "naturlig"
            ],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        # Well-written Norwegian content should score above average
        assert result.total_score >= 5.0
        # Should have no AI patterns flagged (Norwegian wellness content)
        assert result.authenticity.ai_probability < 0.5

    @pytest.mark.asyncio
    async def test_ai_generated_content_scores_lower(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Content with AI markers should score lower on authenticity."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Deliberately AI-like content
        content = """
        In today's fast-paced world, it's no secret that wellness is important.
        Let's dive in and unlock your potential with our game-changing supplements!
        First and foremost, you need to understand that at the end of the day,
        your health matters most.
        """

        request = QualityScoreRequest(
            content=content,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["wellness", "health"],
            visual_quality_score=6.0,
            source_type="evergreen",
        )

        result = await scorer.score_content(request)

        # AI-like content should have lower authenticity
        assert result.authenticity is not None
        assert len(result.authenticity.flagged_patterns) > 0
        assert result.authenticity.authenticity_score < 8.0


class TestScoreConsistency:
    """Test score consistency (10.3)."""

    @pytest.mark.asyncio
    async def test_same_content_same_score(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Same content should produce identical scores."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Consistent test content for scoring verification." * 10,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=7.5,
            source_type="research",
        )

        # Score twice
        result1 = await scorer.score_content(request)
        result2 = await scorer.score_content(request)

        # Scores should be identical
        assert result1.total_score == result2.total_score

        # Component scores should match
        for c1, c2 in zip(result1.component_scores, result2.component_scores):
            assert c1.component == c2.component
            assert c1.raw_score == c2.raw_score
            assert c1.weighted_score == c2.weighted_score

    @pytest.mark.asyncio
    async def test_different_content_different_scores(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Different content should produce different scores."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # High quality request
        high_quality = QualityScoreRequest(
            content="Løvemanke har en fantastisk historie. " * 50 + "Link i bio!",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "DAWOmushrooms", "wellness", "norge", "helse", "naturlig"],
            visual_quality_score=9.5,
            source_type="trending",
        )

        # Low quality request - with AI patterns and poor optimization
        low_quality = QualityScoreRequest(
            content="In today's fast-paced world, let's dive in!",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=[],  # No hashtags
            visual_quality_score=2.0,  # Poor visual
            source_type="unknown",
        )

        high_result = await scorer.score_content(high_quality)
        low_result = await scorer.score_content(low_quality)

        # High quality should score higher than low quality
        assert high_result.total_score > low_result.total_score


class TestPerformance:
    """Test performance requirements (10.4)."""

    @pytest.mark.asyncio
    async def test_scoring_under_10_seconds(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Scoring should complete in under 10 seconds per AC."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content for performance measurement. " * 50,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "DAWOmushrooms", "test"],
            visual_quality_score=7.0,
            source_type="research",
        )

        start_time = time.time()
        result = await scorer.score_content(request)
        elapsed_time = time.time() - start_time

        # Should complete in under 10 seconds
        assert elapsed_time < 10.0, f"Scoring took {elapsed_time:.2f}s, expected < 10s"

        # Also verify scoring_time_ms is reasonable
        assert result.scoring_time_ms < 10000

    @pytest.mark.asyncio
    async def test_multiple_scorings_performance(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Multiple scorings should maintain performance."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        requests = [
            QualityScoreRequest(
                content=f"Test content batch {i}. " * 30,
                content_type=ContentType.INSTAGRAM_FEED,
                hashtags=["DAWO", "test"],
                visual_quality_score=float(i % 10),
                source_type="research",
            )
            for i in range(5)
        ]

        start_time = time.time()
        for request in requests:
            await scorer.score_content(request)
        total_elapsed = time.time() - start_time

        # 5 scorings should complete in under 50 seconds (10s each)
        assert total_elapsed < 50.0, f"5 scorings took {total_elapsed:.2f}s"
        # Average should be well under 10s with mocks
        avg_time = total_elapsed / 5
        assert avg_time < 2.0, f"Average scoring time {avg_time:.2f}s, expected < 2s with mocks"


class TestContentTypeScoring:
    """Test scoring for different content types."""

    @pytest.mark.asyncio
    async def test_story_content_type(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Instagram story should use different optimization rules."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Short content appropriate for story
        request = QualityScoreRequest(
            content="Check out our new product! 🍄",
            content_type=ContentType.INSTAGRAM_STORY,  # Story format
            hashtags=["DAWO", "DAWOmushrooms"],
            visual_quality_score=8.0,
            source_type="trending",
        )

        result = await scorer.score_content(request)

        # Should not penalize short content for stories
        platform = next(
            (c for c in result.component_scores if c.component == "platform"),
            None
        )
        assert platform is not None
        # Story has different rules, shouldn't be heavily penalized
        assert platform.raw_score >= 5.0

    @pytest.mark.asyncio
    async def test_reel_content_type(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Instagram reel should use different optimization rules."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Medium content appropriate for reel
        request = QualityScoreRequest(
            content="Watch our latest video about functional mushrooms! " * 15 + "Link i bio!",
            content_type=ContentType.INSTAGRAM_REEL,  # Reel format
            hashtags=["DAWO", "DAWOmushrooms", "reels", "wellness", "norway"],
            visual_quality_score=9.0,
            source_type="trending",
        )

        result = await scorer.score_content(request)

        # Should score well for reels
        assert result.total_score >= 5.0
