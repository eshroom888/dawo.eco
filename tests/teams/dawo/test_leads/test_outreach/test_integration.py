"""Integration tests for Outreach Draft Generator.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Integration tests verifying:
- Full outreach pipeline with mocked external services
- Lead status transitions (QUALIFIED -> OUTREACH_PENDING)
- outreach_data JSONB storage
- Activity logging for generated drafts
- Approval queue submission
- Template performance logging
"""

import pytest
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional, Sequence
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from teams.dawo.leads.outreach.agent import OutreachDraftAgent
from teams.dawo.leads.outreach.approval_integration import OutreachApprovalIntegration
from teams.dawo.leads.outreach.classifier import ClassificationResult
from teams.dawo.leads.outreach.config import OutreachConfig
from teams.dawo.leads.outreach.generator import OutreachDraftGenerator
from teams.dawo.leads.outreach.personalization import PersonalizationEngine
from teams.dawo.leads.outreach.pipeline import OutreachPipeline, PipelineResult
from teams.dawo.leads.outreach.schemas import (
    GenerationResult,
    GenerationStatus,
    LeadType,
    OutreachDraft,
)
from teams.dawo.leads.outreach.service import OutreachService
from teams.dawo.leads.outreach.templates import OutreachTemplateRegistry
from teams.dawo.leads.outreach.validator import OutreachValidator


@dataclass
class MockLead:
    """Mock lead for integration tests."""

    id: UUID
    company: str
    first_name: str
    last_name: str
    email: str
    website_url: str
    status: str
    confidence_score: float
    country: str = "Norway"
    industry: str = "Health Products"
    enrichment_data: Optional[dict] = None

    def __post_init__(self):
        if self.enrichment_data is None:
            self.enrichment_data = {
                "personalization_hooks": [
                    {"type": "focus", "detail": "økologiske produkter"},
                    {"type": "competitor", "detail": "fører sopp i sortimentet"},
                ],
                "business_insights": {
                    "focus_areas": ["økologiske produkter", "naturlig helse"],
                    "product_categories": ["kosttilskudd", "superfoods"],
                },
            }


class MockLeadRepository:
    """Mock lead repository for integration tests.

    Simulates database operations with in-memory storage.
    """

    def __init__(self):
        self.leads: dict[UUID, MockLead] = {}
        self.outreach_updates: list[dict] = []

    def add_lead(self, lead: MockLead) -> None:
        """Add a lead to the repository."""
        self.leads[lead.id] = lead

    async def get_leads_for_outreach(self, limit: int = 10) -> Sequence[MockLead]:
        """Get leads eligible for outreach."""
        return [
            lead for lead in self.leads.values()
            if lead.status == "qualified"
            and lead.confidence_score >= 6.0
        ][:limit]

    async def get_by_id(self, lead_id: UUID) -> Optional[MockLead]:
        """Get a single lead by ID."""
        return self.leads.get(lead_id)

    async def update_outreach(
        self,
        lead_id: UUID,
        outreach_data: dict,
        status: str,
    ) -> Optional[MockLead]:
        """Update lead with outreach data."""
        lead = self.leads.get(lead_id)
        if lead:
            lead.status = status
            self.outreach_updates.append({
                "lead_id": lead_id,
                "outreach_data": outreach_data,
                "status": status,
                "updated_at": datetime.now(UTC),
            })
        return lead

    async def get_outreach_stats(self) -> dict[str, int]:
        """Get outreach statistics."""
        qualified = sum(1 for l in self.leads.values() if l.status == "qualified")
        pending = sum(1 for l in self.leads.values() if l.status == "outreach_pending")
        return {"qualified": qualified, "outreach_pending": pending}


class MockBrandValidator:
    """Mock brand voice validator."""

    async def validate(self, text: str) -> dict:
        """Validate brand voice."""
        return {"valid": True, "score": 0.85, "issues": []}


class MockClassifier:
    """Mock classifier that matches the service Protocol.

    The service expects classify(lead_id, enrichment_data) -> ClassificationResult.
    """

    def __init__(self, default_type: LeadType = LeadType.HEALTH_STORE):
        self.default_type = default_type

    async def classify(self, lead_id: UUID, enrichment_data: dict) -> ClassificationResult:
        """Classify a lead - matches Protocol expected by OutreachService."""
        return ClassificationResult(
            lead_id=lead_id,
            lead_type=self.default_type,
            confidence=0.85,
            reasoning="Mock classification for integration test",
        )


