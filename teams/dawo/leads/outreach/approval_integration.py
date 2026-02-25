"""Outreach Approval Queue Integration.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Provides integration with the approval queue for outreach drafts:
- OutreachApprovalIntegration: Submit drafts to approval queue

Acceptance Criteria #3:
- Shows lead summary, personalization used, suggested send time
- Operator can edit before approving
- Status changes to OUTREACH_PENDING
"""

import logging
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from teams.dawo.leads.outreach.schemas import OutreachDraft


logger = logging.getLogger(__name__)


class OutreachApprovalIntegration:
    """Integration for submitting outreach drafts to approval queue.

    Provides methods to create approval queue items from outreach drafts
    with all necessary display data for operator review.

    Approval items include:
    - Lead summary (company, contact, location)
    - Personalization hooks used
    - Template type selected
    - Suggested send time (business hours)
    """

    async def submit_to_queue(self, draft: OutreachDraft, lead: Any) -> dict:
        """Submit outreach draft to approval queue.

        Creates an approval queue item with all necessary data
        for operator review and editing.

        Args:
            draft: Generated outreach draft
            lead: Lead object for summary data

        Returns:
            Dict containing approval item data
        """
        display_data = self.get_display_data(draft, lead)

        approval_item = {
            "id": str(uuid4()),
            "source_type": "b2b_outreach",
            "content_type": "email",
            "title": f"Outreach: {lead.company}",
            "preview": draft.subject,
            "full_content": draft.body,
            "metadata": {
                "lead_id": str(lead.id),
                "company": lead.company,
                "contact_name": f"{lead.first_name} {lead.last_name}",
                "contact_email": lead.email,
                "template_id": draft.template_id,
                "template_type": draft.template_type.value,
                "personalization_hooks": draft.personalization_hooks,
                "suggested_send_time": (
                    draft.suggested_send_time.isoformat()
                    if draft.suggested_send_time
                    else None
                ),
            },
            "quality_score": draft.personalization_score,
            "compliance_status": "COMPLIANT",  # B2B outreach doesn't need EU health claims check
            "display_data": display_data,
            "created_at": datetime.now(UTC).isoformat(),
        }

        logger.info(
            "Submitted outreach draft to approval queue",
            extra={
                "lead_id": str(lead.id),
                "template_id": draft.template_id,
            }
        )

        return approval_item

    def get_display_data(self, draft: OutreachDraft, lead: Any) -> dict:
        """Get display data for approval UI.

        Creates a structured dict with all information needed
        for the operator to review the outreach draft.

        Args:
            draft: Generated outreach draft
            lead: Lead object for summary data

        Returns:
            Dict containing display data for approval UI
        """
        return {
            "lead_summary": {
                "lead_id": str(lead.id),
                "company": lead.company,
                "contact_name": f"{lead.first_name} {lead.last_name}",
                "email": lead.email,
                "country": getattr(lead, "country", None),
                "industry": getattr(lead, "industry", None),
                "website": getattr(lead, "website_url", None),
            },
            "personalization_hooks": draft.personalization_hooks,
            "personalization_score": draft.personalization_score,
            "template_type": draft.template_type.value,
            "template_id": draft.template_id,
            "suggested_send_time": (
                draft.suggested_send_time.isoformat()
                if draft.suggested_send_time
                else None
            ),
            "draft": {
                "subject": draft.subject,
                "body": draft.body,
                "word_count": draft.word_count,
            },
        }
