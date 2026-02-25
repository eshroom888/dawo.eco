"""Tests for Gmail Send Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 9: Send Pipeline
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.leads.gmail.pipeline import GmailSendPipeline, PipelineResult
from teams.dawo.leads.gmail.schemas import GmailSendResult
from teams.dawo.leads.gmail.credentials_manager import GmailAuthError
from core.leads.models import LeadStatus


def _make_mock_lead(status="outreach_pending", has_draft=True):
    """Create a mock lead with outreach data."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = f"test-{lead.id}@company.no"
    lead.company = "Test AS"
    lead.status = status
    lead.contact_count = 0
    lead.last_contacted_at = None
    lead.unsubscribed_at = None
    if has_draft:
        lead.outreach_data = {
            "draft": {
                "subject": "DAWO produkter",
                "body": "Hei, vi vil gjerne presentere DAWO.",
            },
            "approved": True,
        }
    else:
        lead.outreach_data = {}
    return lead


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Provide mock repository."""
    repo = AsyncMock()
    repo.get_approved_for_sending.return_value = [
        _make_mock_lead(),
        _make_mock_lead(),
        _make_mock_lead(),
    ]
    repo.get_lead_by_id.return_value = _make_mock_lead()
    return repo


@pytest.fixture
def mock_send_service() -> AsyncMock:
    """Provide mock send service."""
    service = AsyncMock()
    service.send_outreach.return_value = GmailSendResult(
        success=True,
        message_id="msg_123",
        thread_id="thread_456",
        sent_at=datetime.now(UTC),
    )
    return service


@pytest.fixture
def pipeline(mock_repo, mock_send_service) -> GmailSendPipeline:
    """Provide pipeline with mocked dependencies."""
    return GmailSendPipeline(
        lead_repository=mock_repo,
        send_service=mock_send_service,
    )


class TestPipelineExecute:
    """Tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_execute_sends_all_approved(
        self, pipeline: GmailSendPipeline, mock_send_service: AsyncMock
    ) -> None:
        """Test pipeline sends to all approved leads."""
        result = await pipeline.execute(batch_size=10)
        assert result.sent == 3
        assert result.total_processed == 3
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_execute_tracks_gdpr_rejections(
        self, pipeline: GmailSendPipeline, mock_send_service: AsyncMock
    ) -> None:
        """Test pipeline tracks GDPR rejections."""
        mock_send_service.send_outreach.return_value = GmailSendResult(
            success=False, error="GDPR: Lead has unsubscribed"
        )
        result = await pipeline.execute()
        assert result.skipped_gdpr == 3

    @pytest.mark.asyncio
    async def test_execute_continues_on_individual_failure(
        self, pipeline: GmailSendPipeline, mock_send_service: AsyncMock
    ) -> None:
        """Test pipeline continues after individual send failure."""
        success = GmailSendResult(success=True, message_id="msg_1", thread_id="t_1", sent_at=datetime.now(UTC))
        failure = GmailSendResult(success=False, error="API Error")
        mock_send_service.send_outreach.side_effect = [success, failure, success]

        result = await pipeline.execute()
        assert result.sent == 2
        assert result.failed == 1
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_execute_stops_on_auth_failure(
        self, pipeline: GmailSendPipeline, mock_send_service: AsyncMock
    ) -> None:
        """Test pipeline stops when auth fails (affects all sends)."""
        mock_send_service.send_outreach.side_effect = GmailAuthError("Token expired")

        result = await pipeline.execute()
        assert result.is_complete is False
        assert "Auth failure" in result.error
        # Should stop after first failure
        assert result.total_processed == 1

    @pytest.mark.asyncio
    async def test_execute_empty_draft_skipped(
        self, pipeline: GmailSendPipeline, mock_repo: AsyncMock
    ) -> None:
        """Test leads with empty drafts are skipped."""
        mock_repo.get_approved_for_sending.return_value = [
            _make_mock_lead(has_draft=False),
        ]
        result = await pipeline.execute()
        assert result.failed == 1
        assert result.sent == 0

    @pytest.mark.asyncio
    async def test_execute_query_failure(
        self, pipeline: GmailSendPipeline, mock_repo: AsyncMock
    ) -> None:
        """Test pipeline handles query failure."""
        mock_repo.get_approved_for_sending.side_effect = Exception("DB error")
        result = await pipeline.execute()
        assert result.is_complete is False
        assert "Query failed" in result.error


class TestPipelineSendSingle:
    """Tests for single send."""

    @pytest.mark.asyncio
    async def test_send_single_success(
        self, pipeline: GmailSendPipeline
    ) -> None:
        """Test sending to a single lead."""
        lead_id = uuid4()
        result = await pipeline.send_single(lead_id)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_send_single_lead_not_found(
        self, pipeline: GmailSendPipeline, mock_repo: AsyncMock
    ) -> None:
        """Test error when lead is not found."""
        mock_repo.get_lead_by_id.return_value = None
        with pytest.raises(ValueError, match="Lead not found"):
            await pipeline.send_single(uuid4())

    @pytest.mark.asyncio
    async def test_send_single_no_draft(
        self, pipeline: GmailSendPipeline, mock_repo: AsyncMock
    ) -> None:
        """Test error when lead has no approved draft."""
        mock_repo.get_lead_by_id.return_value = _make_mock_lead(has_draft=False)
        with pytest.raises(ValueError, match="no approved draft"):
            await pipeline.send_single(uuid4())
