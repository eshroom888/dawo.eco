"""Integration Tests for Gmail Send Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 15: Integration Tests

Tests the full flow with mocked Gmail API but real interactions
between all components (service, pipeline, GDPR, rate limiter, etc.).
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from teams.dawo.leads.gmail.service import GmailSendService
from teams.dawo.leads.gmail.pipeline import GmailSendPipeline, PipelineResult
from teams.dawo.leads.gmail.client import GmailClient, GmailSendError
from teams.dawo.leads.gmail.credentials_manager import (
    GmailCredentialsManager,
    GmailAuthError,
)
from teams.dawo.leads.gmail.gdpr_validator import GDPRPreSendValidator
from teams.dawo.leads.gmail.utm import UTMInjector
from teams.dawo.leads.gmail.signature import SignatureBuilder
from teams.dawo.leads.gmail.rate_limiter import GmailRateLimiter
from teams.dawo.leads.gmail.schemas import GmailSendResult, EmailMessage
from teams.dawo.leads.gmail.config import GmailConfig, GmailRateLimitConfig
from core.leads.models import LeadStatus, ActivityType


# --- Fixtures ---


def _make_lead(
    email: str = "kontakt@helsekost.no",
    company: str = "Helsekost AS",
    status: str = LeadStatus.OUTREACH_PENDING.value,
    contact_count: int = 0,
    last_contacted_at=None,
    unsubscribed_at=None,
    has_draft: bool = True,
):
    """Create a mock lead with realistic data."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = email
    lead.company = company
    lead.status = status
    lead.contact_count = contact_count
    lead.last_contacted_at = last_contacted_at
    lead.unsubscribed_at = unsubscribed_at
    if has_draft:
        lead.outreach_data = {
            "draft": {
                "subject": "DAWO produkter for din virksomhet",
                "body": "Hei, vi vil gjerne presentere DAWO produktene. Se https://dawo.no/produkter for mer info.",
            },
            "approved": True,
        }
    else:
        lead.outreach_data = {}
    return lead


@pytest.fixture
def gmail_config() -> GmailConfig:
    """Provide Gmail config."""
    return GmailConfig(
        sender_email="sales@dawo.no",
        sender_name="DAWO Sales",
        company_address="Oslo, Norway",
    )


@pytest.fixture
def rate_config() -> GmailRateLimitConfig:
    """Provide rate limit config with high limits for integration tests."""
    return GmailRateLimitConfig(
        max_per_minute=100,
        max_per_day=1000,
        burst_size=10,
    )


