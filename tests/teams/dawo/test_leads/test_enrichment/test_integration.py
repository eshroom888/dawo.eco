"""Integration tests for Lead Enrichment Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 13: Create integration tests

Tests full enrichment flow with mocked external services.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import datetime, UTC

from teams.dawo.leads.enrichment.config import EnrichmentConfig
from teams.dawo.leads.enrichment.schemas import (
    EnrichmentResult,
    WebsiteAnalysis,
    BusinessInsights,
    CompanyEnrichment,
    SocialProfile,
    PersonalizationHook,
    PersonalizationHookType,
    ScoreBreakdown,
)
from teams.dawo.leads.enrichment.service import LeadEnrichmentService
from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline, PipelineStatus
from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
from core.leads.models import LeadStatus, ActivityType


class TestFullEnrichmentPipeline:
    """Integration tests for full enrichment pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_enriches_new_leads(self) -> None:
        """Test complete pipeline enriches NEW leads to QUALIFIED."""
        config = EnrichmentConfig()

        # Create mock lead
        lead = Mock()
        lead.id = uuid4()
        lead.status = LeadStatus.NEW.value
        lead.website_url = "https://healthstore.no"
        lead.company = "Health Store AS"
        lead.linkedin_url = "https://linkedin.com/company/healthstore"
        lead.instagram_handle = "@healthstore_no"
        lead.industry = "Health Food"
        lead.country = "Norway"
        lead.company_size = "11-50"

        # Mock repository
        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = [lead]
        repository.update_enrichment.return_value = lead
        repository.add_activity.return_value = Mock()

        # Mock all analyzers with realistic data
        website_analyzer = AsyncMock()
        website_analyzer.analyze.return_value = WebsiteAnalysis(
            domain="healthstore.no",
            accessible=True,
            content="Vi tilbyr et bredt utvalg av kosttilskudd og funksjonelle sopp produkter...",
            description="Premium health food store in Oslo",
            mushroom_keywords_found=["lion's mane", "functional mushrooms"],
            supplement_section=True,
        )

        business_analyzer = AsyncMock()
        business_analyzer.analyze_business.return_value = BusinessInsights(
            focus_areas=["organic products", "health foods", "local producers"],
            target_demographics="health-conscious consumers, 25-55",
            product_categories=["supplements", "organic groceries", "wellness"],
            wellness_positioning="strong",
        )
        business_analyzer.identify_hooks.return_value = [
            PersonalizationHook(
                hook_type=PersonalizationHookType.FOCUS,
                detail="Strong organic and local producer focus",
            ),
            PersonalizationHook(
                hook_type=PersonalizationHookType.PRODUCT,
                detail="Already sells functional mushroom products",
            ),
        ]
        business_analyzer.detect_existing_customer.return_value = False

        hunter_enricher = AsyncMock()
        hunter_enricher.enrich_company.return_value = CompanyEnrichment(
            domain="healthstore.no",
            organization="Health Store AS",
            headcount=25,
            industry="Health & Wellness",
            email_patterns=["info@healthstore.no"],
        )
        hunter_enricher.find_decision_makers.return_value = []

        social_analyzer = AsyncMock()
        social_analyzer.analyze_instagram.return_value = SocialProfile(
            platform="instagram",
            handle="@healthstore_no",
            url="https://instagram.com/healthstore_no",
            followers=2500,
            active=True,
        )
        social_analyzer.analyze_linkedin.return_value = SocialProfile(
            platform="linkedin",
            url="https://linkedin.com/company/healthstore",
            employees=25,
        )

        scorer = Mock()
        scorer.calculate_confidence.return_value = (
            7.5,
            ScoreBreakdown(
                verified_email=2.0,
                business_description=2.0,
                social_presence=1.0,
                decision_maker=0.0,
                industry_match=1.0,
                product_categories=1.0,
                personalization_hooks=0.5,
            ),
        )
        scorer.calculate_lead_score.return_value = 75.0

        # Create service
        service = LeadEnrichmentService(
            config=config,
            website_analyzer=website_analyzer,
            business_analyzer=business_analyzer,
            hunter_enricher=hunter_enricher,
            social_analyzer=social_analyzer,
            scorer=scorer,
        )

        # Create pipeline
        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=service,
        )

        # Execute pipeline
        result = await pipeline.execute(batch_size=10)

        # Verify pipeline result
        assert result.total_processed == 1
        assert result.successful == 1
        assert result.failed == 0
        assert result.qualified == 1
        assert result.status == PipelineStatus.COMPLETE

        # Verify lead was updated
        repository.update_enrichment.assert_called_once()
        update_call = repository.update_enrichment.call_args[1]
        assert update_call["lead_id"] == lead.id
        assert update_call["status"] == LeadStatus.QUALIFIED

        # Verify activity was logged
        repository.add_activity.assert_called_once()
        activity_call = repository.add_activity.call_args[1]
        assert activity_call["activity_type"] == ActivityType.ENRICHED


