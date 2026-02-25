"""Tests for Outreach Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachPipeline batch processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.outreach.schemas import (
    LeadType,
    OutreachDraft,
    GenerationResult,
    GenerationStatus,
)


class TestOutreachPipeline:
    """Tests for OutreachPipeline class."""

    @pytest.fixture
    def mock_lead_repository(self):
        """Create a mock lead repository."""
        repo = AsyncMock()
        # Create mock leads
        leads = []
        for i in range(5):
            lead = MagicMock()
            lead.id = uuid4()
            lead.company = f"Test Company {i}"
            lead.contact_name = f"Contact {i}"
            lead.status = "QUALIFIED"
            lead.confidence_score = 8.0
            leads.append(lead)

        repo.get_leads_for_outreach.return_value = leads
        repo.update_outreach.return_value = leads[0]
        return repo

    @pytest.fixture
    def mock_outreach_service(self):
        """Create a mock outreach service."""
        service = AsyncMock()
        service.generate_outreach.return_value = GenerationResult(
            lead_id=uuid4(),
            status=GenerationStatus.SUCCESS,
            draft=OutreachDraft(
                lead_id=uuid4(),
                template_id="hs-intro-v1",
                template_type=LeadType.HEALTH_STORE,
                subject="Test Subject",
                body="Test body with enough words " * 20,
                word_count=180,
                personalization_hooks=["test hook"],
                personalization_score=3,
                suggested_send_time=datetime.now(UTC),
            ),
            template_selection=None,
        )
        service.is_qualified_for_outreach.return_value = True
        service.prepare_for_approval.return_value = {"lead_summary": {}}
        return service

    @pytest.fixture
    def pipeline(self, mock_lead_repository, mock_outreach_service):
        """Create OutreachPipeline with mocked dependencies."""
        from teams.dawo.leads.outreach.pipeline import OutreachPipeline
        return OutreachPipeline(
            lead_repository=mock_lead_repository,
            outreach_service=mock_outreach_service,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_pipeline_result(self, pipeline):
        """execute should return PipelineResult."""
        from teams.dawo.leads.outreach.pipeline import PipelineResult
        result = await pipeline.execute()

        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_execute_queries_qualified_leads(self, pipeline, mock_lead_repository):
        """Should query for qualified leads with confidence >= 6."""
        await pipeline.execute()

        mock_lead_repository.get_leads_for_outreach.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_processes_leads_in_batch(self, pipeline, mock_outreach_service, mock_lead_repository):
        """Should process all leads from query."""
        await pipeline.execute()

        # Should call generate_outreach for each lead
        assert mock_outreach_service.generate_outreach.call_count == 5

    @pytest.mark.asyncio
    async def test_execute_respects_batch_size(self, mock_lead_repository, mock_outreach_service):
        """Should respect batch_size parameter."""
        from teams.dawo.leads.outreach.pipeline import OutreachPipeline
        pipeline = OutreachPipeline(
            lead_repository=mock_lead_repository,
            outreach_service=mock_outreach_service,
        )

        await pipeline.execute(batch_size=3)

        mock_lead_repository.get_leads_for_outreach.assert_called_with(limit=3)

    @pytest.mark.asyncio
    async def test_execute_tracks_statistics(self, pipeline):
        """Should track processing statistics."""
        result = await pipeline.execute()

        assert hasattr(result, "total_processed")
        assert hasattr(result, "successful")
        assert hasattr(result, "failed")

    @pytest.mark.asyncio
    async def test_execute_successful_count(self, pipeline):
        """Should count successful generations."""
        result = await pipeline.execute()

        assert result.successful == 5  # All 5 leads should succeed

    @pytest.fixture
    def mock_draft(self):
        """Create a mock draft with to_dict method."""
        draft = MagicMock()
        draft.to_dict.return_value = {"template_type": "health_store", "draft": {}}
        return draft

    @pytest.mark.asyncio
    async def test_execute_continues_on_individual_failure(self, pipeline, mock_outreach_service, mock_draft):
        """Should continue processing if one lead fails."""
        # First call succeeds, second fails, rest succeed
        mock_outreach_service.generate_outreach.side_effect = [
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error="Test error",
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
        ]

        result = await pipeline.execute()

        assert result.total_processed == 5
        assert result.successful == 4
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_execute_handles_exception_gracefully(self, pipeline, mock_outreach_service, mock_draft):
        """Should handle exceptions during processing gracefully."""
        mock_outreach_service.generate_outreach.side_effect = [
            Exception("Unexpected error"),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
        ]

        result = await pipeline.execute()

        assert result.total_processed == 5
        assert result.failed >= 1

    @pytest.mark.asyncio
    async def test_generate_single_returns_generation_result(self, pipeline, mock_outreach_service, mock_lead_repository):
        """generate_single should return GenerationResult."""
        lead_id = uuid4()
        mock_lead = MagicMock()
        mock_lead.id = lead_id
        mock_lead_repository.get_by_id.return_value = mock_lead

        result = await pipeline.generate_single(lead_id)

        assert isinstance(result, GenerationResult)

    @pytest.mark.asyncio
    async def test_generate_single_calls_service(self, pipeline, mock_outreach_service, mock_lead_repository):
        """generate_single should call outreach service."""
        lead_id = uuid4()
        mock_lead = MagicMock()
        mock_lead.id = lead_id
        mock_lead_repository.get_by_id.return_value = mock_lead

        await pipeline.generate_single(lead_id)

        mock_outreach_service.generate_outreach.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_single_returns_error_for_missing_lead(self, pipeline, mock_lead_repository):
        """generate_single should return error for missing lead."""
        lead_id = uuid4()
        mock_lead_repository.get_by_id.return_value = None

        result = await pipeline.generate_single(lead_id)

        assert result.status == GenerationStatus.FAILED
        assert "not found" in result.error.lower()

    def test_pipeline_accepts_dependencies_via_injection(self, mock_lead_repository, mock_outreach_service):
        """Pipeline should accept dependencies via injection."""
        from teams.dawo.leads.outreach.pipeline import OutreachPipeline
        pipeline = OutreachPipeline(
            lead_repository=mock_lead_repository,
            outreach_service=mock_outreach_service,
        )

        assert pipeline._lead_repository is mock_lead_repository
        assert pipeline._outreach_service is mock_outreach_service

    @pytest.mark.asyncio
    async def test_pipeline_result_has_status(self, pipeline):
        """PipelineResult should have status field."""
        result = await pipeline.execute()

        assert hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_pipeline_complete_status(self, pipeline):
        """Pipeline should have COMPLETE status when all succeed."""
        result = await pipeline.execute()

        assert result.status == "COMPLETE"

    @pytest.mark.asyncio
    async def test_pipeline_incomplete_status_on_partial_failures(self, pipeline, mock_outreach_service, mock_draft):
        """Pipeline should have INCOMPLETE status when some fail but some succeed."""
        mock_outreach_service.generate_outreach.side_effect = [
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error="Error",
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error="Error",
            ),
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.SUCCESS,
                draft=mock_draft,
                template_selection=None,
            ),
        ]

        result = await pipeline.execute()

        assert result.status == "INCOMPLETE"

    @pytest.mark.asyncio
    async def test_pipeline_failed_status_when_all_fail(self, pipeline, mock_outreach_service):
        """Pipeline should have FAILED status when all leads fail."""
        mock_outreach_service.generate_outreach.side_effect = [
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error="Error",
            ),
        ] * 5

        result = await pipeline.execute()

        assert result.status == "FAILED"

    @pytest.mark.asyncio
    async def test_execute_logs_activity(self, pipeline, mock_lead_repository, caplog):
        """Should log activity for each processed lead."""
        import logging
        with caplog.at_level(logging.INFO):
            await pipeline.execute()

        # Should have log entries for processing
        assert len(caplog.records) > 0

    @pytest.mark.asyncio
    async def test_pipeline_result_includes_errors(self, pipeline, mock_outreach_service):
        """PipelineResult should include error details."""
        mock_outreach_service.generate_outreach.side_effect = [
            GenerationResult(
                lead_id=uuid4(),
                status=GenerationStatus.FAILED,
                draft=None,
                template_selection=None,
                error="Test error message",
            ),
        ] * 5

        result = await pipeline.execute()

        assert hasattr(result, "errors")
        assert len(result.errors) > 0
