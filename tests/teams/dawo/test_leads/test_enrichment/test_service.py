"""Tests for LeadEnrichmentService.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 7: Implement Lead Enrichment Service
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4


class TestLeadEnrichmentServiceInit:
    """Tests for LeadEnrichmentService initialization."""

    def test_accepts_dependencies_via_injection(self) -> None:
        """Test service accepts all dependencies via DI."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        website_analyzer = AsyncMock()
        business_analyzer = AsyncMock()
        hunter_enricher = AsyncMock()
        social_analyzer = AsyncMock()
        scorer = Mock()

        service = LeadEnrichmentService(
            config=config,
            website_analyzer=website_analyzer,
            business_analyzer=business_analyzer,
            hunter_enricher=hunter_enricher,
            social_analyzer=social_analyzer,
            scorer=scorer,
        )

        assert service._config is config
        assert service._website_analyzer is website_analyzer


class TestEnrichLead:
    """Tests for enrich_lead method."""

    @pytest.mark.asyncio
    async def test_enrich_lead_orchestrates_all_analyzers(self) -> None:
        """Test enrichment orchestrates all analyzer calls."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import (
            WebsiteAnalysis,
            BusinessInsights,
            CompanyEnrichment,
            ScoreBreakdown,
        )

        config = EnrichmentConfig()

        # Mock analyzers
        website_analyzer = AsyncMock()
        website_analyzer.analyze.return_value = WebsiteAnalysis(
            domain="test.com",
            accessible=True,
            content="Test content",
        )

        business_analyzer = AsyncMock()
        business_analyzer.analyze_business.return_value = BusinessInsights(
            focus_areas=["organic"],
        )
        business_analyzer.identify_hooks.return_value = []
        business_analyzer.detect_existing_customer.return_value = False

        hunter_enricher = AsyncMock()
        hunter_enricher.enrich_company.return_value = CompanyEnrichment(
            domain="test.com",
        )
        hunter_enricher.find_decision_makers.return_value = []

        social_analyzer = AsyncMock()
        social_analyzer.analyze_instagram.return_value = None
        social_analyzer.analyze_linkedin.return_value = None

        scorer = Mock()
        scorer.calculate_confidence.return_value = (5.0, ScoreBreakdown())
        scorer.calculate_lead_score.return_value = 50.0

        service = LeadEnrichmentService(
            config=config,
            website_analyzer=website_analyzer,
            business_analyzer=business_analyzer,
            hunter_enricher=hunter_enricher,
            social_analyzer=social_analyzer,
            scorer=scorer,
        )

        # Create mock lead
        lead = Mock()
        lead.id = uuid4()
        lead.website_url = "https://test.com"
        lead.company = "Test Company"

        result = await service.enrich_lead(lead)

        # Verify analyzers were called
        website_analyzer.analyze.assert_called_once()
        hunter_enricher.enrich_company.assert_called_once()

        # Verify result
        assert result.lead_id == lead.id
        assert result.confidence_score == 5.0

    @pytest.mark.asyncio
    async def test_enrich_lead_handles_analyzer_failures(self) -> None:
        """Test graceful degradation on analyzer failures."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import ScoreBreakdown

        config = EnrichmentConfig()

        # Mock analyzers with failures
        website_analyzer = AsyncMock()
        website_analyzer.analyze.side_effect = Exception("Failed")

        business_analyzer = AsyncMock()
        hunter_enricher = AsyncMock()
        social_analyzer = AsyncMock()
        scorer = Mock()
        scorer.calculate_confidence.return_value = (2.0, ScoreBreakdown())
        scorer.calculate_lead_score.return_value = 20.0

        service = LeadEnrichmentService(
            config=config,
            website_analyzer=website_analyzer,
            business_analyzer=business_analyzer,
            hunter_enricher=hunter_enricher,
            social_analyzer=social_analyzer,
            scorer=scorer,
        )

        lead = Mock()
        lead.id = uuid4()
        lead.website_url = "https://test.com"

        result = await service.enrich_lead(lead)

        # Should still return result with errors logged
        assert result.lead_id == lead.id
        assert len(result.errors) > 0


class TestDetermineStatus:
    """Tests for determine_status method."""

    def test_qualified_when_confidence_above_threshold(self) -> None:
        """Test QUALIFIED status when confidence >= 5."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()
        service = LeadEnrichmentService(
            config=config,
            website_analyzer=AsyncMock(),
            business_analyzer=AsyncMock(),
            hunter_enricher=AsyncMock(),
            social_analyzer=AsyncMock(),
            scorer=Mock(),
        )

        result = EnrichmentResult(
            lead_id=uuid4(),
            confidence_score=7.0,
        )

        status = service.determine_status(result, is_existing_customer=False)

        assert status == LeadStatus.QUALIFIED

    def test_researching_when_confidence_below_threshold(self) -> None:
        """Test RESEARCHING status when confidence < 5."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()
        service = LeadEnrichmentService(
            config=config,
            website_analyzer=AsyncMock(),
            business_analyzer=AsyncMock(),
            hunter_enricher=AsyncMock(),
            social_analyzer=AsyncMock(),
            scorer=Mock(),
        )

        result = EnrichmentResult(
            lead_id=uuid4(),
            confidence_score=3.0,
        )

        status = service.determine_status(result, is_existing_customer=False)

        assert status == LeadStatus.RESEARCHING

    def test_converted_when_existing_customer(self) -> None:
        """Test CONVERTED status for existing customers."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()
        service = LeadEnrichmentService(
            config=config,
            website_analyzer=AsyncMock(),
            business_analyzer=AsyncMock(),
            hunter_enricher=AsyncMock(),
            social_analyzer=AsyncMock(),
            scorer=Mock(),
        )

        result = EnrichmentResult(
            lead_id=uuid4(),
            confidence_score=8.0,
        )

        status = service.determine_status(result, is_existing_customer=True)

        assert status == LeadStatus.CONVERTED


class TestGetMissingFields:
    """Tests for get_missing_fields method."""

    def test_identifies_missing_website_analysis(self) -> None:
        """Test identification of missing website analysis."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult

        config = EnrichmentConfig()
        service = LeadEnrichmentService(
            config=config,
            website_analyzer=AsyncMock(),
            business_analyzer=AsyncMock(),
            hunter_enricher=AsyncMock(),
            social_analyzer=AsyncMock(),
            scorer=Mock(),
        )

        result = EnrichmentResult(lead_id=uuid4())

        missing = service.get_missing_fields(result)

        assert "website_analysis" in missing

    def test_no_missing_fields_when_complete(self) -> None:
        """Test no missing fields when enrichment complete."""
        from teams.dawo.leads.enrichment.service import LeadEnrichmentService
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
        service = LeadEnrichmentService(
            config=config,
            website_analyzer=AsyncMock(),
            business_analyzer=AsyncMock(),
            hunter_enricher=AsyncMock(),
            social_analyzer=AsyncMock(),
            scorer=Mock(),
        )

        result = EnrichmentResult(
            lead_id=uuid4(),
            website_analysis=WebsiteAnalysis(domain="test.com", accessible=True),
            business_insights=BusinessInsights(focus_areas=["test"]),
            company_enrichment=CompanyEnrichment(domain="test.com"),
            social_profiles=[SocialProfile(platform="instagram")],
            personalization_hooks=[
                PersonalizationHook(
                    hook_type=PersonalizationHookType.FOCUS,
                    detail="test",
                )
            ],
        )

        missing = service.get_missing_fields(result)

        assert len(missing) == 0
