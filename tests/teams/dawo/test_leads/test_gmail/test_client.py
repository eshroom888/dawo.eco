"""Tests for Gmail API Client.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 3: Gmail API Client
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from email.mime.multipart import MIMEMultipart

from googleapiclient.errors import HttpError

from teams.dawo.leads.gmail.client import GmailClient, GmailSendError
from teams.dawo.leads.gmail.schemas import EmailMessage, GmailSendResult
from teams.dawo.leads.gmail.credentials_manager import GmailCredentialsManager, GmailAuthError
from teams.dawo.middleware.retry import RetryConfig


@pytest.fixture
def mock_creds_manager() -> MagicMock:
    """Provide mock credentials manager."""
    manager = MagicMock(spec=GmailCredentialsManager)
    creds = MagicMock()
    creds.valid = True
    manager.get_credentials.return_value = creds
    return manager


@pytest.fixture
def gmail_client(mock_creds_manager: MagicMock) -> GmailClient:
    """Provide Gmail client with mocked dependencies."""
    return GmailClient(
        credentials_manager=mock_creds_manager,
        retry_config=RetryConfig(max_retries=1, base_delay=0.01, timeout=5.0),
    )


@pytest.fixture
def sample_message() -> EmailMessage:
    """Provide sample email message."""
    return EmailMessage(
        to="lead@company.no",
        from_email="sales@dawo.no",
        subject="DAWO produkter for din virksomhet",
        body="Hei, vi vil gjerne presentere DAWO produktene.",
    )


class TestGmailClientInit:
    """Tests for GmailClient initialization."""

    def test_init_with_custom_retry_config(
        self, mock_creds_manager: MagicMock
    ) -> None:
        """Test initialization with custom retry config."""
        config = RetryConfig(max_retries=5, base_delay=1.0)
        client = GmailClient(
            credentials_manager=mock_creds_manager,
            retry_config=config,
        )
        assert client._retry._config.max_retries == 5

    def test_init_with_default_retry_config(
        self, mock_creds_manager: MagicMock
    ) -> None:
        """Test initialization with default retry config."""
        client = GmailClient(credentials_manager=mock_creds_manager)
        assert client._retry._config.max_retries == 3
        assert client._retry._config.base_delay == 2.0


class TestMIMEConstruction:
    """Tests for MIME message construction."""

    def test_construct_mime_basic(
        self, gmail_client: GmailClient, sample_message: EmailMessage
    ) -> None:
        """Test basic MIME construction with required fields."""
        mime = gmail_client._construct_mime(sample_message)
        assert mime["To"] == "lead@company.no"
        assert mime["From"] == "sales@dawo.no"
        assert mime["Subject"] == "DAWO produkter for din virksomhet"

    def test_construct_mime_with_reply_to(
        self, gmail_client: GmailClient
    ) -> None:
        """Test MIME construction with Reply-To header."""
        msg = EmailMessage(
            to="lead@company.no",
            from_email="sales@dawo.no",
            subject="Test",
            body="Body",
            reply_to="reply@dawo.no",
        )
        mime = gmail_client._construct_mime(msg)
        assert mime["Reply-To"] == "reply@dawo.no"

    def test_construct_mime_with_cc(
        self, gmail_client: GmailClient
    ) -> None:
        """Test MIME construction with CC header."""
        msg = EmailMessage(
            to="lead@company.no",
            from_email="sales@dawo.no",
            subject="Test",
            body="Body",
            cc="cc@dawo.no",
        )
        mime = gmail_client._construct_mime(msg)
        assert mime["Cc"] == "cc@dawo.no"

    def test_construct_mime_body_is_plain_text(
        self, gmail_client: GmailClient, sample_message: EmailMessage
    ) -> None:
        """Test MIME body is plain text (not HTML)."""
        mime = gmail_client._construct_mime(sample_message)
        payload = mime.get_payload()
        assert len(payload) == 1
        assert payload[0].get_content_type() == "text/plain"

    def test_construct_mime_utf8_encoding(
        self, gmail_client: GmailClient
    ) -> None:
        """Test MIME supports Norwegian characters."""
        msg = EmailMessage(
            to="test@example.no",
            from_email="sender@dawo.no",
            subject="Norsk emne med æøå",
            body="Hei, dette er en melding med norske tegn: æ, ø, å.",
        )
        mime = gmail_client._construct_mime(msg)
        payload = mime.get_payload()[0]
        assert payload.get_charset() == "utf-8"


class TestGmailClientSend:
    """Tests for Gmail send operations."""

    @patch("teams.dawo.leads.gmail.client.build")
    @pytest.mark.asyncio
    async def test_sync_send_success(
        self,
        mock_build: MagicMock,
        gmail_client: GmailClient,
        sample_message: EmailMessage,
    ) -> None:
        """Test successful synchronous send."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "msg_123",
            "threadId": "thread_456",
            "labelIds": ["SENT"],
        }

        result = gmail_client._sync_send(sample_message)

        assert result.success is True
        assert result.message_id == "msg_123"
        assert result.thread_id == "thread_456"
        assert result.sent_at is not None

    @patch("teams.dawo.leads.gmail.client.build")
    def test_sync_send_auth_error(
        self,
        mock_build: MagicMock,
        gmail_client: GmailClient,
        sample_message: EmailMessage,
    ) -> None:
        """Test sync send with auth error from credentials."""
        gmail_client._creds_manager.get_credentials.side_effect = GmailAuthError("Token expired")

        with pytest.raises(GmailAuthError):
            gmail_client._sync_send(sample_message)


