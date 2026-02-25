"""Pipeline service for lead pipeline status tracking.

Story 5-5, Task 3: Business logic for pipeline dashboard,
status transitions, follow-up detection, and metrics.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from core.leads.models import Lead, LeadActivity, LeadStatus, ActivityType

if TYPE_CHECKING:
    from teams.dawo.leads.repository import LeadRepository
from teams.dawo.leads.pipeline.schemas import (
    PipelineSummary,
    ConversionMetrics,
    FollowUpCandidate,
)

logger = logging.getLogger(__name__)


# Valid manual status transitions (Story 5-5 Dev Notes)
VALID_MANUAL_TRANSITIONS: dict[str, set[str]] = {
    LeadStatus.NEW.value: {LeadStatus.RESEARCHING.value, LeadStatus.LOST.value},
    LeadStatus.RESEARCHING.value: {LeadStatus.QUALIFIED.value, LeadStatus.LOST.value},
    LeadStatus.QUALIFIED.value: {
        LeadStatus.OUTREACH_PENDING.value,
        LeadStatus.LOST.value,
        LeadStatus.NURTURE.value,
    },
    LeadStatus.OUTREACH_PENDING.value: {
        LeadStatus.CONTACTED.value,
        LeadStatus.LOST.value,
    },
    LeadStatus.CONTACTED.value: {
        LeadStatus.REPLIED.value,
        LeadStatus.LOST.value,
        LeadStatus.NURTURE.value,
    },
    LeadStatus.REPLIED.value: {
        LeadStatus.MEETING_SCHEDULED.value,
        LeadStatus.NEGOTIATING.value,
        LeadStatus.CONVERTED.value,
        LeadStatus.LOST.value,
        LeadStatus.NURTURE.value,
    },
    LeadStatus.MEETING_SCHEDULED.value: {
        LeadStatus.NEGOTIATING.value,
        LeadStatus.CONVERTED.value,
        LeadStatus.LOST.value,
    },
    LeadStatus.NEGOTIATING.value: {
        LeadStatus.CONVERTED.value,
        LeadStatus.LOST.value,
    },
    LeadStatus.NURTURE.value: {
        LeadStatus.CONTACTED.value,
        LeadStatus.LOST.value,
    },
    # Terminal states
    LeadStatus.CONVERTED.value: set(),
    LeadStatus.LOST.value: {LeadStatus.NURTURE.value},
}


class PipelineService:
    """Service for lead pipeline operations.

    Orchestrates repository calls to provide pipeline dashboard data,
    status transitions, follow-up detection, and metrics.

    Accepts LeadRepository via dependency injection.
    """

    def __init__(self, repository: "LeadRepository") -> None:
        """Initialize PipelineService.

        Args:
            repository: LeadRepository instance
        """
        self._repo = repository

    async def get_dashboard_summary(self) -> PipelineSummary:
        """Get pipeline dashboard summary.

        Aggregates status counts, follow-up count, and conversion rate.

        Returns:
            PipelineSummary with all dashboard metrics
        """
        status_counts = await self._repo.get_pipeline_summary()
        followup_leads = await self._repo.get_followup_candidates()
        metrics = await self._repo.get_conversion_metrics()

        total = sum(status_counts.values())

        return PipelineSummary(
            total_leads=total,
            status_counts=status_counts,
            conversion_rate=metrics["conversion_rate"],
            avg_days_in_pipeline=0.0,  # Calculated separately in metrics
            followup_count=len(followup_leads),
        )

    async def get_metrics(self) -> ConversionMetrics:
        """Get detailed pipeline metrics.

        Returns:
            ConversionMetrics with funnel, timing, and trend data
        """
        metrics = await self._repo.get_conversion_metrics()
        avg_time = await self._repo.get_avg_time_per_stage()
        trend = await self._repo.get_weekly_trend(weeks=8)

        return ConversionMetrics(
            conversion_rate=metrics["conversion_rate"],
            total_leads=metrics["total_leads"],
            converted_count=metrics["converted_count"],
            avg_time_per_stage=avg_time,
            weekly_trend=trend,
        )

    async def update_lead_status(
        self,
        lead_id: UUID,
        new_status: LeadStatus,
        reason: Optional[str] = None,
        actor: str = "system",
    ) -> Lead:
        """Manually update lead pipeline status.

        Validates transition, updates timestamps, and logs activity.

        Args:
            lead_id: Lead UUID
            new_status: Target status
            reason: Optional reason for transition
            actor: Who initiated the change

        Returns:
            Updated Lead

        Raises:
            ValueError: If lead not found or transition invalid
        """
        lead = await self._repo.get_lead_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")

        current_status = lead.status
        allowed = VALID_MANUAL_TRANSITIONS.get(current_status, set())

        if new_status.value not in allowed:
            raise ValueError(
                f"Invalid transition from {current_status} to {new_status.value}. "
                f"Allowed: {allowed}"
            )

        # Update status and timestamp directly on the lead object
        lead.status = new_status.value
        lead.updated_at = datetime.now(UTC)

        # Set status-specific fields
        if new_status == LeadStatus.CONVERTED:
            lead.converted_at = datetime.now(UTC)
        elif new_status == LeadStatus.LOST:
            lead.lost_reason = reason
        elif new_status == LeadStatus.REPLIED:
            lead.last_replied_at = datetime.now(UTC)
        elif new_status == LeadStatus.CONTACTED:
            lead.next_followup_at = datetime.now(UTC) + timedelta(days=7)

        # Log activity once (commit flushes lead changes too)
        await self._repo.add_activity(
            lead_id=lead_id,
            activity_type=ActivityType.STATUS_CHANGE,
            description=f"Manual status change: {current_status} -> {new_status.value}",
            metadata={
                "old_status": current_status,
                "new_status": new_status.value,
                "reason": reason,
                "actor": actor,
                "source": "pipeline_dashboard",
            },
        )

        # Re-fetch to get clean state after commit
        result = await self._repo.get_lead_by_id(lead_id)

        logger.info(f"Lead {lead_id} status: {current_status} -> {new_status.value} by {actor}")
        return result

    async def add_note(
        self,
        lead_id: UUID,
        note_text: str,
        actor: str = "system",
    ) -> LeadActivity:
        """Add a manual note to a lead.

        Args:
            lead_id: Lead UUID
            note_text: Note content
            actor: Who added the note

        Returns:
            Created LeadActivity

        Raises:
            ValueError: If lead not found
        """
        lead = await self._repo.get_lead_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")

        activity = await self._repo.add_activity(
            lead_id=lead_id,
            activity_type=ActivityType.NOTE_ADDED,
            description=note_text,
            metadata={"actor": actor, "source": "pipeline_dashboard"},
        )

        logger.info(f"Note added to lead {lead_id} by {actor}")
        return activity

    async def detect_followups(
        self,
        days_threshold: int = 7,
    ) -> list[FollowUpCandidate]:
        """Detect leads needing follow-up.

        Args:
            days_threshold: Days without response before flagging

        Returns:
            List of FollowUpCandidate records
        """
        leads = await self._repo.get_followup_candidates(days_threshold)

        now = datetime.now(UTC)
        return [
            FollowUpCandidate(
                lead_id=lead.id,
                email=lead.email,
                company=lead.company,
                days_since_contact=(
                    (now - lead.last_contacted_at).days
                    if lead.last_contacted_at else 0
                ),
                last_contacted_at=lead.last_contacted_at,
            )
            for lead in leads
        ]


__all__ = [
    "PipelineService",
    "VALID_MANUAL_TRANSITIONS",
]
