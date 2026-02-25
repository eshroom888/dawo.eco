"""Tests for enrichment schemas.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 1.3: Test dataclasses
"""

import pytest
from datetime import datetime, UTC


class TestPersonalizationHookType:
    """Tests for PersonalizationHookType enum."""

    def test_competitor_type_value(self) -> None:
        """Test COMPETITOR has correct value."""
        from teams.dawo.leads.enrichment.schemas import PersonalizationHookType

        assert PersonalizationHookType.COMPETITOR.value == "competitor"

    def test_focus_type_value(self) -> None:
        """Test FOCUS has correct value."""
        from teams.dawo.leads.enrichment.schemas import PersonalizationHookType

        assert PersonalizationHookType.FOCUS.value == "focus"

    def test_all_types_are_strings(self) -> None:
        """Test all hook types are string enums."""
        from teams.dawo.leads.enrichment.schemas import PersonalizationHookType

        for hook_type in PersonalizationHookType:
            assert isinstance(hook_type.value, str)

    def test_expected_types_exist(self) -> None:
        """Test all expected hook types exist."""
        from teams.dawo.leads.enrichment.schemas import PersonalizationHookType

        expected = ["COMPETITOR", "FOCUS", "AUDIENCE", "LOCATION", "PRODUCT", "VALUES", "GROWTH"]
        for name in expected:
            assert hasattr(PersonalizationHookType, name)


class TestPersonalizationHook:
    """Tests for PersonalizationHook dataclass."""

    def test_create_hook_with_required_fields(self) -> None:
        """Test creating a hook with required fields only."""
        from teams.dawo.leads.enrichment.schemas import (
            PersonalizationHook,
            PersonalizationHookType,
        )

        hook = PersonalizationHook(
            hook_type=PersonalizationHookType.COMPETITOR,
            detail="Carries HealthWorks mushroom products",
        )

        assert hook.hook_type == PersonalizationHookType.COMPETITOR
        assert hook.detail == "Carries HealthWorks mushroom products"

    def test_hook_to_dict(self) -> None:
        """Test converting hook to dictionary."""
        from teams.dawo.leads.enrichment.schemas import (
            PersonalizationHook,
            PersonalizationHookType,
        )

        hook = PersonalizationHook(
            hook_type=PersonalizationHookType.FOCUS,
            detail="Strong organic focus",
        )

        result = hook.to_dict()

        assert result["type"] == "focus"
        assert result["detail"] == "Strong organic focus"


class TestWebsiteAnalysis:
    """Tests for WebsiteAnalysis dataclass."""

    def test_create_analysis_with_defaults(self) -> None:
        """Test creating analysis with default values."""
        from teams.dawo.leads.enrichment.schemas import WebsiteAnalysis

        analysis = WebsiteAnalysis(domain="example.com")

        assert analysis.domain == "example.com"
        assert analysis.accessible is False
        assert analysis.description is None
        assert analysis.content is None
        assert analysis.mushroom_keywords_found == []
        assert analysis.supplement_section is False

    def test_create_analysis_with_all_fields(self) -> None:
        """Test creating analysis with all fields."""
        from teams.dawo.leads.enrichment.schemas import WebsiteAnalysis

        analysis = WebsiteAnalysis(
            domain="healthstore.no",
            accessible=True,
            description="Premium health food store in Oslo",
            content="We sell lion's mane and reishi mushrooms...",
            mushroom_keywords_found=["lion's mane", "reishi"],
            supplement_section=True,
        )

        assert analysis.accessible is True
        assert "lion's mane" in analysis.mushroom_keywords_found
        assert analysis.supplement_section is True

    def test_analysis_to_dict(self) -> None:
        """Test converting analysis to dictionary."""
        from teams.dawo.leads.enrichment.schemas import WebsiteAnalysis

        analysis = WebsiteAnalysis(
            domain="test.com",
            accessible=True,
            mushroom_keywords_found=["chaga"],
        )

        result = analysis.to_dict()

        assert result["accessible"] is True
        assert result["mushroom_keywords_found"] == ["chaga"]


class TestBusinessInsights:
    """Tests for BusinessInsights dataclass."""

    def test_create_insights_with_defaults(self) -> None:
        """Test creating insights with default values."""
        from teams.dawo.leads.enrichment.schemas import BusinessInsights

        insights = BusinessInsights()

        assert insights.focus_areas == []
        assert insights.target_demographics is None
        assert insights.product_categories == []
        assert insights.wellness_positioning is None

    def test_create_insights_with_data(self) -> None:
        """Test creating insights with data."""
        from teams.dawo.leads.enrichment.schemas import BusinessInsights

        insights = BusinessInsights(
            focus_areas=["organic products", "health foods"],
            target_demographics="health-conscious consumers, 25-55",
            product_categories=["supplements", "organic groceries"],
            wellness_positioning="strong",
        )

        assert len(insights.focus_areas) == 2
        assert "organic products" in insights.focus_areas
        assert insights.wellness_positioning == "strong"