class TestLeadStatusTransitions:
    """Tests for lead status transitions during enrichment."""

    @pytest.mark.asyncio
    async def test_high_confidence_leads_become_qualified(self) -> None:
        """Test leads with confidence >= 5 become QUALIFIED."""
        config = EnrichmentConfig()

        lead = Mock()
        lead.id = uuid4()
        lead.website_url = "https://test.com"

        # Create service with mocks that produce high confidence
        service = _create_mock_service(confidence_score=7.0)

        result = await service.enrich_lead(lead)
        status = service.determine_status(result, is_existing_customer=False)

        assert status == LeadStatus.QUALIFIED

    @pytest.mark.asyncio
    async def test_low_confidence_leads_become_researching(self) -> None:
        """Test leads with confidence < 5 become RESEARCHING."""
        config = EnrichmentConfig()

        lead = Mock()
        lead.id = uuid4()
        lead.website_url = "https://test.com"

        # Create service with mocks that produce low confidence
        service = _create_mock_service(confidence_score=3.0)

        result = await service.enrich_lead(lead)
        status = service.determine_status(result, is_existing_customer=False)

        assert status == LeadStatus.RESEARCHING

    @pytest.mark.asyncio
    async def test_existing_customers_become_converted(self) -> None:
        """Test existing DAWO customers become CONVERTED."""
        config = EnrichmentConfig()

        lead = Mock()
        lead.id = uuid4()
        lead.website_url = "https://test.com"

        service = _create_mock_service(
            confidence_score=8.0,
            is_existing_customer=True,
        )

        result = await service.enrich_lead(lead)
        status = service.determine_status(result, is_existing_customer=True)

        assert status == LeadStatus.CONVERTED


class TestEnrichmentDataStorage:
    """Tests for enrichment_data JSONB storage."""

    def test_enrichment_result_serializes_to_dict(self) -> None:
        """Test EnrichmentResult can be serialized for JSONB."""
        result = EnrichmentResult(
            lead_id=uuid4(),
            confidence_score=7.5,
            lead_score=75.0,
            website_analysis=WebsiteAnalysis(
                domain="test.com",
                accessible=True,
                content="Test content",
            ),
            business_insights=BusinessInsights(
                focus_areas=["organic", "health"],
            ),
            personalization_hooks=[
                PersonalizationHook(
                    hook_type=PersonalizationHookType.FOCUS,
                    detail="Test hook",
                ),
            ],
        )

        data = result.to_dict()

        # Verify structure - to_dict() returns data for JSONB storage
        assert "confidence_score" in data
        assert data["confidence_score"] == 7.5
        assert "website_analysis" in data
        assert "personalization_hooks" in data
        assert len(data["personalization_hooks"]) == 1

    def test_service_formats_data_for_storage(self) -> None:
        """Test service formats enrichment data correctly."""
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
            confidence_score=6.0,
            website_analysis=WebsiteAnalysis(domain="test.com", accessible=True),
        )

        formatted = service.format_enrichment_data(result)

        # Should be a dict suitable for JSONB
        assert isinstance(formatted, dict)
        assert "confidence_score" in formatted


