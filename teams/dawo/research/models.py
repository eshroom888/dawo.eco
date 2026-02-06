"""Research Pool database models.

Defines the SQLAlchemy ORM models for research data storage.
Uses PostgreSQL-specific features: ARRAY, JSONB, TSVECTOR for full-text search.

Models:
    - ResearchItem: Main research data entity with all required fields

Enums:
    - ResearchSource: Valid research source types
    - ComplianceStatus: EU compliance check status values

Database Schema (PostgreSQL):
    - research_items table with performance indexes
    - GIN indexes for tags and full-text search
    - B-tree indexes for source, score, created_at, compliance_status
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base


class ResearchSource(str, Enum):
    """Valid research sources - matches scanner types.

    Each source corresponds to a specific scanner agent in the
    Harvester Framework pipeline.

    Values:
        REDDIT: Reddit posts and comments
        YOUTUBE: YouTube video transcripts
        INSTAGRAM: Instagram posts (competitor analysis)
        NEWS: Industry news articles
        PUBMED: Scientific research papers
    """

    REDDIT = "reddit"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    NEWS = "news"
    PUBMED = "pubmed"


class ComplianceStatus(str, Enum):
    """EU compliance check result status.

    Indicates the result of EU Health Claims Regulation (EC 1924/2006)
    validation performed on research content.

    Values:
        COMPLIANT: Content passes compliance checks
        WARNING: Borderline content, needs review
        REJECTED: Content contains prohibited claims
    """

    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    REJECTED = "REJECTED"


# Constants for model configuration
DEFAULT_SCORE = 0.0
MAX_SCORE = 10.0
MIN_SCORE = 0.0
DEFAULT_LIMIT = 50
MAX_TITLE_LENGTH = 500
MAX_URL_LENGTH = 2048
MAX_TAG_LENGTH = 100
MAX_SOURCE_LENGTH = 20
MAX_COMPLIANCE_LENGTH = 20


class ResearchItem(Base):
    """Research Pool item - foundation for all research pipelines.

    Stores research data discovered by scanner agents. Each item includes
    source metadata, content, compliance status, and a relevance score.

    Full-text search is supported via the search_vector column, which
    is automatically updated by a PostgreSQL trigger on insert/update.

    Attributes:
        id: Unique identifier (UUID)
        source: Origin of the research (reddit, youtube, etc.)
        title: Headline or summary of the research
        content: Full text or transcript excerpt
        url: Source link for reference
        tags: Topic/theme tags for categorization
        source_metadata: Source-specific data (JSONB for flexibility)
        created_at: Timestamp when item was discovered
        score: Content potential score (0-10, higher is better)
        compliance_status: EU compliance check result
        search_vector: PostgreSQL tsvector for full-text search
    """

    __tablename__ = "research_items"

    # Primary key - UUID for distributed compatibility
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Source identification
    source: Mapped[str] = mapped_column(
        String(MAX_SOURCE_LENGTH),
        nullable=False,
        index=True,
    )

    # Content fields
    title: Mapped[str] = mapped_column(
        String(MAX_TITLE_LENGTH),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=False,
    )

    # Categorization
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(MAX_TAG_LENGTH)),
        default=list,
        server_default="{}",
    )

    # Source-specific metadata (flexible JSONB storage)
    # Note: Named 'source_metadata' as 'metadata' is reserved by SQLAlchemy
    source_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Scoring and compliance
    score: Mapped[float] = mapped_column(
        default=DEFAULT_SCORE,
        server_default=str(DEFAULT_SCORE),
    )

    compliance_status: Mapped[str] = mapped_column(
        String(MAX_COMPLIANCE_LENGTH),
        default=ComplianceStatus.COMPLIANT.value,
        server_default=ComplianceStatus.COMPLIANT.value,
    )

    # Full-text search vector (populated by PostgreSQL trigger)
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    # Table-level indexes for query performance
    # AC#2: Queries complete in < 500ms for pools up to 10,000 items
    __table_args__ = (
        # Score DESC for top-content queries
        Index("idx_research_items_score", score.desc()),
        # Created at DESC for recent-first queries
        Index("idx_research_items_created_at", created_at.desc()),
        # Compliance status for filtering
        Index("idx_research_items_compliance", compliance_status),
        # GIN index on tags for efficient array containment queries
        Index("idx_research_items_tags", tags, postgresql_using="gin"),
        # GIN index on search_vector for full-text search
        Index("idx_research_items_search", search_vector, postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ResearchItem(id={self.id}, source={self.source}, "
            f"score={self.score}, status={self.compliance_status})>"
        )
