"""Tests for enrichment configuration.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 1.4: Test EnrichmentConfig dataclass
"""

import pytest


class TestEnrichmentConfig:
    """Tests for EnrichmentConfig dataclass."""

    def test_create_config_with_defaults(self) -> None:
        """Test creating config with default values."""
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()

        assert config.min_confidence_threshold == 5.0
        assert config.website_timeout_seconds == 5
        assert config.website_rate_limit_per_second == 1.0
        assert config.batch_size == 10

    def test_create_config_with_custom_values(self) -> None:
        """Test creating config with custom values."""
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig(
            min_confidence_threshold=7.0,
            website_timeout_seconds=10,
            batch_size=20,
        )

        assert config.min_confidence_threshold == 7.0
        assert config.website_timeout_seconds == 10
        assert config.batch_size == 20

    def test_config_has_dawo_product_keywords(self) -> None:
        """Test config contains DAWO product keywords for detection."""
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()

        assert "dawo" in config.dawo_product_keywords
        assert len(config.dawo_product_keywords) >= 3

    def test_config_has_scoring_weights(self) -> None:
        """Test config contains scoring weight configuration."""
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()

        assert config.score_weights.verified_email == 2.0
        assert config.score_weights.business_description == 2.0
        assert config.score_weights.social_presence == 1.0
        assert config.score_weights.decision_maker == 1.0

    def test_config_has_lead_score_weights(self) -> None:
        """Test config contains lead score weight configuration."""
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()

        # Industry relevance (0-30)
        assert config.lead_score_weights.industry_relevance_max == 30
        # Company size fit (0-20)
        assert config.lead_score_weights.company_size_max == 20
        # Geographic fit (0-20)
        assert config.lead_score_weights.geographic_max == 20


class TestConfidenceScoreWeights:
    """Tests for ConfidenceScoreWeights dataclass."""

    def test_create_weights_with_defaults(self) -> None:
        """Test creating weights with default values."""
        from teams.dawo.leads.enrichment.config import ConfidenceScoreWeights

        weights = ConfidenceScoreWeights()

        assert weights.verified_email == 2.0
        assert weights.business_description == 2.0
        assert weights.social_presence == 1.0
        assert weights.decision_maker == 1.0
        assert weights.industry_match == 1.0
        assert weights.product_categories == 1.0
        assert weights.personalization_hooks == 1.0
        assert weights.website_accessible == 1.0

    def test_max_possible_score(self) -> None:
        """Test calculating maximum possible score."""
        from teams.dawo.leads.enrichment.config import ConfidenceScoreWeights

        weights = ConfidenceScoreWeights()
        max_score = (
            weights.verified_email
            + weights.business_description
            + weights.social_presence
            + weights.decision_maker
            + weights.industry_match
            + weights.product_categories
            + weights.personalization_hooks
            + weights.website_accessible
        )

        assert max_score == 10.0


class TestLeadScoreWeights:
    """Tests for LeadScoreWeights dataclass."""

    def test_create_weights_with_defaults(self) -> None:
        """Test creating weights with default values."""
        from teams.dawo.leads.enrichment.config import LeadScoreWeights

        weights = LeadScoreWeights()

        assert weights.industry_relevance_max == 30
        assert weights.company_size_max == 20
        assert weights.geographic_max == 20
        assert weights.engagement_potential_max == 15
        assert weights.data_completeness_max == 15

    def test_total_max_is_100(self) -> None:
        """Test that total max score is 100."""
        from teams.dawo.leads.enrichment.config import LeadScoreWeights

        weights = LeadScoreWeights()
        total = (
            weights.industry_relevance_max
            + weights.company_size_max
            + weights.geographic_max
            + weights.engagement_potential_max
            + weights.data_completeness_max
        )

        assert total == 100


class TestEnrichmentConstants:
    """Tests for module constants."""

    def test_min_confidence_threshold_constant(self) -> None:
        """Test MIN_CONFIDENCE_THRESHOLD constant."""
        from teams.dawo.leads.enrichment.config import MIN_CONFIDENCE_THRESHOLD

        assert MIN_CONFIDENCE_THRESHOLD == 5

    def test_default_batch_size_constant(self) -> None:
        """Test DEFAULT_BATCH_SIZE constant."""
        from teams.dawo.leads.enrichment.config import DEFAULT_BATCH_SIZE

        assert DEFAULT_BATCH_SIZE == 10

    def test_website_timeout_constant(self) -> None:
        """Test DEFAULT_WEBSITE_TIMEOUT constant."""
        from teams.dawo.leads.enrichment.config import DEFAULT_WEBSITE_TIMEOUT

        assert DEFAULT_WEBSITE_TIMEOUT == 5
