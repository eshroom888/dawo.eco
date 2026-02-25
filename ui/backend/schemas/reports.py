"""Pydantic schemas for Reports API.

Story 6-10: On-Demand Violation Reports.
Provides request/response schemas for report generation, listing, and download.

Schemas:
    - ReportGenerateRequest: Report generation parameters
    - ReportGenerateResponse: Generated report metadata
    - ReportListItemSchema: Report listing entry
    - ReportListResponse: Paginated report list
    - AvailableTemplatesResponse: Available template types
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Request body for generating a violation report."""

    evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence UUIDs to include (optional)"
    )
    competitor_name: Optional[str] = Field(
        default=None, description="Filter by competitor name"
    )
    date_from: Optional[str] = Field(
        default=None, description="Start date ISO format (optional)"
    )
    date_to: Optional[str] = Field(
        default=None, description="End date ISO format (optional)"
    )
    template_type: str = Field(
        default="standard", description="Report template variant"
    )
    report_title: Optional[str] = Field(
        default=None, description="Custom report title (optional)"
    )


class ReportGenerateResponse(BaseModel):
    """Response after report generation."""

    report_id: str = Field(..., description="Generated report UUID")
    filename: str = Field(..., description="Suggested filename")
    evidence_count: int = Field(..., ge=0, description="Evidence records included")
    page_count: int = Field(..., ge=1, description="PDF page count")
    generated_at: datetime = Field(..., description="Generation timestamp")
    sha256_hash: str = Field(..., description="SHA-256 hash of PDF content")
    download_url: str = Field(..., description="URL to download report")


class ReportListItemSchema(BaseModel):
    """Report listing entry."""

    report_id: str = Field(..., description="Report UUID")
    filename: str = Field(..., description="Report filename")
    evidence_count: int = Field(..., ge=0, description="Evidence records included")
    competitor_name: Optional[str] = Field(
        default=None, description="Competitor filter used"
    )
    template_type: str = Field(..., description="Template variant used")
    generated_at: datetime = Field(..., description="Generation timestamp")
    sha256_hash: str = Field(..., description="SHA-256 hash of PDF content")
    page_count: int = Field(..., ge=0, description="PDF page count")
    file_size_bytes: int = Field(..., ge=0, description="File size on disk")

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """Paginated report list."""

    items: list[ReportListItemSchema] = Field(
        ..., description="Report items for current page"
    )
    total_count: int = Field(..., ge=0, description="Total reports available")
    has_more: bool = Field(..., description="Whether more results exist")


class AvailableTemplatesResponse(BaseModel):
    """Available report template types."""

    templates: list[str] = Field(..., description="List of template type names")


__all__ = [
    "AvailableTemplatesResponse",
    "ReportGenerateRequest",
    "ReportGenerateResponse",
    "ReportListItemSchema",
    "ReportListResponse",
]