class TestActivityLogging:
    """Tests for activity logging during enrichment."""

    @pytest.mark.asyncio
    async def test_pipeline_logs_enrichment_activity(self) -> None:
        """Test pipeline creates activity log entries."""
        config = EnrichmentConfig()

        lead = Mock()
        lead.id = uuid4()
        lead.status = LeadStatus.NEW.value

        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = [lead]
        repository.update_enrichment.return_value = lead

        service = Mock()
        service.enrich_lead = AsyncMock(
            return_value=EnrichmentResult(
                lead_id=lead.id,
                confidence_score=6.0,
            )
        )
        service.determine_status.return_value = LeadStatus.QUALIFIED
        service.format_enrichment_data.return_value = {}

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=service,
        )

        await pipeline.execute()

        # Verify activity was logged
        repository.add_activity.assert_called_once()
        call_kwargs = repository.add_activity.call_args[1]

        assert call_kwargs["lead_id"] == lead.id
        assert call_kwargs["activity_type"] == ActivityType.ENRICHED
        assert "confidence score" in call_kwargs["description"].lower()


class TestExistingCustomerDetection:
    """Tests for existing DAWO customer detection."""

    def test_detects_dawo_in_website_content(self) -> None:
        """Test detection of DAWO products in website content."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        llm_client = AsyncMock()
        analyzer = BusinessAnalyzer(config=config, llm_client=llm_client)

        # Content with DAWO mention
        content = "Vi er stolte av å tilby DAWO sine økologiske soppprodukter..."

        is_customer = analyzer.detect_existing_customer(content)

        assert is_customer is True

    def test_no_detection_without_dawo_mentions(self) -> None:
        """Test no detection when DAWO not mentioned."""
        from teams.dawo.leads.enrichment.business_analyzer import BusinessAnalyzer
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        llm_client = AsyncMock()
        analyzer = BusinessAnalyzer(config=config, llm_client=llm_client)

        content = "We sell various organic supplements and mushroom products."

        is_customer = analyzer.detect_existing_customer(content)

        assert is_customer is False


class TestAgentIntegration:
    """Integration tests for agent with pipeline."""

    @pytest.mark.asyncio
    async def test_agent_executes_pipeline_and_reports_stats(self) -> None:
        """Test agent runs pipeline and returns statistics."""
        config = EnrichmentConfig(batch_size=5)

        from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus

        pipeline_result = PipelineResult(
            total_processed=5,
            successful=4,
            failed=1,
            qualified=3,
            researching=1,
            converted=0,
            status=PipelineStatus.INCOMPLETE,
        )

        pipeline = AsyncMock()
        pipeline.execute.return_value = pipeline_result

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        result = await agent.run()

        # Verify agent result
        assert result.success is True
        assert result.status == "incomplete"
        assert result.leads_processed == 5
        assert result.leads_enriched == 4
        assert result.leads_failed == 1
        assert result.leads_qualified == 3

        # Verify pipeline was called with config batch size
        pipeline.execute.assert_called_once_with(batch_size=5)


# Helper function to create mock service
def _create_mock_service(
    confidence_score: float = 5.0,
    lead_score: float = 50.0,
    is_existing_customer: bool = False,
) -> LeadEnrichmentService:
    """Create a mock LeadEnrichmentService for testing."""
    config = EnrichmentConfig()

    website_analyzer = AsyncMock()
    website_analyzer.analyze.return_value = WebsiteAnalysis(
        domain="test.com",
        accessible=True,
        content="Test content",
    )

    business_analyzer = AsyncMock()
    business_analyzer.analyze_business.return_value = BusinessInsights(
        focus_areas=["test"],
    )
    business_analyzer.identify_hooks.return_value = []
    business_analyzer.detect_existing_customer.return_value = is_existing_customer

    hunter_enricher = AsyncMock()
    hunter_enricher.enrich_company.return_value = CompanyEnrichment(domain="test.com")
    hunter_enricher.find_decision_makers.return_value = []

    social_analyzer = AsyncMock()
    social_analyzer.analyze_instagram.return_value = None
    social_analyzer.analyze_linkedin.return_value = None

    scorer = Mock()
    scorer.calculate_confidence.return_value = (confidence_score, ScoreBreakdown())
    scorer.calculate_lead_score.return_value = lead_score

    return LeadEnrichmentService(
        config=config,
        website_analyzer=website_analyzer,
        business_analyzer=business_analyzer,
        hunter_enricher=hunter_enricher,
        social_analyzer=social_analyzer,
        scorer=scorer,
    )
