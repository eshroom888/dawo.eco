"""Unit tests for Content Quality Scorer scoring components (Task 9).

Tests each scoring component:
- Compliance scoring (9.1)
- Brand voice scoring (9.2)
- Visual quality scoring (9.3)
- Platform optimization (9.4)
- Engagement prediction (9.5)
- Authenticity scoring (9.6)
- Weighted aggregation (9.7)
- Edge cases (9.8)
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from teams.dawo.generators.content_quality import (
    ContentQualityScorer,
    QualityScoreRequest,
    QualityScoreResult,
    ContentType,
    DEFAULT_WEIGHTS,
)
from teams.dawo.validators.eu_compliance import (
    ContentComplianceCheck,
    OverallStatus,
)
from teams.dawo.validators.brand_voice import (
    BrandValidationResult,
    ValidationStatus,
)


class TestComplianceScoring:
    """Test compliance scoring for each status (9.1)."""

    @pytest.mark.asyncio
    async def test_compliant_status_scores_10(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """COMPLIANT status should score 10.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        # Find compliance component
        compliance = next(
            (c for c in result.component_scores if c.component == "compliance"),
            None
        )
        assert compliance is not None
        assert compliance.raw_score == 10.0

    @pytest.mark.asyncio
    async def test_warning_status_scores_8(
        self, mock_compliance_checker_warning, mock_brand_validator, mock_llm_client
    ):
        """WARNING status should score 8.0 (full - 2 per AC)."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker_warning,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        compliance = next(
            (c for c in result.component_scores if c.component == "compliance"),
            None
        )
        assert compliance is not None
        assert compliance.raw_score == 8.0

    @pytest.mark.asyncio
    async def test_rejected_status_scores_0(
        self, mock_compliance_checker_rejected, mock_brand_validator, mock_llm_client
    ):
        """REJECTED status should score 0.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker_rejected,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        compliance = next(
            (c for c in result.component_scores if c.component == "compliance"),
            None
        )
        assert compliance is not None
        assert compliance.raw_score == 0.0

    @pytest.mark.asyncio
    async def test_uses_precomputed_compliance(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should use pre-computed compliance check if provided."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        precomputed = ContentComplianceCheck(
            overall_status=OverallStatus.REJECTED,
            flagged_phrases=[],
            compliance_score=0.0,
            llm_enhanced=False,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
            compliance_check=precomputed,  # Pre-computed
        )

        result = await scorer.score_content(request)

        compliance = next(
            (c for c in result.component_scores if c.component == "compliance"),
            None
        )
        # Should use precomputed REJECTED, not mock's COMPLIANT
        assert compliance.raw_score == 0.0
        # Mock should not have been called
        mock_compliance_checker.check_content.assert_not_called()


class TestBrandVoiceScoring:
    """Test brand voice scoring with mock validator (9.2)."""

    @pytest.mark.asyncio
    async def test_pass_status_scores_10(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """PASS status should score 10.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        brand = next(
            (c for c in result.component_scores if c.component == "brand_voice"),
            None
        )
        assert brand is not None
        assert brand.raw_score == 10.0

    @pytest.mark.asyncio
    async def test_needs_revision_status_scores_6(
        self, mock_compliance_checker, mock_brand_validator_needs_revision, mock_llm_client
    ):
        """NEEDS_REVISION status should score 6.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator_needs_revision,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        brand = next(
            (c for c in result.component_scores if c.component == "brand_voice"),
            None
        )
        assert brand is not None
        assert brand.raw_score == 6.0

    @pytest.mark.asyncio
    async def test_fail_status_scores_2(
        self, mock_compliance_checker, mock_brand_validator_fail, mock_llm_client
    ):
        """FAIL status should score 2.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator_fail,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        brand = next(
            (c for c in result.component_scores if c.component == "brand_voice"),
            None
        )
        assert brand is not None
        assert brand.raw_score == 2.0


class TestVisualQualityScoring:
    """Test visual quality scoring with various inputs (9.3)."""

    @pytest.mark.asyncio
    async def test_high_visual_quality(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """High visual quality input should be passed through."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=9.5,  # High quality
            source_type="research",
        )

        result = await scorer.score_content(request)

        visual = next(
            (c for c in result.component_scores if c.component == "visual_quality"),
            None
        )
        assert visual is not None
        assert visual.raw_score == 9.5

    @pytest.mark.asyncio
    async def test_low_visual_quality(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Low visual quality input should be passed through."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=3.0,  # Low quality
            source_type="research",
        )

        result = await scorer.score_content(request)

        visual = next(
            (c for c in result.component_scores if c.component == "visual_quality"),
            None
        )
        assert visual is not None
        assert visual.raw_score == 3.0

    @pytest.mark.asyncio
    async def test_clamps_above_10(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Visual quality above 10 should be clamped to 10."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=15.0,  # Invalid - too high
            source_type="research",
        )

        result = await scorer.score_content(request)

        visual = next(
            (c for c in result.component_scores if c.component == "visual_quality"),
            None
        )
        assert visual is not None
        assert visual.raw_score == 10.0

    @pytest.mark.asyncio
    async def test_clamps_below_0(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Visual quality below 0 should be clamped to 0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=-5.0,  # Invalid - negative
            source_type="research",
        )

        result = await scorer.score_content(request)

        visual = next(
            (c for c in result.component_scores if c.component == "visual_quality"),
            None
        )
        assert visual is not None
        assert visual.raw_score == 0.0


