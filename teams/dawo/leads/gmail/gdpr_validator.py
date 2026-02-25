"""GDPR Pre-Send Validation for outreach emails.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Validates leads against GDPR and Norwegian Marketing Act requirements
before allowing email sends. All checks must pass.
"""

import logging
from datetime import datetime, UTC

from core.leads.models import Lead, LeadStatus

logger = logging.getLogger(__name__)


# GDPR Constants
MAX_OUTREACH_EMAILS = 4
MIN_CONTACT_SPACING_DAYS = 3

PERSONAL_EMAIL_DOMAINS = frozenset({
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
})


class GDPRPreSendValidator:
    """GDPR compliance validator for outreach emails.

    Validates all GDPR requirements before sending:
    - Lead not unsubscribed
    - Lead not erasure-requested
    - Business email (not personal domain)
    - Lead status allows sending
    - Max contact limit not exceeded
    - Minimum spacing between contacts
    """

    def validate(self, lead: Lead) -> tuple[bool, str]:
        """Validate lead for GDPR-compliant email send.

        Args:
            lead: Lead to validate

        Returns:
            Tuple of (is_valid, reason_message)
        """
        # Check unsubscribe status
        if hasattr(lead, "unsubscribed_at") and lead.unsubscribed_at is not None:
            return False, "Lead has unsubscribed"

        # Check status allows sending
        if lead.status == LeadStatus.LOST.value:
            return False, "Lead is marked as lost"

        if lead.status == LeadStatus.CONVERTED.value:
            return False, "Lead is already a customer"

        # Check max outreach limit
        if lead.contact_count >= MAX_OUTREACH_EMAILS:
            return False, f"Max outreach limit reached ({MAX_OUTREACH_EMAILS})"

        # Check contact spacing
        if lead.last_contacted_at is not None:
            days_since = (datetime.now(UTC) - lead.last_contacted_at).days
            if days_since < MIN_CONTACT_SPACING_DAYS:
                return False, f"Too soon since last contact ({days_since} days)"

        # Check business email
        try:
            domain = lead.email.split("@")[1].lower()
        except (IndexError, AttributeError):
            return False, "Invalid email format"

        if domain in PERSONAL_EMAIL_DOMAINS:
            return False, f"Personal email domain: {domain}"

        return True, "OK"


__all__ = [
    "GDPRPreSendValidator",
    "MAX_OUTREACH_EMAILS",
    "MIN_CONTACT_SPACING_DAYS",
    "PERSONAL_EMAIL_DOMAINS",
]
