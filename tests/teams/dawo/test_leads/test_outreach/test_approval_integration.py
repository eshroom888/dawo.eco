"""Tests for Outreach Approval Queue Integration.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachApprovalIntegration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.outreach.schemas import (
    LeadType,
    OutreachDraft,
)


class TestOutreachApprovalIntegration:
    """Tests for OutreachApprovalIntegration class."""

    @pytest.fixture
    def mock_lead(self):
        """Create a mock lead object."""
        lead = MagicMock()
        lead.id = uuid4()
        lead.company = "Test Helse AS"
        lead.first_name = "Erik"
        lead.last_name = "Hansen"
        lead.email = "erik@test.no"
        lead.country = "Norway"
        lead.industry = "Health Products"
        lead.website_url = "https://testhelse.no"
        return lead

    @pytest.fixture
    def sample_draft(self, mock_lead):
        """Create a sample outreach draft."""
        return OutreachDraft(
            lead_id=mock_lead.id,
            template_id="hs-intro-v1",
            template_type=LeadType.HEALTH_STORE,
            subject="Samarbeid med DAWO",
            body="Test email body " * 20,
            word_count=180,
            personalization_hooks=["økologiske produkter", "naturlige helseløsninger"],
            personalization_score=3,
            suggested_send_time=datetime.now(UTC),
        )

    @pytest.fixture
    def integration(self):
        """Create OutreachApprovalIntegration instance."""
        from teams.dawo.leads.outreach.approval_integration import OutreachApprovalIntegration
        return OutreachApprovalIntegration()

    @pytest.mark.asyncio
    async def test_submit_to_queue_returns_dict(self, integration, sample_draft, mock_lead):
        """submit_to_queue should return approval item dict."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_source_type(self, integration, sample_draft, mock_lead):
        """Approval item should have source_type b2b_outreach."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert result["source_type"] == "b2b_outreach"

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_content_type(self, integration, sample_draft, mock_lead):
        """Approval item should have content_type email."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert result["content_type"] == "email"

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_title(self, integration, sample_draft, mock_lead):
        """Approval item should have title with company name."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "title" in result
        assert mock_lead.company in result["title"]

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_preview(self, integration, sample_draft, mock_lead):
        """Approval item should have preview (subject line)."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "preview" in result
        assert result["preview"] == sample_draft.subject

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_full_content(self, integration, sample_draft, mock_lead):
        """Approval item should have full_content (email body)."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "full_content" in result
        assert result["full_content"] == sample_draft.body

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_metadata(self, integration, sample_draft, mock_lead):
        """Approval item should have metadata dict."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "metadata" in result
        assert isinstance(result["metadata"], dict)

    def test_get_display_data_returns_dict(self, integration, sample_draft, mock_lead):
        """get_display_data should return dict."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert isinstance(result, dict)

    def test_get_display_data_has_lead_summary(self, integration, sample_draft, mock_lead):
        """Display data should have lead_summary."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert "lead_summary" in result
        assert result["lead_summary"]["company"] == mock_lead.company

    def test_get_display_data_has_contact_info(self, integration, sample_draft, mock_lead):
        """Display data should have contact information."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert "contact_name" in result["lead_summary"]
        assert "email" in result["lead_summary"]

    def test_get_display_data_has_personalization(self, integration, sample_draft, mock_lead):
        """Display data should have personalization hooks."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert "personalization_hooks" in result
        assert len(result["personalization_hooks"]) == 2

    def test_get_display_data_has_template_type(self, integration, sample_draft, mock_lead):
        """Display data should have template type."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert "template_type" in result
        assert result["template_type"] == "health_store"

    def test_get_display_data_has_suggested_send_time(self, integration, sample_draft, mock_lead):
        """Display data should have suggested send time."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert "suggested_send_time" in result

    def test_get_display_data_has_location(self, integration, sample_draft, mock_lead):
        """Display data should have location info."""
        result = integration.get_display_data(sample_draft, mock_lead)

        assert "country" in result["lead_summary"]

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_quality_score(self, integration, sample_draft, mock_lead):
        """Approval item should have quality_score based on personalization."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "quality_score" in result
        assert result["quality_score"] == sample_draft.personalization_score

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_compliance_status(self, integration, sample_draft, mock_lead):
        """Approval item should have compliance_status."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "compliance_status" in result
        # B2B outreach doesn't require EU health claims check
        assert result["compliance_status"] == "COMPLIANT"

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_lead_id_in_metadata(self, integration, sample_draft, mock_lead):
        """Metadata should include lead_id."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "lead_id" in result["metadata"]
        assert result["metadata"]["lead_id"] == str(mock_lead.id)

    @pytest.mark.asyncio
    async def test_submit_to_queue_has_template_id_in_metadata(self, integration, sample_draft, mock_lead):
        """Metadata should include template_id."""
        result = await integration.submit_to_queue(sample_draft, mock_lead)

        assert "template_id" in result["metadata"]
        assert result["metadata"]["template_id"] == sample_draft.template_id
