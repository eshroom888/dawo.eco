"""B2B Lead database models.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner (created)
Story 5-5: Lead Pipeline Status Tracking (extended)

Defines SQLAlchemy ORM models for B2B lead management.
Uses PostgreSQL-specific features: UUID, JSONB, ARRAY.

Models:
    - Lead: B2B contact for outreach pipeline
    - LeadActivity: Audit trail for lead interactions
    - OutreachEmail: Sent email tracking

Enums:
    - LeadStatus: Pipeline stages (NEW, CONTACTED, REPLIED, etc.)
    - LeadSource: Where lead was discovered
    - EmailStatus: Outreach email states
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, Index, Boolean, Float, func, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base

if TYPE_CHECKING:
    from typing import List


class LeadStatus(str, Enum):
    """Lead pipeline status.

    Values:
        NEW: Just discovered, not yet contacted
        RESEARCHING: Gathering more information
        QUALIFIED: Meets criteria for outreach
        OUTREACH_PENDING: Draft generated, awaiting approval
        CONTACTED: First outreach sent
        REPLIED: Lead responded
        MEETING_SCHEDULED: Call/meeting booked
        NEGOTIATING: In active discussion
        CONVERTED: Became customer
        LOST: Declined or unresponsive
        NURTURE: Long-term follow-up
    """

    NEW = "new"
    RESEARCHING = "researching"
    QUALIFIED = "qualified"
    OUTREACH_PENDING = "outreach_pending"
    CONTACTED = "contacted"
    REPLIED = "replied"
    MEETING_SCHEDULED = "meeting_scheduled"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    LOST = "lost"
    NURTURE = "nurture"


class LeadSource(str, Enum):
    """Lead discovery source.

    Values:
        LINKEDIN: Found via LinkedIn
        WEBSITE: Visited our website
        REFERRAL: Referred by existing contact
        EVENT: Met at conference/event
        COLD_RESEARCH: Proactive research
        INBOUND: Contacted us first
        PARTNER: Via partner channel
    """

    LINKEDIN = "linkedin"
    WEBSITE = "website"
    REFERRAL = "referral"
    EVENT = "event"
    COLD_RESEARCH = "cold_research"
    INBOUND = "inbound"
    PARTNER = "partner"


class EmailStatus(str, Enum):
    """Outreach email status.

    Values:
        DRAFT: Not yet sent
        SCHEDULED: Queued for sending
        SENT: Successfully sent
        DELIVERED: Confirmed delivered
        OPENED: Email was opened
        CLICKED: Link was clicked
        REPLIED: Received reply
        BOUNCED: Delivery failed
        UNSUBSCRIBED: Opted out
    """

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class ActivityType(str, Enum):
    """Lead activity types for audit trail.

    Values:
        CREATED: Lead record created
        STATUS_CHANGE: Pipeline status updated
        EMAIL_SENT: Outreach email sent
        EMAIL_OPENED: Email was opened
        EMAIL_REPLIED: Received reply
        NOTE_ADDED: Manual note added
        ENRICHED: Data enriched from external source
        SCORE_UPDATED: Lead score recalculated
        MEETING: Meeting/call occurred
    """

    CREATED = "created"
    STATUS_CHANGE = "status_change"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_REPLIED = "email_replied"
    NOTE_ADDED = "note_added"
    ENRICHED = "enriched"
    SCORE_UPDATED = "score_updated"
    MEETING = "meeting"


# Model constants
MAX_EMAIL_LENGTH = 255
MAX_NAME_LENGTH = 100
MAX_COMPANY_LENGTH = 200
MAX_TITLE_LENGTH = 200
MAX_URL_LENGTH = 500
MAX_PHONE_LENGTH = 50
MAX_COUNTRY_LENGTH = 100


class Lead(Base):
    """B2B Lead for outreach pipeline.

    Epic 5, Story 5-5: Lead Pipeline Status Tracking.

    Attributes:
        id: Unique identifier (UUID)
        email: Primary email address
        first_name: Contact first name
        last_name: Contact last name
        company: Company name
        job_title: Role/position
        linkedin_url: LinkedIn profile URL
        website_url: Company website
        phone: Phone number (optional)
        country: Country/region
        industry: Industry vertical
        company_size: Employee count range
        status: Pipeline status
        source: How lead was discovered
        score: Lead score (0-100)
        score_breakdown: Scoring factors (JSONB)
        enrichment_data: Data from enrichment services (JSONB)
        enriched_at: When enrichment occurred
        tags: Custom tags for filtering
        notes: Free-form notes
        assigned_to: Sales rep assignment
        last_contacted_at: Last outreach timestamp
        last_replied_at: Last reply timestamp
        contact_count: Number of outreach attempts
        next_followup_at: Scheduled follow-up
        converted_at: When converted to customer
        lost_reason: Why lead was lost
        created_at: Record creation time
        updated_at: Last update time
    """

    __tablename__ = "leads"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Contact information
    email: Mapped[str] = mapped_column(
        String(MAX_EMAIL_LENGTH),
        nullable=False,
        unique=True,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(MAX_NAME_LENGTH),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(MAX_NAME_LENGTH),
        nullable=False,
    )

    company: Mapped[str] = mapped_column(
        String(MAX_COMPANY_LENGTH),
        nullable=False,
        index=True,
    )

    job_title: Mapped[Optional[str]] = mapped_column(
        String(MAX_TITLE_LENGTH),
        nullable=True,
    )

    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=True,
    )

    website_url: Mapped[Optional[str]] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=True,
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(MAX_PHONE_LENGTH),
        nullable=True,
    )

    country: Mapped[Optional[str]] = mapped_column(
        String(MAX_COUNTRY_LENGTH),
        nullable=True,
    )

    industry: Mapped[Optional[str]] = mapped_column(
        String(MAX_COMPANY_LENGTH),
        nullable=True,
    )

    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),  # e.g., "11-50", "51-200"
        nullable=True,
    )

    # Pipeline tracking
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=LeadStatus.NEW.value,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=LeadSource.COLD_RESEARCH.value,
    )

    # Lead scoring
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True,
    )

    score_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Enrichment data
    enrichment_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    enriched_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    # Outreach data (Story 5-3)
    outreach_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    outreach_generated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    # Organization
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        server_default="{}",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(MAX_EMAIL_LENGTH),
        nullable=True,
    )

    # Activity tracking
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    last_replied_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    contact_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    next_followup_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    # Outcome tracking
    converted_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        default=None,
    )

    lost_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    activities: Mapped["List[LeadActivity]"] = relationship(
        "LeadActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="LeadActivity.created_at.desc()",
    )

    emails: Mapped["List[OutreachEmail]"] = relationship(
        "OutreachEmail",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="OutreachEmail.created_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("idx_leads_pipeline", status, score.desc()),
        Index("idx_leads_followup", next_followup_at),
        Index("idx_leads_company_search", company),
    )

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, email={self.email}, company={self.company}, status={self.status})>"


class LeadActivity(Base):
    """Audit trail for lead interactions.

    Epic 5, Story 5-5: Activity tracking for leads.

    Attributes:
        id: Unique identifier
        lead_id: Foreign key to Lead
        activity_type: Type of activity
        description: Human-readable description
        metadata: Additional data (JSONB)
        created_by: Who performed the action
        created_at: When activity occurred
    """

    __tablename__ = "lead_activities"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    activity_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    activity_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",  # Keep DB column name as "metadata"
        JSONB,
        nullable=True,
        default=None,
    )

    created_by: Mapped[Optional[str]] = mapped_column(
        String(MAX_EMAIL_LENGTH),
        nullable=True,
        default="system",
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationship
    lead: Mapped["Lead"] = relationship(
        "Lead",
        back_populates="activities",
    )

    def __repr__(self) -> str:
        return f"<LeadActivity(id={self.id}, type={self.activity_type}, lead={self.lead_id})>"


class OutreachEmail(Base):
    """Outreach email tracking.

    Epic 5, Story 5-4: Gmail API Integration tracking.

    Attributes:
        id: Unique identifier
        lead_id: Foreign key to Lead
        subject: Email subject line
        body: Email body (HTML or plain)
        template_id: Template used (if any)
        status: Email status
        gmail_message_id: Gmail API message ID
        gmail_thread_id: Gmail thread ID
        sent_at: When email was sent
        delivered_at: Delivery confirmation time
        opened_at: First open time
        clicked_at: First click time
        replied_at: Reply received time
        bounce_reason: Why email bounced
        created_at: Record creation time
    """

    __tablename__ = "outreach_emails"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    template_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EmailStatus.DRAFT.value,
        index=True,
    )

    # Gmail tracking
    gmail_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    gmail_thread_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Timing tracking
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    opened_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    clicked_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    replied_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    bounce_reason: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationship
    lead: Mapped["Lead"] = relationship(
        "Lead",
        back_populates="emails",
    )

    def __repr__(self) -> str:
        return f"<OutreachEmail(id={self.id}, lead={self.lead_id}, status={self.status})>"


__all__ = [
    "Lead",
    "LeadActivity",
    "OutreachEmail",
    "LeadStatus",
    "LeadSource",
    "EmailStatus",
    "ActivityType",
]
