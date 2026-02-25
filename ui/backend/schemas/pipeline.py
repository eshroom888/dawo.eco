"""Pydantic schemas for Pipeline API.

Story 5-5: Lead Pipeline Status Tracking.
Provides request/response schemas for pipeline dashboard endpoints.

Schemas:
    - PipelineLeadSchema: Lead summary for pipeline view
    - PipelineSummarySchema: Status counts, conversion rate, followup count
    - PipelineLeadListResponse: Paginated lead list
    - LeadHistoryEntrySchema: Single activity record
    - LeadHistoryResponse: List of history entries
    - StatusUpdateRequest: Manual status transition request
    - StatusUpdateResponse: Status update confirmation
    - PipelineMetricsSchema: Conversion funnel, avg time, weekly trend
    - LeadDetailSchema: Full lead detail with relations
    - AddNoteRequest: Add manual note to lead
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PipelineLeadSchema(BaseModel):
    """Lead summary for pipeline view.

    Compact representation of a lead for Kanban board display.
    """

    id: str = Field(..., description="Lead UUID")
    email: str = Field(..., description="Primary email address")
    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    company: str = Field(..., description="Company name")
    job_title: Optional[str] = Field(default=None, description="Role/position")
    status: str = Field(..., description="Pipeline status")
    source: str = Field(..., description="Lead source")
    score: float = Field(..., ge=0, le=100, description="Lead score (0-100)")
    last_contacted_at: Optional[datetime] = Field(
        default=None, description="Last outreach timestamp"
    )
    days_since_contact: Optional[int] = Field(
        default=None, description="Days since last contact"
    )
    needs_followup: bool = Field(
        default=False, description="Whether lead needs follow-up"
    )
    contact_count: int = Field(default=0, description="Number of outreach attempts")
    created_at: datetime = Field(..., description="Record creation time")

    model_config = {"from_attributes": True}


class PipelineSummarySchema(BaseModel):
    """Pipeline dashboard summary.

    Top-level metrics for the pipeline overview.
    """

    total_leads: int = Field(..., ge=0, description="Total leads in pipeline")
    status_counts: dict[str, int] = Field(
        ..., description="Lead count per pipeline status"
    )
    conversion_rate: float = Field(
        ..., ge=0, description="Conversion rate percentage"
    )
    avg_days_in_pipeline: float = Field(
        ..., ge=0, description="Average days leads spend in pipeline"
    )
    followup_count: int = Field(
        ..., ge=0, description="Number of leads needing follow-up"
    )

    model_config = {"from_attributes": True}


class PipelineLeadListResponse(BaseModel):
    """Paginated lead list response.

    Supports offset-based pagination with cursor.
    """

    leads: list[PipelineLeadSchema] = Field(
        ..., description="List of leads for current page"
    )
    total_count: int = Field(..., ge=0, description="Total matching leads")
    has_more: bool = Field(..., description="Whether more leads exist")
    next_cursor: Optional[str] = Field(
        default=None, description="Cursor for next page"
    )

    model_config = {"from_attributes": True}


class LeadHistoryEntrySchema(BaseModel):
    """Single lead activity record.

    Represents one entry in the lead's activity timeline.
    """

    id: str = Field(..., description="Activity UUID")
    lead_id: str = Field(..., description="Lead UUID")
    activity_type: str = Field(..., description="Activity type")
    description: str = Field(..., description="Human-readable description")
    timestamp: datetime = Field(..., description="When activity occurred")
    actor: Optional[str] = Field(default=None, description="Who performed the action")
    metadata: Optional[dict] = Field(
        default=None, description="Additional activity data"
    )

    model_config = {"from_attributes": True}


class LeadHistoryResponse(BaseModel):
    """Lead activity history response.

    Complete activity timeline for a single lead.
    """

    entries: list[LeadHistoryEntrySchema] = Field(
        ..., description="Activity entries ordered by timestamp desc"
    )

    model_config = {"from_attributes": True}


class StatusUpdateRequest(BaseModel):
    """Manual status transition request.

    Used by operators to manually advance or close leads.
    """

    new_status: str = Field(..., description="Target pipeline status")
    reason: Optional[str] = Field(
        default=None, description="Reason for status change"
    )
    note: Optional[str] = Field(
        default=None, description="Optional note about the transition"
    )


class StatusUpdateResponse(BaseModel):
    """Status update confirmation response."""

    success: bool = Field(..., description="Whether update succeeded")
    lead: PipelineLeadSchema = Field(..., description="Updated lead data")
    message: str = Field(..., description="Confirmation message")

    model_config = {"from_attributes": True}


class PipelineMetricsSchema(BaseModel):
    """Conversion funnel and trend metrics.

    Detailed pipeline performance data for metrics panel.
    """

    conversion_rate: float = Field(
        ..., ge=0, description="Conversion rate percentage"
    )
    total_leads: int = Field(..., ge=0, description="Total leads in pipeline")
    converted_count: int = Field(
        ..., ge=0, description="Number of converted leads"
    )
    avg_time_per_stage: dict[str, float] = Field(
        ..., description="Average days per pipeline stage"
    )
    weekly_trend: list[dict] = Field(
        ..., description="Weekly new vs converted counts"
    )

    model_config = {"from_attributes": True}


class LeadDetailSchema(PipelineLeadSchema):
    """Full lead detail with relations.

    Extends PipelineLeadSchema with enrichment data, outreach data,
    activity history, and email records.
    """

    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile")
    website_url: Optional[str] = Field(default=None, description="Company website")
    phone: Optional[str] = Field(default=None, description="Phone number")
    country: Optional[str] = Field(default=None, description="Country/region")
    industry: Optional[str] = Field(default=None, description="Industry vertical")
    company_size: Optional[str] = Field(
        default=None, description="Employee count range"
    )
    enrichment_data: Optional[dict] = Field(
        default=None, description="Enrichment service data"
    )
    outreach_data: Optional[dict] = Field(
        default=None, description="Outreach template data"
    )
    tags: list[str] = Field(default_factory=list, description="Custom tags")
    notes: Optional[str] = Field(default=None, description="Free-form notes")
    assigned_to: Optional[str] = Field(
        default=None, description="Sales rep assignment"
    )
    next_followup_at: Optional[datetime] = Field(
        default=None, description="Scheduled follow-up time"
    )
    converted_at: Optional[datetime] = Field(
        default=None, description="Conversion timestamp"
    )
    lost_reason: Optional[str] = Field(default=None, description="Why lead was lost")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update time"
    )
    activities: list[LeadHistoryEntrySchema] = Field(
        default_factory=list, description="Activity history"
    )
    emails: list[dict] = Field(
        default_factory=list, description="Outreach email records"
    )

    model_config = {"from_attributes": True}


class AddNoteRequest(BaseModel):
    """Add manual note request."""

    note: str = Field(..., min_length=1, description="Note text")


__all__ = [
    "PipelineLeadSchema",
    "PipelineSummarySchema",
    "PipelineLeadListResponse",
    "LeadHistoryEntrySchema",
    "LeadHistoryResponse",
    "StatusUpdateRequest",
    "StatusUpdateResponse",
    "PipelineMetricsSchema",
    "LeadDetailSchema",
    "AddNoteRequest",
]
