"""B2B Leads Module.

Epic 5: B2B Sales Pipeline

Provides models and services for B2B lead management,
outreach tracking, and pipeline status.

Exports:
    Models:
        - Lead: B2B contact for outreach
        - LeadActivity: Activity audit trail
        - OutreachEmail: Sent email tracking

    Enums:
        - LeadStatus: Pipeline stages
        - LeadSource: Lead discovery sources
        - EmailStatus: Outreach email states
        - ActivityType: Activity types
"""

from core.leads.models import (
    Lead,
    LeadActivity,
    OutreachEmail,
    LeadStatus,
    LeadSource,
    EmailStatus,
    ActivityType,
)

__all__ = [
    "Lead",
    "LeadActivity",
    "OutreachEmail",
    "LeadStatus",
    "LeadSource",
    "EmailStatus",
    "ActivityType",
]