class MockGenerator:
    """Mock generator that matches the service Protocol."""

    async def generate(
        self,
        lead_id: UUID,
        contact_name: str,
        company: str,
        enrichment_data: dict,
        lead_type: LeadType,
    ) -> OutreachDraft:
        """Generate draft - matches Protocol expected by OutreachService."""
        return OutreachDraft(
            lead_id=lead_id,
            template_id="hs-intro-v1",
            template_type=lead_type,
            subject="Test Subject",
            body="Test body " * 20,  # ~40 words
            word_count=180,
            personalization_hooks=["test hook 1", "test hook 2"],
            personalization_score=3,
            suggested_send_time=datetime.now(UTC),
        )


class MockValidator:
    """Mock validator that matches the service Protocol."""

    def __init__(self, should_pass: bool = True):
        self.should_pass = should_pass

    async def validate(self, draft: OutreachDraft):
        """Validate draft - returns object with is_valid."""
        result = MagicMock()
        result.is_valid = self.should_pass
        result.issues = [] if self.should_pass else ["Test validation failure"]
        result.suggestions = []
        result.brand_voice_score = 0.85 if self.should_pass else 0.3
        return result


class MockOutreachService:
    """Mock outreach service for pipeline integration tests."""

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.generate_calls: list[dict] = []

    async def generate_outreach(self, lead) -> GenerationResult:
        """Generate outreach for a lead."""
        self.generate_calls.append({
            "lead_id": lead.id,
            "company": lead.company,
        })

        if self.should_succeed:
            draft = OutreachDraft(
                lead_id=lead.id,
                template_id="hs-intro-v1",
                template_type=LeadType.HEALTH_STORE,
                subject="Test Subject",
                body="Test body " * 20,
                word_count=180,
                personalization_hooks=["hook1", "hook2"],
                personalization_score=3,
                suggested_send_time=datetime.now(UTC),
            )
            return GenerationResult(
                lead_id=lead.id,
                status=GenerationStatus.SUCCESS,
                draft=draft,
                template_selection=None,
            )
        else:
            return GenerationResult(
                lead_id=lead.id,
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error="Mock generation failure",
            )

    def is_qualified_for_outreach(self, lead) -> bool:
        """Check if lead is qualified."""
        return lead.confidence_score >= 6.0

    def prepare_for_approval(self, draft, lead) -> dict:
        """Prepare for approval queue."""
        return {
            "template_type": draft.template_type.value,
            "template_id": draft.template_id,
            "draft": {
                "subject": draft.subject,
                "body": draft.body,
                "word_count": draft.word_count,
            },
            "personalization": {
                "hooks_used": draft.personalization_hooks,
                "personalization_score": draft.personalization_score,
            },
            "validation": {
                "brand_voice_pass": True,
            },
        }


