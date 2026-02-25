"""Tests for EnrichmentPipeline.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 8: Implement Enrichment Pipeline
"""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4


class TestEnrichmentPipelineInit:
    """Tests for EnrichmentPipeline initialization."""

    def test_accepts_dependencies_via_injection(self) -> None:
        """Test pipeline accepts all dependencies via DI."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        repository = AsyncMock()
        enrichment_service = AsyncMock()

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        assert pipeline._config is config
        assert pipeline._repository is repository
        assert pipeline._enrichment_service is enrichment_service


class TestExecutePipeline:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_execute_processes_new_leads(self) -> None:
        """Test pipeline queries and processes NEW leads."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()

        # Mock leads
        lead1 = Mock()
        lead1.id = uuid4()
        lead1.status = LeadStatus.NEW.value
        lead1.website_url = "https://test1.com"

        lead2 = Mock()
        lead2.id = uuid4()
        lead2.status = LeadStatus.NEW.value
        lead2.website_url = "https://test2.com"

        # Mock repository
        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = [lead1, lead2]
        repository.update_enrichment.return_value = lead1

        # Mock enrichment service
        enrichment_service = Mock()
        enrichment_service.enrich_lead = AsyncMock(
            return_value=EnrichmentResult(
                lead_id=lead1.id,
                confidence_score=7.0,
            )
        )
        enrichment_service.determine_status.return_value = LeadStatus.QUALIFIED
        enrichment_service.format_enrichment_data.return_value = {"test": "data"}

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        result = await pipeline.execute(batch_size=10)

        # Verify leads were queried
        repository.get_leads_for_enrichment.assert_called_once_with(limit=10)

        # Verify enrichment was called for both leads
        assert enrichment_service.enrich_lead.call_count == 2

        # Verify result contains statistics
        assert result.total_processed == 2
        assert result.successful >= 0

    @pytest.mark.asyncio
    async def test_execute_continues_on_individual_failure(self) -> None:
        """Test pipeline continues processing when one lead fails."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()

        # Mock leads
        lead1 = Mock()
        lead1.id = uuid4()
        lead1.status = LeadStatus.NEW.value

        lead2 = Mock()
        lead2.id = uuid4()
        lead2.status = LeadStatus.NEW.value

        # Mock repository
        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = [lead1, lead2]
        repository.update_enrichment.return_value = lead2

        # Mock enrichment service - first fails, second succeeds
        enrichment_service = Mock()
        enrichment_service.enrich_lead = AsyncMock(
            side_effect=[
                Exception("Enrichment failed"),
                EnrichmentResult(lead_id=lead2.id, confidence_score=6.0),
            ]
        )
        enrichment_service.determine_status.return_value = LeadStatus.QUALIFIED
        enrichment_service.format_enrichment_data.return_value = {}

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        result = await pipeline.execute(batch_size=10)

        # Verify both leads were attempted
        assert enrichment_service.enrich_lead.call_count == 2

        # Verify we have counts for both success and failure
        assert result.total_processed == 2
        assert result.failed == 1
        assert result.successful == 1

    @pytest.mark.asyncio
    async def test_execute_respects_batch_size(self) -> None:
        """Test pipeline respects batch_size parameter."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()

        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = []

        enrichment_service = Mock()

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        await pipeline.execute(batch_size=5)

        repository.get_leads_for_enrichment.assert_called_once_with(limit=5)

    @pytest.mark.asyncio
    async def test_execute_updates_lead_after_enrichment(self) -> None:
        """Test pipeline updates lead record after enrichment."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()

        lead = Mock()
        lead.id = uuid4()
        lead.status = LeadStatus.NEW.value

        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = [lead]
        repository.update_enrichment.return_value = lead

        enrichment_result = EnrichmentResult(
            lead_id=lead.id,
            confidence_score=7.5,
            lead_score=65.0,
        )

        enrichment_service = Mock()
        enrichment_service.enrich_lead = AsyncMock(return_value=enrichment_result)
        enrichment_service.determine_status.return_value = LeadStatus.QUALIFIED
        enrichment_service.format_enrichment_data.return_value = {"confidence": 7.5}

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        await pipeline.execute()

        # Verify update was called
        repository.update_enrichment.assert_called_once()
        call_kwargs = repository.update_enrichment.call_args[1]
        assert call_kwargs["lead_id"] == lead.id
        assert call_kwargs["status"] == LeadStatus.QUALIFIED


class TestEnrichSingle:
    """Tests for enrich_single method."""

    @pytest.mark.asyncio
    async def test_enrich_single_processes_specific_lead(self) -> None:
        """Test single lead enrichment by ID."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus

        config = EnrichmentConfig()

        lead_id = uuid4()
        lead = Mock()
        lead.id = lead_id
        lead.status = LeadStatus.NEW.value

        repository = AsyncMock()
        repository.get_by_id.return_value = lead
        repository.update_enrichment.return_value = lead

        enrichment_result = EnrichmentResult(
            lead_id=lead_id,
            confidence_score=8.0,
        )

        enrichment_service = Mock()
        enrichment_service.enrich_lead = AsyncMock(return_value=enrichment_result)
        enrichment_service.determine_status.return_value = LeadStatus.QUALIFIED
        enrichment_service.format_enrichment_data.return_value = {}

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        result = await pipeline.enrich_single(lead_id)

        # Verify lead was fetched
        repository.get_by_id.assert_called_once_with(lead_id)

        # Verify enrichment was performed
        enrichment_service.enrich_lead.assert_called_once_with(lead)

        # Verify result
        assert result.lead_id == lead_id
        assert result.confidence_score == 8.0

    @pytest.mark.asyncio
    async def test_enrich_single_raises_for_missing_lead(self) -> None:
        """Test error when lead not found."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline, LeadNotFoundError
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        lead_id = uuid4()

        repository = AsyncMock()
        repository.get_by_id.return_value = None

        enrichment_service = Mock()

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        with pytest.raises(LeadNotFoundError):
            await pipeline.enrich_single(lead_id)


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_pipeline_result_has_required_fields(self) -> None:
        """Test PipelineResult contains all statistics."""
        from teams.dawo.leads.enrichment.pipeline import PipelineResult

        result = PipelineResult(
            total_processed=10,
            successful=8,
            failed=2,
            qualified=6,
            researching=2,
            converted=0,
        )

        assert result.total_processed == 10
        assert result.successful == 8
        assert result.failed == 2
        assert result.qualified == 6
        assert result.researching == 2
        assert result.converted == 0

    def test_pipeline_result_has_status_flag(self) -> None:
        """Test PipelineResult has pipeline status."""
        from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus

        result = PipelineResult(
            total_processed=0,
            successful=0,
            failed=0,
            qualified=0,
            researching=0,
            converted=0,
            status=PipelineStatus.COMPLETE,
        )

        assert result.status == PipelineStatus.COMPLETE


class TestActivityLogging:
    """Tests for activity logging during enrichment."""

    @pytest.mark.asyncio
    async def test_adds_activity_log_on_enrichment(self) -> None:
        """Test activity log entry is created after enrichment."""
        from teams.dawo.leads.enrichment.pipeline import EnrichmentPipeline
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.schemas import EnrichmentResult
        from core.leads.models import LeadStatus, ActivityType

        config = EnrichmentConfig()

        lead = Mock()
        lead.id = uuid4()
        lead.status = LeadStatus.NEW.value

        repository = AsyncMock()
        repository.get_leads_for_enrichment.return_value = [lead]
        repository.update_enrichment.return_value = lead

        enrichment_result = EnrichmentResult(
            lead_id=lead.id,
            confidence_score=7.0,
        )

        enrichment_service = Mock()
        enrichment_service.enrich_lead = AsyncMock(return_value=enrichment_result)
        enrichment_service.determine_status.return_value = LeadStatus.QUALIFIED
        enrichment_service.format_enrichment_data.return_value = {}

        pipeline = EnrichmentPipeline(
            config=config,
            repository=repository,
            enrichment_service=enrichment_service,
        )

        await pipeline.execute()

        # Verify activity was logged
        repository.add_activity.assert_called_once()
        call_kwargs = repository.add_activity.call_args[1]
        assert call_kwargs["lead_id"] == lead.id
        assert call_kwargs["activity_type"] == ActivityType.ENRICHED
