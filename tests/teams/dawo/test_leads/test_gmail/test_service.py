"""Tests for Gmail Send Service.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 8: Email Send Service
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from teams.dawo.leads.gmail.service import GmailSendService
from teams.dawo.leads.gmail.client import GmailClient, GmailSendError
from teams.dawo.leads.gmail.credentials_manager import GmailAuthError
from teams.dawo.leads.gmail.gdpr_validator import GDPRPreSendValidator
from teams.dawo.leads.gmail.utm import UTMInjector
from teams.dawo.leads.gmail.signature import SignatureBuilder
from teams.dawo.leads.gmail.rate_limiter import GmailRateLimiter
from teams.dawo.leads.gmail.schemas import GmailSendResult
from teams.dawo.leads.gmail.config import GmailConfig, GmailRateLimitConfig
from core.leads.models import LeadStatus


@pytest.fixture
def mock_lead() -> MagicMock:
    """Provide mock lead for testing."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = "kontakt@helsekost.no"
    lead.company = "Helsekost AS"
    lead.status = LeadStatus.OUTREACH_PENDING.value
    lead.contact_count = 0
    lead.last_contacted_at = None
    lead.unsubscribed_at = None
    return lead


@pytest.fixture
def mock_gmail_client() -> AsyncMock:
    """Provide mock Gmail client."""
    client = AsyncMock(spec=GmailClient)
    client.send_message.return_value = GmailSendResult(
        success=True,
        message_id="msg_123",
        thread_id="thread_456",
        sent_at=datetime.now(UTC),
    )
    return client


@pytest.fixture
def mock_gdpr_validator() -> MagicMock:
    """Provide mock GDPR validator that passes."""
    validator = MagicMock(spec=GDPRPreSendValidator)
    validator.validate.return_value = (True, "OK")
    return validator


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Provide mock lead repository."""
    repo = AsyncMock()
    repo.update_send_result.return_value = MagicMock()
    repo.create_outreach_email.return_value = MagicMock()
    return repo


@pytest.fixture
def mock_discord() -> AsyncMock:
    """Provide mock Discord alerts."""
    return AsyncMock()


@pytest.fixture
def gmail_config() -> GmailConfig:
    """Provide Gmail config."""
    return GmailConfig(
        sender_email="sales@dawo.no",
        sender_name="Test Sender",
        company_address="Oslo, Norway",
    )


@pytest.fixture
def send_service(
    mock_gmail_client,
    mock_gdpr_validator,
    mock_repo,
    mock_discord,
    gmail_config,
) -> GmailSendService:
    """Provide fully mocked send service."""
    rate_config = GmailRateLimitConfig(max_per_minute=100, max_per_day=1000)
    return GmailSendService(
        gmail_client=mock_gmail_client,
        gdpr_validator=mock_gdpr_validator,
        utm_injector=UTMInjector(),
        signature_builder=SignatureBuilder(gmail_config),
        rate_limiter=GmailRateLimiter(rate_config),
        lead_repository=mock_repo,
        discord_alerts=mock_discord,
        config=gmail_config,
    )


class TestSendOutreach:
    """Tests for send_outreach method."""

    @pytest.mark.asyncio
    async def test_successful_send(
        self, send_service: GmailSendService, mock_lead: MagicMock
    ) -> None:
        """Test successful outreach email send."""
        result = await send_service.send_outreach(
            lead=mock_lead,
            subject="Test Subject",
            body="Test body text",
        )
        assert result.success is True
        assert result.message_id == "msg_123"

    @pytest.mark.asyncio
    async def test_gdpr_rejection(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
    ) -> None:
        """Test GDPR validation blocks send."""
        send_service._gdpr.validate.return_value = (
            False, "Lead has unsubscribed"
        )
        result = await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Body",
        )
        assert result.success is False
        assert "GDPR" in result.error

    @pytest.mark.asyncio
    async def test_send_updates_lead_via_update_send_result(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test successful send calls update_send_result with Gmail IDs."""
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Body",
        )
        mock_repo.update_send_result.assert_called_once_with(
            mock_lead.id,
            gmail_message_id="msg_123",
            gmail_thread_id="thread_456",
        )

    @pytest.mark.asyncio
    async def test_send_creates_outreach_email(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test successful send creates OutreachEmail record."""
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Body",
        )
        mock_repo.create_outreach_email.assert_called_once()
        call_kwargs = mock_repo.create_outreach_email.call_args.kwargs
        assert call_kwargs["lead_id"] == mock_lead.id
        assert call_kwargs["email_data"]["gmail_message_id"] == "msg_123"

    @pytest.mark.asyncio
    async def test_auth_failure_alerts_discord(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
        mock_discord: AsyncMock,
    ) -> None:
        """Test auth failure sends Discord alert."""
        send_service._client.send_message.side_effect = GmailAuthError("Token expired")
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Body",
        )
        mock_discord.send_api_error_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_failure_alerts_discord(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
        mock_discord: AsyncMock,
    ) -> None:
        """Test send failure sends Discord alert."""
        send_service._client.send_message.side_effect = GmailSendError("API error")
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Body",
        )
        mock_discord.send_api_error_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_failure_does_not_change_lead_status(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
        mock_repo: AsyncMock,
    ) -> None:
        """Test send failure does NOT change lead status."""
        send_service._client.send_message.side_effect = GmailSendError("Failed")
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Body",
        )
        mock_repo.update_send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_body_includes_utm_parameters(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
    ) -> None:
        """Test body with URLs gets UTM parameters."""
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Visit https://dawo.no for more.",
        )
        # Verify the sent message body contains UTM params
        call_args = send_service._client.send_message.call_args
        sent_message = call_args[0][0]  # First positional arg
        assert "utm_source=email" in sent_message.body

    @pytest.mark.asyncio
    async def test_body_includes_signature(
        self,
        send_service: GmailSendService,
        mock_lead: MagicMock,
    ) -> None:
        """Test body includes email signature and GDPR footer."""
        await send_service.send_outreach(
            lead=mock_lead,
            subject="Test",
            body="Hello.",
        )
        call_args = send_service._client.send_message.call_args
        sent_message = call_args[0][0]
        assert "Test Sender" in sent_message.body
        assert "Hvorfor mottok du denne e-posten?" in sent_message.body
