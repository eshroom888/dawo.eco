"""Tests for EnrichmentScorer.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 6: Implement Enrichment Scoring
"""

import pytest
from uuid import uuid4


class TestEnrichmentScorerInit:
    """Tests for EnrichmentScorer initialization."""

    def test_creates_instance_with_defaults(self) -> None:
        """Test EnrichmentScorer can be instantiated with defaults."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        assert scorer is not None
        assert scorer._config is config


class TestCalculateConfidence:
    """Tests for calculate_confidence method."""

    def test_confidence_for_verified_email(self) -> None:
        """Test confidence score includes verified email weight."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            CompanyEnrichment,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        result = EnrichmentResult(
            lead_id=uuid4(),
            company_enrichment=CompanyEnrichment(
                domain="test.com",
                email_patterns=["verified@test.com"],
            ),
        )

        score, breakdown = scorer.calculate_confidence(result, has_verified_email=True)

        assert breakdown.verified_email == 2.0
        assert score >= 2.0

    def test_confidence_for_business_description(self) -> None:
        """Test confidence includes business description weight."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            WebsiteAnalysis,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        result = EnrichmentResult(
            lead_id=uuid4(),
            website_analysis=WebsiteAnalysis(
                domain="test.com",
                accessible=True,
                description="Health food store in Oslo",
            ),
        )

        score, breakdown = scorer.calculate_confidence(result)

        assert breakdown.business_description == 2.0
        assert breakdown.website_accessible == 1.0

    def test_confidence_for_social_presence(self) -> None:
        """Test confidence includes social media presence weight."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            SocialProfile,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        result = EnrichmentResult(
            lead_id=uuid4(),
            social_profiles=[
                SocialProfile(platform="instagram", followers=1000),
            ],
        )

        score, breakdown = scorer.calculate_confidence(result)

        assert breakdown.social_presence == 1.0

    def test_confidence_for_personalization_hooks(self) -> None:
        """Test confidence includes personalization hooks weight."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            PersonalizationHook,
            PersonalizationHookType,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        result = EnrichmentResult(
            lead_id=uuid4(),
            personalization_hooks=[
                PersonalizationHook(
                    hook_type=PersonalizationHookType.FOCUS,
                    detail="Strong organic focus",
                ),
            ],
        )

        score, breakdown = scorer.calculate_confidence(result)

        assert breakdown.personalization_hooks == 1.0

    def test_maximum_confidence_is_10(self) -> None:
        """Test maximum confidence score is 10."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            WebsiteAnalysis,
            BusinessInsights,
            CompanyEnrichment,
            SocialProfile,
            PersonalizationHook,
            PersonalizationHookType,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        # Full enrichment result with everything
        result = EnrichmentResult(
            lead_id=uuid4(),
            website_analysis=WebsiteAnalysis(
                domain="test.com",
                accessible=True,
                description="Description",
            ),
            business_insights=BusinessInsights(
                focus_areas=["organic"],
                product_categories=["supplements"],
            ),
            company_enrichment=CompanyEnrichment(
                domain="test.com",
                industry="Health & Wellness",
            ),
            social_profiles=[
                SocialProfile(platform="instagram", followers=1000),
            ],
            personalization_hooks=[
                PersonalizationHook(
                    hook_type=PersonalizationHookType.FOCUS,
                    detail="Organic focus",
                ),
            ],
        )

        score, breakdown = scorer.calculate_confidence(
            result,
            has_verified_email=True,
            has_decision_maker=True,
        )

        assert score == 10.0


class TestCalculateLeadScore:
    """Tests for calculate_lead_score method."""

    def test_lead_score_includes_industry_relevance(self) -> None:
        """Test lead score includes industry relevance."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            CompanyEnrichment,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        result = EnrichmentResult(
            lead_id=uuid4(),
            company_enrichment=CompanyEnrichment(
                domain="test.com",
                industry="Health & Wellness",
            ),
        )

        score = scorer.calculate_lead_score(result, industry="Health & Wellness")

        assert score >= 20  # Industry match gives significant points

    def test_lead_score_includes_geographic_fit(self) -> None:
        """Test lead score includes geographic fit."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        result = EnrichmentResult(lead_id=uuid4())

        score = scorer.calculate_lead_score(result, country="Norway")

        assert score >= 15  # Nordic country gives geographic points

    def test_lead_score_maximum_is_100(self) -> None:
        """Test maximum lead score is 100."""
        from teams.dawo.leads.enrichment.scorer import EnrichmentScorer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            CompanyEnrichment,
            WebsiteAnalysis,
            BusinessInsights,
            SocialProfile,
        )

        config = EnrichmentConfig()
        scorer = EnrichmentScorer(config=config)

        # Perfect lead
        result = EnrichmentResult(
            lead_id=uuid4(),
            company_enrichment=CompanyEnrichment(
                domain="test.com",
                industry="Health & Wellness",
                headcount="11-50",
            ),
            website_analysis=WebsiteAnalysis(
                domain="test.com",
                accessible=True,
                description="Health food store",
                supplement_section=True,
            ),
            business_insights=BusinessInsights(
                focus_areas=["organic", "wellness"],
                product_categories=["supplements"],
            ),
            social_profiles=[
                SocialProfile(platform="instagram", followers=5000, active=True),
            ],
        )

        score = scorer.calculate_lead_score(
            result,
            country="Norway",
            industry="Health & Wellness",
        )

        assert score <= 100


class TestMinConfidenceThreshold:
    """Tests for minimum confidence threshold."""

    def test_threshold_constant_is_5(self) -> None:
        """Test MIN_CONFIDENCE_THRESHOLD is 5."""
        from teams.dawo.leads.enrichment.config import MIN_CONFIDENCE_THRESHOLD

        assert MIN_CONFIDENCE_THRESHOLD == 5
