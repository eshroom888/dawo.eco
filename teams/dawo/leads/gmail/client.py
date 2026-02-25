"""Gmail API Client.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Wraps the Google Gmail API for sending emails.
Uses RetryMiddleware for all API calls.
Runs synchronous API calls in executor to avoid blocking.
"""

import asyncio
import base64
import logging
from datetime import datetime, UTC
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from teams.dawo.leads.gmail.config import GmailConfig
from teams.dawo.leads.gmail.credentials_manager import (
    GmailCredentialsManager,
    GmailAuthError,
)
from teams.dawo.leads.gmail.schemas import EmailMessage, GmailSendResult
from teams.dawo.middleware.retry import RetryMiddleware, RetryConfig

logger = logging.getLogger(__name__)


class GmailSendError(Exception):
    """Raised when Gmail send operation fails after retries."""

    pass


class GmailClient:
    """Gmail API client for sending emails.

    Wraps google-api-python-client with retry middleware.
    Runs synchronous Gmail API calls in thread pool executor.

    Attributes:
        _creds_manager: Credential manager (injected)
        _retry: Retry middleware for API calls
        _service: Cached Gmail API service instance
    """

    def __init__(
        self,
        credentials_manager: GmailCredentialsManager,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        """Initialize Gmail client.

        Args:
            credentials_manager: Gmail credentials manager (injected)
            retry_config: Optional retry configuration override
        """
        self._creds_manager = credentials_manager
        self._retry = RetryMiddleware(retry_config or RetryConfig(
            max_retries=3,
            base_delay=2.0,
            timeout=30.0,
        ))
        self._service = None

    def _build_service(self):
        """Build or return cached Gmail API service.

        Returns:
            Gmail API service resource

        Raises:
            GmailAuthError: If credentials are invalid
        """
        if self._service is not None:
            return self._service
        creds = self._creds_manager.get_credentials()
        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    async def send_message(self, message: EmailMessage) -> GmailSendResult:
        """Send email via Gmail API.

        Runs synchronous API call in executor to avoid blocking.
        Wraps with retry middleware for resilience.

        Args:
            message: Email message to send

        Returns:
            GmailSendResult with message_id and thread_id

        Raises:
            GmailSendError: If send fails after retries
            GmailAuthError: If authentication fails
        """
        async def _do_send():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._sync_send, message)

        result = await self._retry.execute_with_retry(
            _do_send,
            context="gmail_send",
        )

        if result.is_incomplete:
            raise GmailSendError(
                f"Send failed after {result.attempts} retries: {result.last_error}"
            )

        if not result.success:
            raise GmailSendError(f"Send failed: {result.last_error}")

        return result.response

    def _sync_send(self, message: EmailMessage) -> GmailSendResult:
        """Synchronous Gmail API send (runs in executor).

        Args:
            message: Email message to send

        Returns:
            GmailSendResult with Gmail IDs
        """
        service = self._build_service()
        mime_msg = self._construct_mime(message)
        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

        result = service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()

        return GmailSendResult(
            success=True,
            message_id=result.get("id"),
            thread_id=result.get("threadId"),
            sent_at=datetime.now(UTC),
        )

    def _construct_mime(self, message: EmailMessage) -> MIMEMultipart:
        """Construct MIME message from EmailMessage.

        Args:
            message: Email message data

        Returns:
            MIMEMultipart message ready for encoding
        """
        mime_msg = MIMEMultipart()
        mime_msg["To"] = message.to
        mime_msg["From"] = message.from_email
        mime_msg["Subject"] = message.subject

        if message.reply_to:
            mime_msg["Reply-To"] = message.reply_to

        if message.cc:
            mime_msg["Cc"] = message.cc

        mime_msg.attach(MIMEText(message.body, "plain", "utf-8"))
        return mime_msg


__all__ = [
    "GmailClient",
    "GmailSendError",
]
