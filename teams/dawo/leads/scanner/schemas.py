"""Data schemas for B2B Lead Research Scanner.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner

Defines data structures for the lead discovery pipeline:
- RawLead: Initial lead from search
- HarvestedLead: Enriched lead from Hunter.io
- TransformedLead: Lead ready for database insertion
- ScanResult: Scanner stage output
- PipelineResult: Full pipeline output
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from uuid import UUID


class PipelineStatus(str, Enum):
    """Pipeline execution status.

    Values:
        COMPLETE: All stages completed successfully
        PARTIAL: Some leads failed but pipeline continued
        INCOMPLETE: API failure, queued for retry
        FAILED: Critical error, requires manual intervention
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


@dataclass
class RawLead:
    """Raw lead data from initial search.

    Represents a potential lead discovered during scanning.
    Minimal data before enrichment.
    """

    domain: str
    company_name: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = 0.0
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Normalize domain on creation."""
        if self.domain:
            # Remove protocol and www prefix
            domain = self.domain.lower().strip()
            for prefix in ["https://", "http://", "www."]:
                if domain.startswith(prefix):
                    domain = domain[len(prefix):]
            # Remove trailing slash
            self.domain = domain.rstrip("/")


@dataclass
class HarvestedContact:
    """Contact information from Hunter.io.

    Represents a single contact at a company.
    """

    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    linkedin: Optional[str] = None
    phone: Optional[str] = None
    confidence: float = 0.0


@dataclass
class HarvestedLead:
    """Lead enriched with Hunter.io data.

    Contains full company information and contacts.
    """

    domain: str
    company_name: str
    contacts: list[HarvestedContact] = field(default_factory=list)

    # Company info
    organization: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    phone: Optional[str] = None
    headcount: Optional[str] = None
    industry: Optional[str] = None

    # Discovery metadata
    source_url: Optional[str] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    enriched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def primary_contact(self) -> Optional[HarvestedContact]:
        """Get the best contact (highest confidence)."""
        if not self.contacts:
            return None
        return max(self.contacts, key=lambda c: c.confidence)


@dataclass
class TransformedLead:
    """Lead ready for database insertion.

    Mapped to the Lead model schema.
    """

    email: str
    first_name: str
    last_name: str
    company: str
    job_title: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    source: str = "cold_research"
    status: str = "new"
    score: float = 0.0

    # Enrichment metadata stored in JSONB
    enrichment_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company": self.company,
            "job_title": self.job_title,
            "website_url": self.website_url,
            "linkedin_url": self.linkedin_url,
            "phone": self.phone,
            "country": self.country,
            "industry": self.industry,
            "company_size": self.company_size,
            "source": self.source,
            "status": self.status,
            "score": self.score,
            "enrichment_data": self.enrichment_data,
        }


@dataclass
class ScanStatistics:
    """Statistics from a scan operation."""

    domains_searched: int = 0
    raw_leads_found: int = 0
    leads_harvested: int = 0
    leads_transformed: int = 0
    duplicates_found: int = 0
    leads_created: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "domains_searched": self.domains_searched,
            "raw_leads_found": self.raw_leads_found,
            "leads_harvested": self.leads_harvested,
            "leads_transformed": self.leads_transformed,
            "duplicates_found": self.duplicates_found,
            "leads_created": self.leads_created,
            "errors": self.errors,
        }


@dataclass
class ScanResult:
    """Result from the scanner stage."""

    leads: list[RawLead]
    domains_searched: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result from the full lead discovery pipeline."""

    status: PipelineStatus
    stats: ScanStatistics = field(default_factory=ScanStatistics)
    created_lead_ids: list[UUID] = field(default_factory=list)
    error: Optional[str] = None
    retry_scheduled: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Set completion time if not provided."""
        if self.completed_at is None and self.status != PipelineStatus.INCOMPLETE:
            self.completed_at = datetime.now(UTC)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate pipeline duration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "status": self.status.value,
            "stats": self.stats.to_dict(),
            "created_lead_ids": [str(id) for id in self.created_lead_ids],
            "error": self.error,
            "retry_scheduled": self.retry_scheduled,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }
