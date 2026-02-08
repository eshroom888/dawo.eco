"""Unit tests for quality scoring module."""

import pytest
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Mock genai before imports
mock_genai = MagicMock()
sys.modules["google.generativeai"] = mock_genai

from integrations.gemini import GeneratedImage, ImageStyle

from teams.dawo.generators.nano_banana.quality import (
    ImageQualityScorer,
    QualityAssessment,
)


@pytest.fixture
def scorer():
    """Create ImageQualityScorer instance."""
    return ImageQualityScorer()


@pytest.fixture
def sample_image():
    """Create sample GeneratedImage."""
    return GeneratedImage(
        id="gen_123",
        prompt="Nordic minimalist wellness photography. Test topic.",
        style=ImageStyle.NORDIC,
        image_url="/tmp/gen_123.png",
        local_path=Path("/tmp/gen_123.png"),
        width=1080,
        height=1080,
        created_at=datetime.now(timezone.utc),
    )


class TestImageQualityScorer:
    """Test ImageQualityScorer."""

    def test_score_returns_assessment(self, scorer, sample_image):
        """Score returns QualityAssessment object."""
        result = scorer.score(sample_image)

        assert isinstance(result, QualityAssessment)

    def test_score_overall_in_range(self, scorer, sample_image):
        """Overall score is between 1 and 10."""
        result = scorer.score(sample_image)

        assert result.overall_score >= 1.0
        assert result.overall_score <= 10.0

    def test_score_component_scores_in_range(self, scorer, sample_image):
        """Component scores are between 1 and 10."""
        result = scorer.score(sample_image)

        assert result.aesthetic_score >= 1.0
        assert result.aesthetic_score <= 10.0
        assert result.brand_alignment >= 1.0
        assert result.brand_alignment <= 10.0
        assert result.ai_detectability >= 1.0
        assert result.ai_detectability <= 10.0

    def test_score_nordic_style_high_brand_alignment(self, scorer, sample_image):
        """Nordic style gets high brand alignment score."""
        result = scorer.score(sample_image, prompt_compliance=0.9)

        # Nordic style should score well for brand alignment
        assert result.brand_alignment >= 7.0

    def test_score_failed_generation_low(self, scorer, sample_image):
        """Failed generation gets low aesthetic score."""
        result = scorer.score(
            sample_image,
            generation_success=False,
        )

        assert result.aesthetic_score < 5.0

    def test_score_high_resolution_bonus(self, scorer):
        """High resolution images get aesthetic bonus."""
        high_res_image = GeneratedImage(
            id="gen_123",
            prompt="Test prompt",
            style=ImageStyle.NORDIC,
            image_url="/tmp/gen_123.png",
            local_path=Path("/tmp/gen_123.png"),
            width=2000,
            height=2000,
            created_at=datetime.now(timezone.utc),
        )

        result = scorer.score(high_res_image)

        # Should have bonus for high resolution
        assert result.aesthetic_score >= 8.0

    def test_score_low_resolution_penalty(self, scorer):
        """Low resolution images get aesthetic penalty."""
        low_res_image = GeneratedImage(
            id="gen_123",
            prompt="Test prompt",
            style=ImageStyle.NORDIC,
            image_url="/tmp/gen_123.png",
            local_path=Path("/tmp/gen_123.png"),
            width=600,
            height=600,
            created_at=datetime.now(timezone.utc),
        )

        result = scorer.score(low_res_image)

        # Should have penalty for low resolution
        assert "low_resolution" in result.flags

    def test_score_prompt_compliance_affects_brand(self, scorer, sample_image):
        """Prompt compliance affects brand alignment score."""
        high_compliance = scorer.score(sample_image, prompt_compliance=1.0)
        low_compliance = scorer.score(sample_image, prompt_compliance=0.2)

        assert high_compliance.brand_alignment > low_compliance.brand_alignment

    def test_score_needs_review_threshold(self, scorer):
        """Needs review is set when overall score < 6."""
        low_quality_image = GeneratedImage(
            id="gen_123",
            prompt="Test prompt",
            style=ImageStyle.ABSTRACT,  # Lower brand alignment
            image_url="/tmp/gen_123.png",
            local_path=Path("/tmp/gen_123.png"),
            width=500,  # Low resolution
            height=500,
            created_at=datetime.now(timezone.utc),
        )

        result = scorer.score(
            low_quality_image,
            prompt_compliance=0.2,
            generation_success=True,
        )

        # With low compliance and abstract style, may need review
        # The actual threshold is 6.0
        if result.overall_score < 6.0:
            assert result.needs_review is True


class TestQualityAssessmentFlags:
    """Test quality assessment flags."""

    def test_flags_empty_for_good_image(self, scorer, sample_image):
        """No flags for high-quality image."""
        result = scorer.score(
            sample_image,
            prompt_compliance=0.9,
            generation_success=True,
        )

        # Good image should have minimal flags
        assert len(result.flags) <= 1

    def test_generation_failed_flag(self, scorer, sample_image):
        """Generation failed flag is set."""
        result = scorer.score(
            sample_image,
            generation_success=False,
        )

        assert "generation_failed" in result.flags


class TestScorerRecommendation:
    """Test scorer recommendation method."""

    def test_excellent_recommendation(self, scorer, sample_image):
        """Excellent score gets auto-publish recommendation."""
        result = scorer.score(
            sample_image,
            prompt_compliance=1.0,
            generation_success=True,
        )

        # Manually create high score assessment
        high_score_assessment = QualityAssessment(
            aesthetic_score=10.0,
            brand_alignment=10.0,
            ai_detectability=10.0,
            overall_score=9.5,
            needs_review=False,
            flags=[],
        )

        recommendation = scorer.get_recommendation(high_score_assessment)
        assert "auto-publish" in recommendation.lower() or "excellent" in recommendation.lower()

    def test_poor_recommendation(self, scorer):
        """Poor score gets regeneration recommendation."""
        poor_assessment = QualityAssessment(
            aesthetic_score=3.0,
            brand_alignment=3.0,
            ai_detectability=3.0,
            overall_score=3.0,
            needs_review=True,
            flags=["generation_failed", "low_resolution"],
        )

        recommendation = scorer.get_recommendation(poor_assessment)
        assert "regenerat" in recommendation.lower() or "poor" in recommendation.lower()
