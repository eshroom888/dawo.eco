"""Tests for GDPR Pre-Send Validator.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 6: GDPR Pre-Send Validation
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from teams.dawo.leads.gmail.gdpr_validator import (
    GDPRPreSendValidator,
    MAX_OUTREACH_EMAILS,
    MIN_CONTACT_SPACING_DAYS,
    PERSONAL_EMAIL_DOMAINS,
)
from core.leads.models import LeadStatus


@pytest.fixture
def validator() -> GDPRPreSendValidator:
    """Provide GDPR validator instance."""
    return GDPRPreSendValidator()


@pytest.fixture
def valid_lead() -> MagicMock:
    """Provide a valid lead for sending."""
    lead = MagicMock()
    lead.email = "kontakt@helsekost-oslo.no"
    lead.status = LeadStatus.OUTREACH_PENDING.value
    lead.contact_count = 0
    lead.last_contacted_at = None
    lead.unsubscribed_at = None
    return lead


class TestGDPRValidation:
    """Tests for GDPR validation rules."""

    def test_valid_lead_passes(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test valid lead passes all checks."""
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is True
        assert reason == "OK"

    def test_unsubscribed_lead_rejected(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test unsubscribed lead is rejected."""
        valid_lead.unsubscribed_at = datetime.now(UTC)
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "unsubscribed" in reason.lower()

    def test_lost_lead_rejected(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test LOST status lead is rejected."""
        valid_lead.status = LeadStatus.LOST.value
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "lost" in reason.lower()

    def test_converted_lead_rejected(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test CONVERTED status lead is rejected."""
        valid_lead.status = LeadStatus.CONVERTED.value
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "customer" in reason.lower()

    def test_max_outreach_limit_rejected(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test lead at max contact count is rejected."""
        valid_lead.contact_count = MAX_OUTREACH_EMAILS
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "limit" in reason.lower()

    def test_contact_spacing_too_soon(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test lead contacted too recently is rejected."""
        valid_lead.contact_count = 1
        valid_lead.last_contacted_at = datetime.now(UTC) - timedelta(days=1)
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "too soon" in reason.lower()

    def test_contact_spacing_ok_after_3_days(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test lead contacted 3+ days ago passes spacing check."""
        valid_lead.contact_count = 1
        valid_lead.last_contacted_at = datetime.now(UTC) - timedelta(days=4)
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is True


class TestPersonalEmailDetection:
    """Tests for personal email domain detection."""

    @pytest.mark.parametrize("domain", [
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "aol.com",
        "icloud.com",
        "me.com",
        "protonmail.com",
        "mail.com",
    ])
    def test_personal_domains_rejected(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock, domain: str
    ) -> None:
        """Test all known personal email domains are rejected."""
        valid_lead.email = f"person@{domain}"
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "personal email" in reason.lower()

    def test_business_domain_accepted(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test business email domain is accepted."""
        valid_lead.email = "info@helsekost-bergen.no"
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is True

    def test_invalid_email_format_rejected(
        self, validator: GDPRPreSendValidator, valid_lead: MagicMock
    ) -> None:
        """Test invalid email format is rejected."""
        valid_lead.email = "not-an-email"
        is_valid, reason = validator.validate(valid_lead)
        assert is_valid is False
        assert "invalid" in reason.lower()


class TestConstants:
    """Tests for GDPR constants."""

    def test_max_outreach_emails(self) -> None:
        """Test MAX_OUTREACH_EMAILS is 4."""
        assert MAX_OUTREACH_EMAILS == 4

    def test_min_contact_spacing(self) -> None:
        """Test MIN_CONTACT_SPACING_DAYS is 3."""
        assert MIN_CONTACT_SPACING_DAYS == 3

    def test_personal_domains_count(self) -> None:
        """Test all expected personal domains are listed."""
        assert len(PERSONAL_EMAIL_DOMAINS) == 10
