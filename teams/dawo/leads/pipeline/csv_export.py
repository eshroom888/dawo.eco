"""CSV export service for lead pipeline.

Story 5-5, Task 4: Generates CSV files for lead data export
with support for status and date range filtering.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from core.leads.models import LeadStatus

if TYPE_CHECKING:
    from teams.dawo.leads.repository import LeadRepository

logger = logging.getLogger(__name__)


# Export column definitions
LEAD_CSV_COLUMNS = [
    "id", "email", "first_name", "last_name", "company",
    "job_title", "status", "source", "score", "country",
    "industry", "created_at", "last_contacted_at",
    "contact_count", "converted_at", "lost_reason",
]

HISTORY_CSV_COLUMNS = [
    "id", "activity_type", "description", "created_at",
    "created_by", "metadata",
]


class CSVExporter:
    """CSV export service for lead data.

    Generates in-memory CSV strings for lead lists and history.
    Accepts LeadRepository via dependency injection.
    """

    def __init__(self, repository: "LeadRepository") -> None:
        """Initialize CSVExporter.

        Args:
            repository: LeadRepository instance
        """
        self._repo = repository

    async def export_leads(
        self,
        status_filter: Optional[LeadStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Export leads to CSV string.

        Args:
            status_filter: Optional status filter
            date_from: Optional start date filter
            date_to: Optional end date filter

        Returns:
            CSV string with headers and lead data
        """
        leads, _ = await self._repo.get_leads_filtered(
            status=status_filter,
            date_from=date_from,
            date_to=date_to,
            limit=10000,  # Export all matching
            offset=0,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(LEAD_CSV_COLUMNS)

        for lead in leads:
            writer.writerow([
                str(lead.id),
                lead.email,
                lead.first_name,
                lead.last_name,
                lead.company,
                lead.job_title or "",
                lead.status,
                lead.source,
                lead.score,
                lead.country or "",
                lead.industry or "",
                str(lead.created_at) if lead.created_at else "",
                str(lead.last_contacted_at) if lead.last_contacted_at else "",
                lead.contact_count,
                str(lead.converted_at) if lead.converted_at else "",
                lead.lost_reason or "",
            ])

        csv_content = output.getvalue()
        logger.info(f"Exported {len(leads)} leads to CSV")
        return csv_content

    async def export_lead_history(self, lead_id: UUID) -> str:
        """Export single lead's activity history to CSV.

        Args:
            lead_id: Lead UUID

        Returns:
            CSV string with activity history
        """
        activities = await self._repo.get_lead_activities(lead_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(HISTORY_CSV_COLUMNS)

        for activity in activities:
            metadata_str = ""
            if activity.activity_metadata:
                metadata_str = str(activity.activity_metadata)

            writer.writerow([
                str(activity.id),
                activity.activity_type,
                activity.description,
                str(activity.created_at) if activity.created_at else "",
                activity.created_by or "",
                metadata_str,
            ])

        csv_content = output.getvalue()
        logger.info(f"Exported {len(activities)} activities for lead {lead_id}")
        return csv_content


__all__ = [
    "CSVExporter",
    "LEAD_CSV_COLUMNS",
    "HISTORY_CSV_COLUMNS",
]
