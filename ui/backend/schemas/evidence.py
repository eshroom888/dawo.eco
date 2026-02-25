"""Pydantic schemas for Evidence API.

Story 6-9: Searchable Evidence Database.
Provides response schemas for evidence search, detail, and summary endpoints.

Schemas:
    - EvidenceListItemSchema: Evidence summary for list view
    - EvidenceDetailSchema: Full evidence detail with relations
    - EvidenceListResponse: Paginated evidence list
    - EvidenceSummarySchema: Aggregate counts by severity, competitor, violation_type
    - CompetitorTimelineEntry: Monthly violation count for trend chart
    - AuditLogEntrySchema: Single audit log record
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceListItemSchema(BaseModel):
    """Evidence summary for list view.

    Compact representation for evidence grid display.
    """

    id: str = Field(..., description="Evidence UUID")
    competitor_name: str = Field(..., description="Competitor name")
    violation_type: str = Field(..., description="Violation type descriptor")
    severity: str = Field(..., description="Severity level (high/medium/low)")
    claim_text: str = Field(..., description="Claim text (may be truncated)")
    claim_category: str = Field(..., description="Claim category")
    source_type: str = Field(..., description="Source type (instagram_post/website_page)")
    source_url: str = Field(..., description="Original source URL")
    captured_at: datetime = Field(..., description="When screenshot was captured")
    screenshot_path: str = Field(..., description="Relative path to screenshot")
    screenshot_hash: str = Field(..., description="SHA-256 hash of screenshot")

    model_config = {"from_attributes": True}


class AuditLogEntrySchema(BaseModel):
    """Single audit log record."""

    id: str = Field(..., description="Audit log UUID")
    action: str = Field(..., description="Operation type")
    actor: str = Field(..., description="Who performed the action")
    details: Optional[dict] = Field(default=None, description="Operation-specific data")
    hash_verified: Optional[bool] = Field(
        default=None, description="Integrity check result"
    )
    created_at: datetime = Field(..., description="When action occurred")

    model_config = {"from_attributes": True}


class EvidenceDetailSchema(BaseModel):
    """Full evidence detail with violation and audit log relations.

    Displayed in the evidence detail drawer/panel.
    """

    id: str = Field(..., description="Evidence UUID")
    competitor_name: str = Field(..., description="Competitor name")
    violation_type: str = Field(..., description="Violation type descriptor")
    severity: str = Field(..., description="Severity level")
    claim_text: str = Field(..., description="Full claim text")
    claim_category: str = Field(..., description="Claim category")
    source_type: str = Field(..., description="Source type")
    source_url: str = Field(..., description="Original source URL")
    captured_at: datetime = Field(..., description="Screenshot capture time")
    screenshot_path: str = Field(..., description="Relative path to screenshot")
    screenshot_hash: str = Field(..., description="SHA-256 hash")
    screenshot_size_bytes: int = Field(..., description="File size in bytes")
    regulation_violated: Optional[str] = Field(
        default=None, description="EU regulation reference"
    )
    detection_reasoning: Optional[str] = Field(
        default=None, description="Classification reasoning"
    )
    confidence: float = Field(..., description="Confidence score 0.0-1.0")
    evidence_metadata: Optional[dict] = Field(
        default=None, description="Additional metadata"
    )
    created_at: datetime = Field(..., description="Record creation time")
    audit_logs: list[AuditLogEntrySchema] = Field(
        default_factory=list, description="Audit log timeline"
    )

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    """Paginated evidence list."""

    items: list[EvidenceListItemSchema] = Field(
        ..., description="Evidence items for current page"
    )
    total_count: int = Field(..., ge=0, description="Total matching evidence")
    has_more: bool = Field(..., description="Whether more results exist")

    model_config = {"from_attributes": True}


class EvidenceSummarySchema(BaseModel):
    """Aggregate evidence statistics.

    Dashboard overview counts.
    """

    total_evidence: int = Field(..., ge=0, description="Total evidence records")
    by_severity: dict[str, int] = Field(
        ..., description="Evidence count per severity level"
    )
    by_competitor: dict[str, int] = Field(
        ..., description="Evidence count per competitor"
    )
    by_violation_type: dict[str, int] = Field(
        ..., description="Evidence count per violation type"
    )

    model_config = {"from_attributes": True}


class CompetitorTimelineEntry(BaseModel):
    """Monthly violation count for competitor trend chart."""

    month: str = Field(..., description="Month in YYYY-MM format")
    count: int = Field(..., ge=0, description="Violation count for this month")

    model_config = {"from_attributes": True}


__all__ = [
    "AuditLogEntrySchema",
    "CompetitorTimelineEntry",
    "EvidenceDetailSchema",
    "EvidenceListItemSchema",
    "EvidenceListResponse",
    "EvidenceSummarySchema",
]