class TestPlatformOptimization:
    """Test platform optimization scoring (9.4)."""

    @pytest.mark.asyncio
    async def test_optimal_hashtag_count(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Optimal hashtag count (11) should score high."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Need ~200 words for optimal length. "Test content here now " * 50 = 200 words
        request = QualityScoreRequest(
            content="Test content here now " * 50 + " Link i bio.",  # ~200 words + CTA
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "DAWOmushrooms"] + [f"tag{i}" for i in range(9)],  # 11 hashtags
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        platform = next(
            (c for c in result.component_scores if c.component == "platform"),
            None
        )
        assert platform is not None
        assert platform.raw_score >= 7.5  # Should be reasonably high (hashtags optimal, has CTA)

    @pytest.mark.asyncio
    async def test_too_few_hashtags(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Too few hashtags should score lower and suggest adding more."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content " * 40,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["mushrooms"],  # Only 1 hashtag
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        platform = next(
            (c for c in result.component_scores if c.component == "platform"),
            None
        )
        assert platform is not None
        suggestions = platform.details.get("suggestions", [])
        assert any("hashtag" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_missing_brand_hashtags(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Missing brand hashtags should suggest adding them."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content " * 40,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["mushrooms", "wellness", "health"],  # No brand hashtags
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        platform = next(
            (c for c in result.component_scores if c.component == "platform"),
            None
        )
        assert platform is not None
        suggestions = platform.details.get("suggestions", [])
        assert any("brand hashtag" in s.lower() or "dawo" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_caption_too_short(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Too short caption should suggest lengthening."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Short content",  # Very short
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        platform = next(
            (c for c in result.component_scores if c.component == "platform"),
            None
        )
        assert platform is not None
        suggestions = platform.details.get("suggestions", [])
        assert any("short" in s.lower() for s in suggestions)


class TestEngagementPrediction:
    """Test engagement prediction scoring (9.5)."""

    @pytest.mark.asyncio
    async def test_trending_source_scores_high(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Trending source type should score higher."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="trending",  # High engagement source
        )

        result = await scorer.score_content(request)

        engagement = next(
            (c for c in result.component_scores if c.component == "engagement"),
            None
        )
        assert engagement is not None
        assert engagement.raw_score >= 7.5

    @pytest.mark.asyncio
    async def test_evergreen_source_scores_lower(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Evergreen source type should score lower than trending."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="evergreen",  # Lower engagement source
        )

        result = await scorer.score_content(request)

        engagement = next(
            (c for c in result.component_scores if c.component == "engagement"),
            None
        )
        assert engagement is not None
        assert engagement.raw_score < 7.0

    @pytest.mark.asyncio
    async def test_default_fallback_for_unknown_source(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Unknown source type should fallback to default score."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="unknown_source",  # Unknown
        )

        result = await scorer.score_content(request)

        engagement = next(
            (c for c in result.component_scores if c.component == "engagement"),
            None
        )
        assert engagement is not None
        assert engagement.raw_score == 5.0  # Default fallback


class TestAuthenticityScoring:
    """Test authenticity scoring for AI patterns (9.6)."""

    @pytest.mark.asyncio
    async def test_human_like_content_scores_high(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Human-like content without AI patterns should score high."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Natural Norwegian content without AI markers
        content = """
        Løvemanke har vært en del av asiatisk tradisjon i århundrer.
        Vi hos DAWO er stolte av å bringe denne fantastiske soppen til Norge.
        """

        request = QualityScoreRequest(
            content=content,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        authenticity = next(
            (c for c in result.component_scores if c.component == "authenticity"),
            None
        )
        assert authenticity is not None
        assert authenticity.raw_score >= 8.0

    @pytest.mark.asyncio
    async def test_ai_patterns_reduce_score(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Content with AI patterns should score lower."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Content with obvious AI markers
        content = """
        In today's fast-paced world, it's no secret that mushrooms are game-changers.
        Let's dive in and unlock your potential!
        """

        request = QualityScoreRequest(
            content=content,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        authenticity = next(
            (c for c in result.component_scores if c.component == "authenticity"),
            None
        )
        assert authenticity is not None
        assert authenticity.raw_score < 8.0  # Should be lower
        # Check that patterns were flagged
        assert result.authenticity is not None
        assert len(result.authenticity.flagged_patterns) > 0

    @pytest.mark.asyncio
    async def test_norwegian_ai_patterns_detected(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Norwegian AI patterns should also be detected."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        # Content with Norwegian AI markers
        content = """
        I dagens moderne verden er det ingen hemmelighet at sopp er fantastisk.
        La oss dykke inn i denne fantastiske verden.
        """

        request = QualityScoreRequest(
            content=content,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        authenticity = next(
            (c for c in result.component_scores if c.component == "authenticity"),
            None
        )
        assert authenticity is not None
        assert authenticity.raw_score < 10.0  # Should detect patterns


class TestWeightedAggregation:
    """Test weighted aggregation with custom weights (9.7)."""

    @pytest.mark.asyncio
    async def test_default_weights_sum_to_1(self):
        """Default weights should sum to 1.0."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert 0.99 <= total <= 1.01

    @pytest.mark.asyncio
    async def test_custom_weights_applied(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Custom weights should affect component contributions."""
        # Give compliance 100% weight
        custom_weights = {
            "compliance": 1.0,
            "brand_voice": 0.0,
            "visual_quality": 0.0,
            "platform": 0.0,
            "engagement": 0.0,
            "authenticity": 0.0,
        }

        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,  # Returns COMPLIANT = 10
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
            weights=custom_weights,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=0.0,  # This shouldn't matter with 0 weight
            source_type="research",
        )

        result = await scorer.score_content(request)

        # With only compliance at weight 1.0 and COMPLIANT status, total should be 10
        assert result.total_score == 10.0


class TestEdgeCases:
    """Test edge cases and boundary values (9.8)."""

    @pytest.mark.asyncio
    async def test_score_rounded_to_1_decimal(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Total score should be rounded to 1 decimal place."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.123456,
            source_type="research",
        )

        result = await scorer.score_content(request)

        # Check that score has at most 1 decimal place
        assert result.total_score == round(result.total_score, 1)

    @pytest.mark.asyncio
    async def test_total_score_clamped_to_10(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Total score should never exceed 10.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Perfect content " * 40,
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "DAWOmushrooms"] + [f"tag{i}" for i in range(9)],
            visual_quality_score=10.0,
            source_type="trending",
        )

        result = await scorer.score_content(request)

        assert result.total_score <= 10.0

    @pytest.mark.asyncio
    async def test_total_score_clamped_to_0(
        self, mock_compliance_checker_rejected, mock_brand_validator_fail, mock_llm_client
    ):
        """Total score should never go below 0.0."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker_rejected,
            brand_validator=mock_brand_validator_fail,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="In today's fast-paced world, it's no secret that we should unlock your potential!",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=[],
            visual_quality_score=0.0,
            source_type="unknown",
        )

        result = await scorer.score_content(request)

        assert result.total_score >= 0.0

    @pytest.mark.asyncio
    async def test_empty_content(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Empty content should still produce a valid result."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=[],
            visual_quality_score=5.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        assert result is not None
        assert 0.0 <= result.total_score <= 10.0

    @pytest.mark.asyncio
    async def test_scoring_time_recorded(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Scoring time should be recorded in result."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        assert result.scoring_time_ms >= 0

    @pytest.mark.asyncio
    async def test_all_component_scores_present(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """All 6 component scores should be present."""
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )

        request = QualityScoreRequest(
            content="Test content",
            content_type=ContentType.INSTAGRAM_FEED,
            hashtags=["DAWO", "test"],
            visual_quality_score=8.0,
            source_type="research",
        )

        result = await scorer.score_content(request)

        components = [c.component for c in result.component_scores]
        expected = ["compliance", "brand_voice", "visual_quality", "platform", "engagement", "authenticity"]

        for exp in expected:
            assert exp in components, f"Missing component: {exp}"