class TestSocialProfile:
    """Tests for SocialProfile dataclass."""

    def test_create_instagram_profile(self) -> None:
        """Test creating Instagram social profile."""
        from teams.dawo.leads.enrichment.schemas import SocialProfile

        profile = SocialProfile(
            platform="instagram",
            handle="@example_store",
            followers=2500,
            active=True,
        )

        assert profile.platform == "instagram"
        assert profile.handle == "@example_store"
        assert profile.followers == 2500
        assert profile.active is True

    def test_create_linkedin_profile(self) -> None:
        """Test creating LinkedIn social profile."""
        from teams.dawo.leads.enrichment.schemas import SocialProfile

        profile = SocialProfile(
            platform="linkedin",
            url="linkedin.com/company/example",
            employees="11-50",
        )

        assert profile.platform == "linkedin"
        assert profile.url == "linkedin.com/company/example"
        assert profile.employees == "11-50"


class TestCompanyEnrichment:
    """Tests for CompanyEnrichment dataclass."""

    def test_create_enrichment_with_required_fields(self) -> None:
        """Test creating enrichment with required domain."""
        from teams.dawo.leads.enrichment.schemas import CompanyEnrichment

        enrichment = CompanyEnrichment(domain="example.com")

        assert enrichment.domain == "example.com"
        assert enrichment.organization is None
        assert enrichment.headcount is None
        assert enrichment.industry is None

    def test_create_enrichment_with_full_data(self) -> None:
        """Test creating enrichment with all data."""
        from teams.dawo.leads.enrichment.schemas import CompanyEnrichment

        enrichment = CompanyEnrichment(
            domain="healthstore.no",
            organization="Health Store AS",
            headcount="11-50",
            industry="Retail - Health & Wellness",
            email_patterns=["first.last@healthstore.no"],
        )

        assert enrichment.organization == "Health Store AS"
        assert enrichment.headcount == "11-50"
        assert len(enrichment.email_patterns) == 1


class TestEnrichmentResult:
    """Tests for EnrichmentResult dataclass."""

    def test_create_result_with_lead_id(self) -> None:
        """Test creating result with lead ID."""
        from uuid import uuid4
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult

        lead_id = uuid4()
        result = EnrichmentResult(lead_id=lead_id)

        assert result.lead_id == lead_id
        assert result.confidence_score == 0.0
        assert result.lead_score == 0.0
        assert result.errors == []
        assert result.personalization_hooks == []

    def test_result_has_timestamp(self) -> None:
        """Test result has enriched_at timestamp."""
        from uuid import uuid4
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult

        result = EnrichmentResult(lead_id=uuid4())

        assert result.enriched_at is not None
        assert isinstance(result.enriched_at, datetime)

    def test_result_to_dict(self) -> None:
        """Test converting result to dictionary."""
        from uuid import uuid4
        from teams.dawo.leads.enrichment.schemas import (
            EnrichmentResult,
            BusinessInsights,
            PersonalizationHook,
            PersonalizationHookType,
        )

        lead_id = uuid4()
        result = EnrichmentResult(
            lead_id=lead_id,
            confidence_score=7.5,
            lead_score=65.0,
            business_insights=BusinessInsights(
                focus_areas=["organic"],
                wellness_positioning="strong",
            ),
            personalization_hooks=[
                PersonalizationHook(
                    hook_type=PersonalizationHookType.FOCUS,
                    detail="Strong organic focus",
                )
            ],
        )

        data = result.to_dict()

        assert data["confidence_score"] == 7.5
        assert data["lead_score"] == 65.0
        assert "business_insights" in data
        assert len(data["personalization_hooks"]) == 1


class TestScoreBreakdown:
    """Tests for ScoreBreakdown dataclass."""

    def test_create_breakdown_with_defaults(self) -> None:
        """Test creating breakdown with default zero values."""
        from teams.dawo.leads.enrichment.schemas import ScoreBreakdown

        breakdown = ScoreBreakdown()

        assert breakdown.verified_email == 0.0
        assert breakdown.business_description == 0.0
        assert breakdown.social_presence == 0.0
        assert breakdown.decision_maker == 0.0
        assert breakdown.industry_match == 0.0
        assert breakdown.product_categories == 0.0
        assert breakdown.personalization_hooks == 0.0
        assert breakdown.website_accessible == 0.0

    def test_total_calculates_correctly(self) -> None:
        """Test total property calculates sum."""
        from teams.dawo.leads.enrichment.schemas import ScoreBreakdown

        breakdown = ScoreBreakdown(
            verified_email=2.0,
            business_description=2.0,
            social_presence=1.0,
            decision_maker=1.0,
        )

        assert breakdown.total == 6.0

    def test_breakdown_to_dict(self) -> None:
        """Test converting breakdown to dictionary."""
        from teams.dawo.leads.enrichment.schemas import ScoreBreakdown

        breakdown = ScoreBreakdown(verified_email=2.0, website_accessible=1.0)
        result = breakdown.to_dict()

        assert result["verified_email"] == 2.0
        assert result["website_accessible"] == 1.0
