"""Tests for Gmail schemas.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 1: Module structure - schemas
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from teams.dawo.leads.gmail.schemas import (
    GmailSendRequest,
    GmailSendResult,
    EmailMessage,
    SendQueueItem,
    SendStatus,
)


class TestEmailMessage:
    """Tests for EmailMessage dataclass."""

    def test_create_email_message(self) -> None:
        """Test basic EmailMessage creation."""
        msg = EmailMessage(
            to="test@example.com",
            from_email="sender@dawo.no",
            subject="Test Subject",
            body="Hello, this is a test.",
        )
        assert msg.to == "test@example.com"
        assert msg.from_email == "sender@dawo.no"
        assert msg.subject == "Test Subject"
        assert msg.body == "Hello, this is a test."

    def test_email_message_optional_fields(self) -> None:
        """Test EmailMessage optional fields default to None."""
        msg = EmailMessage(
            to="test@example.com",
            from_email="sender@dawo.no",
            subject="Test",
            body="Body",
        )
        assert msg.reply_to is None
        assert msg.cc is None

    def test_email_message_with_reply_to(self) -> None:
        """Test EmailMessage with reply_to field."""
        msg = EmailMessage(
            to="test@example.com",
            from_email="sender@dawo.no",
            subject="Test",
            body="Body",
            reply_to="reply@dawo.no",
        )
        assert msg.reply_to == "reply@dawo.no"


class TestGmailSendRequest:
    """Tests for GmailSendRequest dataclass."""

    def test_create_send_request(self) -> None:
        """Test basic GmailSendRequest creation."""
        lead_id = uuid4()
        msg = EmailMessage(
            to="test@example.com",
            from_email="sender@dawo.no",
            subject="Test",
            body="Body",
        )
        request = GmailSendRequest(
            lead_id=lead_id,
            message=msg,
            campaign="b2b_outreach",
        )
        assert request.lead_id == lead_id
        assert request.message == msg
        assert request.campaign == "b2b_outreach"


class TestGmailSendResult:
    """Tests for GmailSendResult dataclass."""

    def test_create_success_result(self) -> None:
        """Test creating a successful send result."""
        result = GmailSendResult(
            success=True,
            message_id="msg_123",
            thread_id="thread_456",
        )
        assert result.success is True
        assert result.message_id == "msg_123"
        assert result.thread_id == "thread_456"
        assert result.error is None

    def test_create_failure_result(self) -> None:
        """Test creating a failed send result."""
        result = GmailSendResult(
            success=False,
            error="Authentication failed",
        )
        assert result.success is False
        assert result.message_id is None
        assert result.thread_id is None
        assert result.error == "Authentication failed"


class TestSendQueueItem:
    """Tests for SendQueueItem dataclass."""

    def test_create_queue_item(self) -> None:
        """Test creating a send queue item."""
        lead_id = uuid4()
        item = SendQueueItem(
            lead_id=lead_id,
            subject="Test",
            body="Body text",
            to_email="test@example.com",
            campaign="b2b_outreach",
        )
        assert item.lead_id == lead_id
        assert item.subject == "Test"
        assert item.to_email == "test@example.com"
        assert item.status == SendStatus.PENDING

    def test_queue_item_default_status(self) -> None:
        """Test queue item defaults to PENDING status."""
        item = SendQueueItem(
            lead_id=uuid4(),
            subject="Test",
            body="Body",
            to_email="test@example.com",
            campaign="b2b_outreach",
        )
        assert item.status == SendStatus.PENDING


class TestSendStatus:
    """Tests for SendStatus enum."""

    def test_send_status_values(self) -> None:
        """Test all SendStatus values exist."""
        assert SendStatus.PENDING.value == "pending"
        assert SendStatus.SENDING.value == "sending"
        assert SendStatus.SENT.value == "sent"
        assert SendStatus.FAILED.value == "failed"
        assert SendStatus.RATE_LIMITED.value == "rate_limited"
        assert SendStatus.GDPR_REJECTED.value == "gdpr_rejected"