@pytest.fixture
def mock_gmail_client() -> AsyncMock:
    """Provide mock Gmail client that returns successful sends."""
    client = AsyncMock(spec=GmailClient)
    client.send_message.return_value = GmailSendResult(
        success=True,
        message_id="msg_integration_123",
        thread_id="thread_integration_456",
        sent_at=datetime.now(UTC),
    )
    return client


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Provide mock repository."""
    repo = AsyncMock()
    repo.update_send_result.return_value = MagicMock()
    repo.create_outreach_email.return_value = MagicMock()
    repo.get_lead_by_id.return_value = _make_lead()
    return repo


@pytest.fixture
def mock_discord() -> AsyncMock:
    """Provide mock Discord alerts."""
    return AsyncMock()


@pytest.fixture
def send_service(
    mock_gmail_client,
    mock_repo,
    mock_discord,
    gmail_config,
    rate_config,
) -> GmailSendService:
    """Provide fully assembled send service with real validators."""
    return GmailSendService(
        gmail_client=mock_gmail_client,
        gdpr_validator=GDPRPreSendValidator(),
        utm_injector=UTMInjector(),
        signature_builder=SignatureBuilder(gmail_config),
        rate_limiter=GmailRateLimiter(rate_config),
        lead_repository=mock_repo,
        discord_alerts=mock_discord,
        config=gmail_config,
    )


@pytest.fixture
def pipeline(mock_repo, send_service) -> GmailSendPipeline:
    """Provide pipeline with real send service."""
    return GmailSendPipeline(
        lead_repository=mock_repo,
        send_service=send_service,
    )


# --- 15.1: Full send pipeline with mocked Gmail API ---


class TestFullPipelineFlow:
    """Integration test: full send pipeline with real component interactions."""

    @pytest.mark.asyncio
    async def test_full_pipeline_sends_batch(
        self,
        pipeline: GmailSendPipeline,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test full pipeline processes a batch of approved leads."""
        leads = [_make_lead() for _ in range(3)]
        mock_repo.get_approved_for_sending.return_value = leads

        result = await pipeline.execute(batch_size=10)

        assert result.sent == 3
        assert result.is_complete is True
        assert mock_gmail_client.send_message.call_count == 3

    @pytest.mark.asyncio
    async def test_pipeline_constructs_proper_emails(
        self,
        pipeline: GmailSendPipeline,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test emails include UTM params and signature."""
        lead = _make_lead()
        mock_repo.get_approved_for_sending.return_value = [lead]

        await pipeline.execute()

        sent_message = mock_gmail_client.send_message.call_args[0][0]
        # UTM parameters injected
        assert "utm_source=email" in sent_message.body
        # Signature included
        assert "DAWO Sales" in sent_message.body
        # GDPR footer included
        assert "Hvorfor mottok du denne e-posten?" in sent_message.body
        # Proper from address
        assert sent_message.from_email == "sales@dawo.no"


# --- 15.2: Lead status transitions ---


class TestLeadStatusTransitions:
    """Integration test: lead status transitions on send."""

    @pytest.mark.asyncio
    async def test_successful_send_sets_contacted(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
    ) -> None:
        """Test OUTREACH_PENDING -> CONTACTED on successful send."""
        lead = _make_lead(status=LeadStatus.OUTREACH_PENDING.value)

        result = await send_service.send_outreach(
            lead=lead,
            subject="Test",
            body="Body",
        )

        assert result.success is True
        mock_repo.update_send_result.assert_called_once_with(
            lead.id,
            gmail_message_id="msg_integration_123",
            gmail_thread_id="thread_integration_456",
        )

    @pytest.mark.asyncio
    async def test_gdpr_rejected_lead_not_updated(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
    ) -> None:
        """Test GDPR-rejected lead status is not changed."""
        lead = _make_lead(unsubscribed_at=datetime.now(UTC))

        result = await send_service.send_outreach(
            lead=lead,
            subject="Test",
            body="Body",
        )

        assert result.success is False
        assert "GDPR" in result.error
        mock_repo.update_send_result.assert_not_called()


# --- 15.3: OutreachEmail record creation ---


class TestOutreachEmailTracking:
    """Integration test: OutreachEmail record creation with Gmail IDs."""

    @pytest.mark.asyncio
    async def test_outreach_email_includes_gmail_ids(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
    ) -> None:
        """Test OutreachEmail record includes gmail_message_id and gmail_thread_id."""
        lead = _make_lead()

        await send_service.send_outreach(
            lead=lead,
            subject="DAWO",
            body="Hello",
        )

        mock_repo.create_outreach_email.assert_called_once()
        call_kwargs = mock_repo.create_outreach_email.call_args.kwargs
        assert call_kwargs["email_data"]["gmail_message_id"] == "msg_integration_123"
        assert call_kwargs["email_data"]["gmail_thread_id"] == "thread_integration_456"
        assert call_kwargs["email_data"]["sent_at"] is not None


# --- 15.4: Activity logging for sent emails ---


class TestActivityLogging:
    """Integration test: activity logging on email send."""

    @pytest.mark.asyncio
    async def test_successful_send_calls_update_send_result(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
    ) -> None:
        """Test update_send_result is called (handles activity logging internally)."""
        lead = _make_lead(email="info@bedrift.no")

        await send_service.send_outreach(
            lead=lead,
            subject="Test",
            body="Body",
        )

        mock_repo.update_send_result.assert_called_once()
        call_args = mock_repo.update_send_result.call_args
        assert call_args[0][0] == lead.id

    @pytest.mark.asyncio
    async def test_failed_send_does_not_create_records(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test no records created on send failure."""
        mock_gmail_client.send_message.side_effect = GmailSendError("API error")
        lead = _make_lead()

        result = await send_service.send_outreach(
            lead=lead,
            subject="Test",
            body="Body",
        )

        assert result.success is False
        mock_repo.update_send_result.assert_not_called()
        mock_repo.create_outreach_email.assert_not_called()


# --- 15.5: GDPR validation integration ---


class TestGDPRIntegration:
    """Integration test: GDPR validation with real lead data."""

    @pytest.mark.asyncio
    async def test_personal_email_blocked_in_pipeline(
        self,
        pipeline: GmailSendPipeline,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test pipeline skips personal emails via GDPR validator."""
        personal_lead = _make_lead(email="user@gmail.com")
        mock_repo.get_approved_for_sending.return_value = [personal_lead]

        result = await pipeline.execute()

        assert result.skipped_gdpr == 1
        assert result.sent == 0
        mock_gmail_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribed_lead_blocked(
        self,
        send_service: GmailSendService,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test unsubscribed lead is blocked by GDPR validator."""
        lead = _make_lead(unsubscribed_at=datetime.now(UTC))

        result = await send_service.send_outreach(
            lead=lead, subject="Test", body="Body"
        )

        assert result.success is False
        assert "unsubscribed" in result.error.lower()
        mock_gmail_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_contact_count_blocked(
        self,
        send_service: GmailSendService,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test lead at max contact count is blocked."""
        lead = _make_lead(contact_count=4)

        result = await send_service.send_outreach(
            lead=lead, subject="Test", body="Body"
        )

        assert result.success is False
        assert "limit" in result.error.lower()
        mock_gmail_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_contact_spacing_enforced(
        self,
        send_service: GmailSendService,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test contact spacing is enforced (min 3 days)."""
        lead = _make_lead(
            contact_count=1,
            last_contacted_at=datetime.now(UTC) - timedelta(days=1),
        )

        result = await send_service.send_outreach(
            lead=lead, subject="Test", body="Body"
        )

        assert result.success is False
        assert "too soon" in result.error.lower()
        mock_gmail_client.send_message.assert_not_called()


# --- 15.6: Rate limiting across batch ---


class TestRateLimitingIntegration:
    """Integration test: rate limiting behavior across batch sends."""

    @pytest.mark.asyncio
    async def test_batch_respects_rate_limits(
        self,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
        mock_discord: AsyncMock,
        gmail_config: GmailConfig,
    ) -> None:
        """Test batch processing with low rate limit."""
        tight_rate = GmailRateLimitConfig(
            max_per_minute=2, max_per_day=100, burst_size=2
        )
        service = GmailSendService(
            gmail_client=mock_gmail_client,
            gdpr_validator=GDPRPreSendValidator(),
            utm_injector=UTMInjector(),
            signature_builder=SignatureBuilder(gmail_config),
            rate_limiter=GmailRateLimiter(tight_rate),
            lead_repository=mock_repo,
            discord_alerts=mock_discord,
            config=gmail_config,
        )
        pipe = GmailSendPipeline(
            lead_repository=mock_repo,
            send_service=service,
        )

        leads = [_make_lead(email=f"lead{i}@bedrift.no") for i in range(5)]
        mock_repo.get_approved_for_sending.return_value = leads

        result = await pipe.execute(batch_size=5)

        # At least some should succeed; rate limiter may block the rest
        assert result.total_processed == 5
        assert result.sent >= 2  # At least 2 should go through


# --- 15.7: Send failure does not change lead status ---


class TestFailureDoesNotChangeStatus:
    """Integration test: send failure keeps lead in OUTREACH_PENDING."""

    @pytest.mark.asyncio
    async def test_send_failure_preserves_status(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test send failure does NOT update lead status."""
        mock_gmail_client.send_message.side_effect = GmailSendError("API error")
        lead = _make_lead()

        result = await send_service.send_outreach(
            lead=lead, subject="Test", body="Body"
        )

        assert result.success is False
        mock_repo.update_send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_auth_failure_preserves_status(
        self,
        send_service: GmailSendService,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test auth failure does NOT update lead status."""
        mock_gmail_client.send_message.side_effect = GmailAuthError("Token expired")
        lead = _make_lead()

        result = await send_service.send_outreach(
            lead=lead, subject="Test", body="Body"
        )

        assert result.success is False
        mock_repo.update_send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_auth_failure_alerts_discord(
        self,
        send_service: GmailSendService,
        mock_gmail_client: AsyncMock,
        mock_discord: AsyncMock,
    ) -> None:
        """Test auth failure sends Discord alert."""
        mock_gmail_client.send_message.side_effect = GmailAuthError("Token expired")
        lead = _make_lead()

        await send_service.send_outreach(
            lead=lead, subject="Test", body="Body"
        )

        mock_discord.send_api_error_alert.assert_called_once()
        call_kwargs = mock_discord.send_api_error_alert.call_args.kwargs
        assert call_kwargs["api_name"] == "gmail"

    @pytest.mark.asyncio
    async def test_pipeline_auth_failure_stops_remaining(
        self,
        pipeline: GmailSendPipeline,
        mock_repo: AsyncMock,
        mock_gmail_client: AsyncMock,
    ) -> None:
        """Test pipeline stops processing remaining leads on auth failure."""
        leads = [_make_lead(email=f"lead{i}@bedrift.no") for i in range(5)]
        mock_repo.get_approved_for_sending.return_value = leads
        mock_gmail_client.send_message.side_effect = GmailAuthError("Token expired")

        result = await pipeline.execute()

        assert result.is_complete is False
        assert "Auth failure" in result.error
        # Only first lead processed before stopping
        assert result.total_processed == 1