class TestGmailClientHttpErrors:
    """Tests for Gmail API HTTP error handling (14.5)."""

    @patch("teams.dawo.leads.gmail.client.build")
    def test_401_unauthorized_error(
        self,
        mock_build: MagicMock,
        gmail_client: GmailClient,
        sample_message: EmailMessage,
    ) -> None:
        """Test 401 Unauthorized raises from sync_send."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_resp = MagicMock(status=401, reason="Unauthorized")
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
            HttpError(mock_resp, b"Invalid credentials")
        )
        with pytest.raises(HttpError) as exc_info:
            gmail_client._sync_send(sample_message)
        assert exc_info.value.resp.status == 401

    @patch("teams.dawo.leads.gmail.client.build")
    def test_403_forbidden_error(
        self,
        mock_build: MagicMock,
        gmail_client: GmailClient,
        sample_message: EmailMessage,
    ) -> None:
        """Test 403 Forbidden error (insufficient permissions)."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_resp = MagicMock(status=403, reason="Forbidden")
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
            HttpError(mock_resp, b"Insufficient permissions")
        )
        with pytest.raises(HttpError) as exc_info:
            gmail_client._sync_send(sample_message)
        assert exc_info.value.resp.status == 403

    @patch("teams.dawo.leads.gmail.client.build")
    def test_429_rate_limit_error(
        self,
        mock_build: MagicMock,
        gmail_client: GmailClient,
        sample_message: EmailMessage,
    ) -> None:
        """Test 429 Too Many Requests (Gmail rate limit)."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_resp = MagicMock(status=429, reason="Too Many Requests")
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
            HttpError(mock_resp, b"Rate limit exceeded")
        )
        with pytest.raises(HttpError) as exc_info:
            gmail_client._sync_send(sample_message)
        assert exc_info.value.resp.status == 429

    @patch("teams.dawo.leads.gmail.client.build")
    def test_500_internal_server_error(
        self,
        mock_build: MagicMock,
        gmail_client: GmailClient,
        sample_message: EmailMessage,
    ) -> None:
        """Test 500 Internal Server Error from Gmail API."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_resp = MagicMock(status=500, reason="Internal Server Error")
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
            HttpError(mock_resp, b"Backend error")
        )
        with pytest.raises(HttpError) as exc_info:
            gmail_client._sync_send(sample_message)
        assert exc_info.value.resp.status == 500
