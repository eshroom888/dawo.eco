"""Test package structure and exports for Content Quality Scorer (Task 1).

Tests that:
- Package can be imported
- Protocol is exported
- Main class is exported
- All schema types are exported
- Constructor injection pattern works
"""

import pytest


class TestPackageImports:
    """Test that package exports are correct."""

    def test_can_import_package(self):
        """Package should be importable."""
        from teams.dawo.generators import content_quality
        assert content_quality is not None

    def test_exports_content_quality_scorer(self):
        """ContentQualityScorer class should be exported."""
        from teams.dawo.generators.content_quality import ContentQualityScorer
        assert ContentQualityScorer is not None

    def test_exports_protocol(self):
        """ContentQualityScorerProtocol should be exported."""
        from teams.dawo.generators.content_quality import ContentQualityScorerProtocol
        assert ContentQualityScorerProtocol is not None

    def test_exports_quality_score_request(self):
        """QualityScoreRequest dataclass should be exported."""
        from teams.dawo.generators.content_quality import QualityScoreRequest
        assert QualityScoreRequest is not None

    def test_exports_quality_score_result(self):
        """QualityScoreResult dataclass should be exported."""
        from teams.dawo.generators.content_quality import QualityScoreResult
        assert QualityScoreResult is not None

    def test_exports_component_score(self):
        """ComponentScore dataclass should be exported."""
        from teams.dawo.generators.content_quality import ComponentScore
        assert ComponentScore is not None

    def test_exports_content_type_enum(self):
        """ContentType enum should be exported."""
        from teams.dawo.generators.content_quality import ContentType
        assert ContentType is not None
        # Verify enum values
        assert ContentType.INSTAGRAM_FEED.value == "instagram_feed"
        assert ContentType.INSTAGRAM_STORY.value == "instagram_story"
        assert ContentType.INSTAGRAM_REEL.value == "instagram_reel"

    def test_exports_authenticity_result(self):
        """AuthenticityResult dataclass should be exported."""
        from teams.dawo.generators.content_quality import AuthenticityResult
        assert AuthenticityResult is not None

    def test_exports_platform_optimization_result(self):
        """PlatformOptimizationResult dataclass should be exported."""
        from teams.dawo.generators.content_quality import PlatformOptimizationResult
        assert PlatformOptimizationResult is not None

    def test_exports_engagement_prediction(self):
        """EngagementPrediction dataclass should be exported."""
        from teams.dawo.generators.content_quality import EngagementPrediction
        assert EngagementPrediction is not None

    def test_exports_default_weights(self):
        """DEFAULT_WEIGHTS constant should be exported."""
        from teams.dawo.generators.content_quality import DEFAULT_WEIGHTS
        assert DEFAULT_WEIGHTS is not None
        assert isinstance(DEFAULT_WEIGHTS, dict)
        # Verify weights sum to 1.0
        total = sum(DEFAULT_WEIGHTS.values())
        assert 0.99 <= total <= 1.01, f"Weights should sum to 1.0, got {total}"

    def test_all_list_complete(self):
        """__all__ should include all public exports."""
        from teams.dawo.generators.content_quality import __all__
        expected_exports = [
            "ContentQualityScorer",
            "ContentQualityScorerProtocol",
            "QualityScoreRequest",
            "QualityScoreResult",
            "ComponentScore",
            "ContentType",
            "AuthenticityResult",
            "PlatformOptimizationResult",
            "EngagementPrediction",
            "DEFAULT_WEIGHTS",
        ]
        for export in expected_exports:
            assert export in __all__, f"{export} should be in __all__"


class TestConstructorInjection:
    """Test constructor injection pattern."""

    def test_accepts_compliance_checker(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should accept EUComplianceChecker via constructor."""
        from teams.dawo.generators.content_quality import ContentQualityScorer

        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )
        assert scorer is not None

    def test_accepts_brand_validator(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should accept BrandVoiceValidator via constructor."""
        from teams.dawo.generators.content_quality import ContentQualityScorer

        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )
        assert scorer is not None

    def test_accepts_llm_client(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should accept LLMClient via constructor."""
        from teams.dawo.generators.content_quality import ContentQualityScorer

        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )
        assert scorer is not None

    def test_accepts_optional_weights(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should accept optional custom weights."""
        from teams.dawo.generators.content_quality import ContentQualityScorer

        custom_weights = {
            "compliance": 0.30,
            "brand_voice": 0.25,
            "visual_quality": 0.15,
            "platform": 0.10,
            "engagement": 0.10,
            "authenticity": 0.10,
        }
        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
            weights=custom_weights,
        )
        assert scorer is not None

    def test_validates_weights_sum(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should raise ValueError if weights don't sum to 1.0."""
        from teams.dawo.generators.content_quality import ContentQualityScorer

        invalid_weights = {
            "compliance": 0.50,
            "brand_voice": 0.50,
            "visual_quality": 0.50,  # Sum = 1.5
            "platform": 0.0,
            "engagement": 0.0,
            "authenticity": 0.0,
        }
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ContentQualityScorer(
                compliance_checker=mock_compliance_checker,
                brand_validator=mock_brand_validator,
                llm_client=mock_llm_client,
                weights=invalid_weights,
            )


class TestProtocolCompliance:
    """Test that ContentQualityScorer implements protocol."""

    def test_has_score_content_method(
        self, mock_compliance_checker, mock_brand_validator, mock_llm_client
    ):
        """Should have score_content async method."""
        from teams.dawo.generators.content_quality import ContentQualityScorer

        scorer = ContentQualityScorer(
            compliance_checker=mock_compliance_checker,
            brand_validator=mock_brand_validator,
            llm_client=mock_llm_client,
        )
        assert hasattr(scorer, "score_content")
        assert callable(scorer.score_content)