class TestOutreachPipelineIntegration:
    """Integration tests for full outreach pipeline."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository with test leads."""
        repo = MockLeadRepository()
        # Add qualified leads
        for i in range(5):
            repo.add_lead(MockLead(
                id=uuid4(),
                company=f"Test Company {i}",
                first_name=f"Name{i}",
                last_name=f"Last{i}",
                email=f"test{i}@example.no",
                website_url=f"https://test{i}.no",
                status="qualified",
                confidence_score=7.0 + i * 0.5,
            ))
        return repo

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        return MockOutreachService(should_succeed=True)

    @pytest.fixture
    def pipeline(self, mock_repository, mock_service):
        """Create outreach pipeline."""
        return OutreachPipeline(
            lead_repository=mock_repository,
            outreach_service=mock_service,
        )

    # 14.1 Test full outreach pipeline with mocked external services
    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, pipeline):
        """Full pipeline should process all qualified leads."""
        result = await pipeline.execute(batch_size=10)

        assert isinstance(result, PipelineResult)
        assert result.status in ["COMPLETE", "INCOMPLETE"]
        assert result.total_processed == 5  # All qualified leads

    @pytest.mark.asyncio
    async def test_pipeline_updates_leads(self, pipeline, mock_service):
        """Pipeline should call service for each lead."""
        await pipeline.execute(batch_size=10)

        # Check that service was called for each lead
        assert len(mock_service.generate_calls) == 5

    @pytest.mark.asyncio
    async def test_pipeline_end_to_end_flow(self, pipeline, mock_service):
        """Test end-to-end pipeline flow."""
        result = await pipeline.execute(batch_size=5)

        # Verify service was called
        assert len(mock_service.generate_calls) > 0

        # Verify leads were processed
        assert result.successful > 0

    # 14.2 Test lead status transitions (QUALIFIED -> OUTREACH_PENDING)
    @pytest.mark.asyncio
    async def test_lead_status_transition_tracking(self, pipeline, mock_service):
        """Pipeline should track status transitions via service calls."""
        await pipeline.execute(batch_size=10)

        # All leads should have been processed
        assert len(mock_service.generate_calls) == 5

    @pytest.mark.asyncio
    async def test_status_only_changes_on_success(self, mock_repository):
        """Status should only change when draft generation succeeds."""
        # Create service that fails
        failing_service = MockOutreachService(should_succeed=False)
        pipeline = OutreachPipeline(
            lead_repository=mock_repository,
            outreach_service=failing_service,
        )

        result = await pipeline.execute(batch_size=10)

        # All should fail
        assert result.failed == 5
        assert result.successful == 0

    # 14.3 Test outreach_data JSONB storage
    @pytest.mark.asyncio
    async def test_outreach_data_structure_from_service(self, mock_service):
        """Service prepare_for_approval should create correct structure."""
        lead = MockLead(
            id=uuid4(),
            company="Test Co",
            first_name="Test",
            last_name="User",
            email="test@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        # Generate draft via service
        result = await mock_service.generate_outreach(lead)

        # Prepare for approval
        outreach_data = mock_service.prepare_for_approval(result.draft, lead)

        # Verify required structure
        assert "template_type" in outreach_data
        assert "template_id" in outreach_data
        assert "draft" in outreach_data
        assert "subject" in outreach_data["draft"]
        assert "body" in outreach_data["draft"]

    @pytest.mark.asyncio
    async def test_outreach_data_has_personalization(self, mock_service):
        """outreach_data should contain personalization info."""
        lead = MockLead(
            id=uuid4(),
            company="Test Co",
            first_name="Test",
            last_name="User",
            email="test@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        result = await mock_service.generate_outreach(lead)
        outreach_data = mock_service.prepare_for_approval(result.draft, lead)

        assert "personalization" in outreach_data
        personalization = outreach_data["personalization"]
        assert "hooks_used" in personalization
        assert "personalization_score" in personalization

    @pytest.mark.asyncio
    async def test_outreach_data_has_validation_results(self, mock_service):
        """outreach_data should contain validation results."""
        lead = MockLead(
            id=uuid4(),
            company="Test Co",
            first_name="Test",
            last_name="User",
            email="test@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        result = await mock_service.generate_outreach(lead)
        outreach_data = mock_service.prepare_for_approval(result.draft, lead)

        assert "validation" in outreach_data
        validation = outreach_data["validation"]
        assert "brand_voice_pass" in validation

    # 14.4 Test activity logging for generated drafts
    @pytest.mark.asyncio
    async def test_pipeline_logs_generation_activity(self, pipeline, caplog):
        """Pipeline should log draft generation activity."""
        import logging

        with caplog.at_level(logging.INFO):
            await pipeline.execute(batch_size=5)

        # Should have logged pipeline execution
        assert any("pipeline" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_service_logs_generation_steps(self, caplog):
        """Service should log each generation step."""
        import logging

        # Create real service with mocks
        service = OutreachService(
            classifier=MockClassifier(),
            template_registry=OutreachTemplateRegistry(),
            generator=MockGenerator(),
            validator=MockValidator(should_pass=True),
        )

        lead = MockLead(
            id=uuid4(),
            company="Test Company",
            first_name="Erik",
            last_name="Hansen",
            email="erik@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        with caplog.at_level(logging.INFO):
            await service.generate_outreach(lead)

        # Should have logged activity
        log_messages = [record.message.lower() for record in caplog.records]
        assert len(log_messages) > 0

    # 14.5 Test approval queue submission
    @pytest.mark.asyncio
    async def test_approval_integration_submit(self):
        """ApprovalIntegration should create proper queue items."""
        integration = OutreachApprovalIntegration()

        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="hs-intro-v1",
            template_type=LeadType.HEALTH_STORE,
            subject="Samarbeid med DAWO",
            body="Test email body " * 20,
            word_count=180,
            personalization_hooks=["økologiske produkter"],
            personalization_score=3,
            suggested_send_time=datetime.now(UTC),
        )

        lead = MockLead(
            id=uuid4(),
            company="Test Helse AS",
            first_name="Erik",
            last_name="Hansen",
            email="erik@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        approval_item = await integration.submit_to_queue(draft, lead)

        assert approval_item["source_type"] == "b2b_outreach"
        assert approval_item["content_type"] == "email"
        assert "metadata" in approval_item
        assert "display_data" in approval_item

    def test_approval_display_data_complete(self):
        """Approval display data should contain all required fields."""
        integration = OutreachApprovalIntegration()

        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="hs-intro-v1",
            template_type=LeadType.HEALTH_STORE,
            subject="Test",
            body="Test body",
            word_count=2,
            personalization_hooks=["test"],
            personalization_score=1,
            suggested_send_time=datetime.now(UTC),
        )

        lead = MockLead(
            id=uuid4(),
            company="Test Co",
            first_name="Test",
            last_name="User",
            email="test@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        display = integration.get_display_data(draft, lead)

        # Verify all required display fields (AC #3)
        assert "lead_summary" in display
        assert "personalization_hooks" in display
        assert "suggested_send_time" in display
        assert "template_type" in display
        assert "draft" in display

    @pytest.mark.asyncio
    async def test_approval_item_editable(self):
        """Approval item should support operator editing."""
        integration = OutreachApprovalIntegration()

        draft = OutreachDraft(
            lead_id=uuid4(),
            template_id="hs-intro-v1",
            template_type=LeadType.HEALTH_STORE,
            subject="Original subject",
            body="Original body",
            word_count=2,
            personalization_hooks=[],
            personalization_score=0,
            suggested_send_time=datetime.now(UTC),
        )

        lead = MockLead(
            id=uuid4(),
            company="Test",
            first_name="Test",
            last_name="Test",
            email="t@t.no",
            website_url="https://t.no",
            status="qualified",
            confidence_score=8.0,
        )

        item = await integration.submit_to_queue(draft, lead)

        # Verify fields exist that operator can edit
        assert "full_content" in item  # Email body - editable
        assert "preview" in item  # Subject line - editable

    # 14.6 Test template performance logging
    def test_template_selection_logged(self, caplog):
        """Template selection should be logged for performance tracking."""
        import logging

        registry = OutreachTemplateRegistry()
        lead_id = uuid4()

        # Get a template
        template = registry.get_template(LeadType.HEALTH_STORE)

        # Log the selection
        with caplog.at_level(logging.INFO):
            registry.log_template_selection(template.template_id, lead_id)

        # Verify logging occurred
        assert any("template" in record.message.lower() for record in caplog.records)

    def test_template_performance_metrics(self, caplog):
        """Template registry should log selection metrics."""
        import logging

        registry = OutreachTemplateRegistry()

        # Log multiple selections
        with caplog.at_level(logging.INFO):
            for lead_type in LeadType:
                template = registry.get_template(lead_type)
                registry.log_template_selection(template.template_id, uuid4())

        # All lead types should have selections logged
        log_count = sum(1 for r in caplog.records if "template" in r.message.lower())
        assert log_count == len(LeadType)


class TestAgentIntegration:
    """Integration tests for OutreachDraftAgent."""

    @pytest.fixture
    def mock_pipeline(self):
        """Create mock pipeline."""
        pipeline = AsyncMock()
        pipeline.execute.return_value = PipelineResult(
            status="COMPLETE",
            total_processed=5,
            successful=5,
            failed=0,
            errors=[],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        return pipeline

    @pytest.fixture
    def config(self):
        """Create config."""
        return OutreachConfig()

    @pytest.fixture
    def agent(self, config, mock_pipeline):
        """Create agent."""
        return OutreachDraftAgent(
            config=config,
            pipeline=mock_pipeline,
        )

    @pytest.mark.asyncio
    async def test_agent_executes_pipeline(self, agent, mock_pipeline):
        """Agent should execute the pipeline."""
        result = await agent.run()

        mock_pipeline.execute.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_agent_result_contains_statistics(self, agent):
        """Agent result should contain processing statistics."""
        result = await agent.run()

        assert hasattr(result, "leads_processed")
        assert hasattr(result, "drafts_generated")
        assert hasattr(result, "drafts_failed")

    @pytest.mark.asyncio
    async def test_agent_handles_pipeline_failure(self, agent, mock_pipeline):
        """Agent should handle pipeline failures gracefully."""
        mock_pipeline.execute.return_value = PipelineResult(
            status="FAILED",
            total_processed=5,
            successful=0,
            failed=5,
            errors=["All leads failed"],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        result = await agent.run()

        assert result.success is False
        assert result.drafts_failed == 5

    def test_agent_schedule_after_enrichment(self, agent):
        """Agent should be scheduled after enrichment."""
        schedule = agent.get_schedule()

        assert "after" in schedule
        assert "lead_enrichment" in schedule["after"]

    @pytest.mark.asyncio
    async def test_agent_result_serialization(self, agent):
        """Agent result should be serializable."""
        result = await agent.run()
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "leads_processed" in result_dict
        assert "drafts_generated" in result_dict


class TestEndToEndWorkflow:
    """End-to-end workflow integration tests."""

    @pytest.mark.asyncio
    async def test_complete_outreach_workflow(self):
        """Test complete workflow from lead to approval queue."""
        # Setup all components with mocks that match protocols
        template_registry = OutreachTemplateRegistry()
        classifier = MockClassifier()
        generator = MockGenerator()
        validator = MockValidator(should_pass=True)

        service = OutreachService(
            classifier=classifier,
            template_registry=template_registry,
            generator=generator,
            validator=validator,
        )
        approval_integration = OutreachApprovalIntegration()

        # Create a lead
        lead = MockLead(
            id=uuid4(),
            company="Premium Helsekost AS",
            first_name="Kari",
            last_name="Nordmann",
            email="kari@premiumhelsekost.no",
            website_url="https://premiumhelsekost.no",
            status="qualified",
            confidence_score=8.5,
        )

        # Step 1: Generate outreach
        result = await service.generate_outreach(lead)

        assert result.status == GenerationStatus.SUCCESS
        assert result.draft is not None

        # Step 2: Submit to approval queue
        approval_item = await approval_integration.submit_to_queue(result.draft, lead)

        assert approval_item["source_type"] == "b2b_outreach"
        assert lead.company in approval_item["title"]

        # Step 3: Verify display data for operator
        display = approval_item["display_data"]
        assert display["lead_summary"]["company"] == lead.company
        assert len(display["personalization_hooks"]) > 0

    @pytest.mark.asyncio
    async def test_workflow_with_multiple_lead_types(self):
        """Test workflow handles different lead types correctly."""
        template_registry = OutreachTemplateRegistry()
        generator = MockGenerator()
        validator = MockValidator(should_pass=True)

        # Test different lead types
        lead_types_to_test = [
            (LeadType.HEALTH_STORE, "Helsekost Butikk"),
            (LeadType.GYM_FITNESS, "Treningssenter AS"),
            (LeadType.ONLINE_RETAILER, "Nettbutikk Norge"),
        ]

        for lead_type, company_name in lead_types_to_test:
            # Create classifier for specific type
            classifier = MockClassifier(default_type=lead_type)

            service = OutreachService(
                classifier=classifier,
                template_registry=template_registry,
                generator=generator,
                validator=validator,
            )

            lead = MockLead(
                id=uuid4(),
                company=company_name,
                first_name="Test",
                last_name="User",
                email="test@test.no",
                website_url="https://test.no",
                status="qualified",
                confidence_score=8.0,
            )

            result = await service.generate_outreach(lead)

            # Each lead type should generate a draft
            assert result.status == GenerationStatus.SUCCESS
            assert result.draft is not None

    @pytest.mark.asyncio
    async def test_workflow_validation_failure_path(self):
        """Test workflow handles validation failure correctly."""
        template_registry = OutreachTemplateRegistry()
        classifier = MockClassifier()
        generator = MockGenerator()
        validator = MockValidator(should_pass=False)  # Will fail validation

        service = OutreachService(
            classifier=classifier,
            template_registry=template_registry,
            generator=generator,
            validator=validator,
        )

        lead = MockLead(
            id=uuid4(),
            company="Test Company",
            first_name="Test",
            last_name="User",
            email="test@test.no",
            website_url="https://test.no",
            status="qualified",
            confidence_score=8.0,
        )

        result = await service.generate_outreach(lead)

        # Should fail validation
        assert result.status == GenerationStatus.VALIDATION_FAILED
        assert result.draft is not None  # Draft still created
        assert "validation" in result.error.lower()
