"""Regulatory data models for EU Health Claims and Novel Food monitoring.

Epic 6: CleanMarket & Regulatory Intelligence
Story 6-1: EU Health Claims Register Monitor
Story 6-2: Novel Food Catalogue Monitor

SQLAlchemy ORM models for health claim tracking, novel food catalogue monitoring,
snapshots, and change detection. Uses PostgreSQL-specific features: UUID.

Models:
    - HealthClaim: Individual EU health claim record
    - ClaimSnapshot: Point-in-time register download record
    - ClaimChange: Detected difference between snapshots
    - NovelFoodEntry: EU Novel Food Catalogue entry
    - NovelFoodSnapshot: Point-in-time catalogue query record
    - NovelFoodChange: Detected change in catalogue

Enums:
    - ClaimStatus: EU claim authorization status
    - NovelFoodStatus: Novel food classification status
    - AuthorizationStatus: Novel food authorization status
    - ChangeType: Type of change detected
    - ChangeSeverity: Severity level of detected change
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, Index, Boolean, Integer, Float, func, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base

if TYPE_CHECKING:
    from typing import List


class ClaimStatus(str, Enum):
    """EU health claim authorization status.

    Values:
        AUTHORISED: Claim approved for use
        NON_AUTHORISED: Claim rejected
        ON_HOLD: Pending evaluation (Article 13.1/13.5)
        WITHDRAWN: Previously authorised, now removed
    """

    AUTHORISED = "authorised"
    NON_AUTHORISED = "non_authorised"
    ON_HOLD = "on_hold"
    WITHDRAWN = "withdrawn"


class ChangeType(str, Enum):
    """Type of change detected between register snapshots.

    Values:
        NEW: Claim present in current but not previous snapshot
        REMOVED: Claim present in previous but not current snapshot
        MODIFIED: Claim field value changed (non-status)
        STATUS_CHANGED: Claim authorization status changed
    """

    NEW = "new"
    REMOVED = "removed"
    MODIFIED = "modified"
    STATUS_CHANGED = "status_changed"


class ChangeSeverity(str, Enum):
    """Severity of detected change for alerting.

    Values:
        LOW: Minor field update (wording, reference)
        MEDIUM: Non-relevant claim change
        HIGH: New relevant claim approved
        CRITICAL: Status change on relevant substance
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NovelFoodStatus(str, Enum):
    """EU Novel Food Catalogue classification status.

    Story 6-2: Novel Food Catalogue Monitor.

    Values:
        NOVEL: Classified as novel food
        NOT_NOVEL: Not classified as novel food (traditional consumption)
        NOT_DETERMINED: Classification not yet determined
        AMBIGUOUS: Ambiguous classification (varies by form/preparation)
    """

    NOVEL = "novel"
    NOT_NOVEL = "not_novel"
    NOT_DETERMINED = "not_determined"
    AMBIGUOUS = "ambiguous"


class AuthorizationStatus(str, Enum):
    """EU Novel Food authorization status.

    Story 6-2: Novel Food Catalogue Monitor.

    Values:
        AUTHORISED: Authorised for market under EU regulation
        NOT_AUTHORISED: Not authorised for market
        PENDING: Authorization pending
        NOT_APPLICABLE: Authorization not applicable
    """

    AUTHORISED = "authorised"
    NOT_AUTHORISED = "not_authorised"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"


# Model constants
MAX_CLAIM_ID_LENGTH = 50
MAX_SUBSTANCE_LENGTH = 500
MAX_STATUS_LENGTH = 30
MAX_CATEGORY_LENGTH = 200
MAX_URL_LENGTH = 500
MAX_HASH_LENGTH = 64
MAX_REGULATION_LENGTH = 500
MAX_SPECIES_LENGTH = 300
MAX_ENTRY_NAME_LENGTH = 500


class HealthClaim(Base):
    """EU Health Claim from the register.

    Epic 6, Story 6-1: EU Health Claims Register Monitor.

    Each record represents one claim from the EU Register on nutrition
    and health claims. Claims are linked to a snapshot representing
    when they were downloaded.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_id: Foreign key to ClaimSnapshot
        claim_id: EU register claim identifier (e.g., "ID-0001")
        claim_type: Type of claim (Article 13.1, 14.1, etc.)
        substance: Nutrient or substance name
        health_relationship: Claimed health benefit
        claim_text: Full claim wording
        conditions_of_use: Usage conditions/restrictions
        food_category: Applicable food category
        status: Authorization status
        efsa_opinion: EFSA scientific opinion reference
        commission_regulation: EU regulation reference
        date_of_entry: When claim entered register
        last_update: Last register update for this claim
        restrictions: Usage restrictions
        is_relevant: Whether claim matches DAWO keywords
        relevance_category: Which keyword category matched
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """

    __tablename__ = "health_claims"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Snapshot relationship
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claim_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Claim identification
    claim_id: Mapped[str] = mapped_column(
        String(MAX_CLAIM_ID_LENGTH),
        nullable=False,
        index=True,
    )

    claim_type: Mapped[Optional[str]] = mapped_column(
        String(MAX_CATEGORY_LENGTH),
        nullable=True,
    )

    # Substance and health relationship
    substance: Mapped[str] = mapped_column(
        String(MAX_SUBSTANCE_LENGTH),
        nullable=False,
    )

    health_relationship: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    claim_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    conditions_of_use: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    food_category: Mapped[Optional[str]] = mapped_column(
        String(MAX_CATEGORY_LENGTH),
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ClaimStatus.ON_HOLD.value,
    )

    # Regulatory references
    efsa_opinion: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    commission_regulation: Mapped[Optional[str]] = mapped_column(
        String(MAX_REGULATION_LENGTH),
        nullable=True,
    )

    # Dates from the register
    date_of_entry: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    last_update: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    # Restrictions
    restrictions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # DAWO relevance
    is_relevant: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    relevance_category: Mapped[Optional[str]] = mapped_column(
        String(MAX_CATEGORY_LENGTH),
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
    snapshot: Mapped["ClaimSnapshot"] = relationship(
        "ClaimSnapshot",
        back_populates="claims",
    )

    # Indexes
    __table_args__ = (
        Index("idx_health_claims_substance", "substance"),
        Index("idx_health_claims_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<HealthClaim(id={self.id}, claim_id={self.claim_id}, "
            f"substance={self.substance}, status={self.status})>"
        )


class ClaimSnapshot(Base):
    """Point-in-time snapshot of the EU Health Claims Register.

    Epic 6, Story 6-1: EU Health Claims Register Monitor.

    Each snapshot records a download of the register, including metadata
    about the download and aggregate statistics.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_hash: SHA-256 hash of downloaded data
        claim_count: Total claims in this snapshot
        relevant_claim_count: Claims matching DAWO keywords
        source_url: URL the data was downloaded from
        downloaded_at: When the download occurred
        file_size_bytes: Size of downloaded data
        created_at: Record creation timestamp
    """

    __tablename__ = "claim_snapshots"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    snapshot_hash: Mapped[str] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=False,
    )

    claim_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    relevant_claim_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    source_url: Mapped[str] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=False,
    )

    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    claims: Mapped["List[HealthClaim]"] = relationship(
        "HealthClaim",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    changes: Mapped["List[ClaimChange]"] = relationship(
        "ClaimChange",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ClaimSnapshot(id={self.id}, claim_count={self.claim_count}, "
            f"hash={self.snapshot_hash})>"
        )


class ClaimChange(Base):
    """Detected change between two register snapshots.

    Epic 6, Story 6-1: EU Health Claims Register Monitor.

    Records individual field-level changes detected when comparing
    the current register snapshot to the previous one.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_id: Foreign key to the new ClaimSnapshot
        claim_id: EU register claim identifier
        change_type: Type of change (NEW, REMOVED, MODIFIED, STATUS_CHANGED)
        field_changed: Which field changed (null for NEW/REMOVED)
        old_value: Previous value (null for NEW)
        new_value: New value (null for REMOVED)
        is_relevant: Whether this change affects DAWO keywords
        severity: Severity level for alerting
        created_at: Record creation timestamp
    """

    __tablename__ = "claim_changes"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Snapshot relationship
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claim_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Change details
    claim_id: Mapped[str] = mapped_column(
        String(MAX_CLAIM_ID_LENGTH),
        nullable=False,
    )

    change_type: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    field_changed: Mapped[Optional[str]] = mapped_column(
        String(MAX_CATEGORY_LENGTH),
        nullable=True,
    )

    old_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    new_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relevance
    is_relevant: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    severity: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ChangeSeverity.LOW.value,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    snapshot: Mapped["ClaimSnapshot"] = relationship(
        "ClaimSnapshot",
        back_populates="changes",
    )

    # Indexes
    __table_args__ = (
        Index("idx_claim_changes_snapshot", "snapshot_id"),
        Index("idx_claim_changes_relevant", "is_relevant", "severity"),
    )

    def __repr__(self) -> str:
        return (
            f"<ClaimChange(id={self.id}, claim_id={self.claim_id}, "
            f"type={self.change_type})>"
        )


class NovelFoodSnapshot(Base):
    """Point-in-time snapshot of Novel Food Catalogue queries.

    Epic 6, Story 6-2: Novel Food Catalogue Monitor.

    Each snapshot records a complete query cycle across all configured
    mushroom species, including aggregate statistics and timing.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_hash: SHA-256 hash of combined entry data
        total_entries: Total entries found across all species
        relevant_entries: Entries matching DAWO species
        species_queried: Number of species queried
        search_duration_seconds: Total time for all queries
        created_at: Record creation timestamp
    """

    __tablename__ = "novel_food_snapshots"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    snapshot_hash: Mapped[str] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=False,
    )

    total_entries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    relevant_entries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    species_queried: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    search_duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    entries: Mapped["List[NovelFoodEntry]"] = relationship(
        "NovelFoodEntry",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    changes: Mapped["List[NovelFoodChange]"] = relationship(
        "NovelFoodChange",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<NovelFoodSnapshot(id={self.id}, total_entries={self.total_entries}, "
            f"hash={self.snapshot_hash})>"
        )


class NovelFoodEntry(Base):
    """EU Novel Food Catalogue entry.

    Epic 6, Story 6-2: Novel Food Catalogue Monitor.

    Each record represents one entry from the EU Novel Food Catalogue,
    linked to a snapshot representing when the query was performed.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_id: Foreign key to NovelFoodSnapshot
        species_latin: Latin species name (e.g., "Hericium erinaceus")
        species_common: Common name (e.g., "Lion's Mane")
        entry_name: Catalogue entry name (composite key component)
        novel_food_status: Novel food classification
        authorization_status: Market authorization status
        history_of_consumption: History of consumption details
        member_state_comments: EU member state comments
        commission_comments: European Commission comments
        conditions_of_use: Usage conditions/restrictions
        regulation_reference: EU regulation reference
        union_list_entry: Union List entry reference
        source_url: URL the data was queried from
        raw_html_hash: SHA-256 hash of raw response for this entry
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """

    __tablename__ = "novel_food_entries"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Snapshot relationship
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("novel_food_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Species identification
    species_latin: Mapped[str] = mapped_column(
        String(MAX_SPECIES_LENGTH),
        nullable=False,
    )

    species_common: Mapped[Optional[str]] = mapped_column(
        String(MAX_SPECIES_LENGTH),
        nullable=True,
    )

    entry_name: Mapped[str] = mapped_column(
        String(MAX_ENTRY_NAME_LENGTH),
        nullable=False,
    )

    # Status fields
    novel_food_status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=NovelFoodStatus.NOT_DETERMINED.value,
    )

    authorization_status: Mapped[Optional[str]] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=True,
    )

    # Detail fields
    history_of_consumption: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    member_state_comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    commission_comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    conditions_of_use: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    regulation_reference: Mapped[Optional[str]] = mapped_column(
        String(MAX_REGULATION_LENGTH),
        nullable=True,
    )

    union_list_entry: Mapped[Optional[str]] = mapped_column(
        String(MAX_REGULATION_LENGTH),
        nullable=True,
    )

    # Source tracking
    source_url: Mapped[Optional[str]] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=True,
    )

    raw_html_hash: Mapped[Optional[str]] = mapped_column(
        String(MAX_HASH_LENGTH),
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
    snapshot: Mapped["NovelFoodSnapshot"] = relationship(
        "NovelFoodSnapshot",
        back_populates="entries",
    )

    # Indexes
    __table_args__ = (
        Index("idx_novel_food_entries_species", "species_latin"),
        Index("idx_novel_food_entries_snapshot", "snapshot_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<NovelFoodEntry(id={self.id}, species={self.species_latin}, "
            f"status={self.novel_food_status})>"
        )


class NovelFoodChange(Base):
    """Detected change in the Novel Food Catalogue.

    Epic 6, Story 6-2: Novel Food Catalogue Monitor.

    Records individual changes detected when comparing current catalogue
    entries against the previous snapshot.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_id: Foreign key to the new NovelFoodSnapshot
        species_latin: Latin species name
        entry_name: Catalogue entry name
        change_type: Type of change (NEW, REMOVED, MODIFIED, STATUS_CHANGED)
        field_changed: Which field changed (null for NEW/REMOVED)
        old_value: Previous value (null for NEW)
        new_value: New value (null for REMOVED)
        severity: Severity level for alerting
        created_at: Record creation timestamp
    """

    __tablename__ = "novel_food_changes"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Snapshot relationship
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("novel_food_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Entry identification (composite key for matching)
    species_latin: Mapped[str] = mapped_column(
        String(MAX_SPECIES_LENGTH),
        nullable=False,
    )

    entry_name: Mapped[str] = mapped_column(
        String(MAX_ENTRY_NAME_LENGTH),
        nullable=False,
    )

    # Change details
    change_type: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    field_changed: Mapped[Optional[str]] = mapped_column(
        String(MAX_CATEGORY_LENGTH),
        nullable=True,
    )

    old_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    new_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    severity: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ChangeSeverity.LOW.value,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    snapshot: Mapped["NovelFoodSnapshot"] = relationship(
        "NovelFoodSnapshot",
        back_populates="changes",
    )

    # Indexes
    __table_args__ = (
        Index("idx_novel_food_changes_snapshot", "snapshot_id"),
        Index("idx_novel_food_changes_severity", "severity"),
    )

    def __repr__(self) -> str:
        return (
            f"<NovelFoodChange(id={self.id}, species={self.species_latin}, "
            f"type={self.change_type})>"
        )


# Story 6-3: Mattilsynet Regulatory Monitor constants
MAX_TITLE_LENGTH = 500
MAX_PAGE_NAME_LENGTH = 200
MAX_SUMMARY_LENGTH = 2000
MAX_SOURCE_TYPE_LENGTH = 30


class MattilsynetSourceType(str, Enum):
    """Source type for Mattilsynet regulatory updates.

    Story 6-3: Mattilsynet Regulatory Monitor.

    Values:
        RSS_NEWS: Update discovered from news RSS feed
        RSS_WARNING: Update discovered from warnings RSS feed
        PAGE_CHANGE: Update detected via page hash change
        SITEMAP_NEW: New URL discovered via sitemap
    """

    RSS_NEWS = "rss_news"
    RSS_WARNING = "rss_warning"
    PAGE_CHANGE = "page_change"
    SITEMAP_NEW = "sitemap_new"


class MattilsynetCategory(str, Enum):
    """Category of Mattilsynet regulatory content.

    Story 6-3: Mattilsynet Regulatory Monitor.

    Values:
        ENFORCEMENT: Enforcement action (tilsyn, vedtak)
        REGULATION: Regulation change or update
        GUIDANCE: Guidance document or recommendation
        NEWS: General news article
        RECALL: Product recall (tilbakekalling)
        IMPORT_BAN: Import refusal or ban (importnekt)
    """

    ENFORCEMENT = "enforcement"
    REGULATION = "regulation"
    GUIDANCE = "guidance"
    NEWS = "news"
    RECALL = "recall"
    IMPORT_BAN = "import_ban"


class MattilsynetSnapshot(Base):
    """Point-in-time snapshot of a Mattilsynet monitoring scan.

    Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.

    Each snapshot records one complete scan cycle across RSS feeds
    and monitored pages, including aggregate statistics and timing.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_hash: SHA-256 hash of combined scan data
        total_updates: Total updates found in this scan
        relevant_updates: Updates matching DAWO keywords
        feeds_checked: Number of RSS feeds checked
        pages_checked: Number of pages checked for changes
        scan_duration_seconds: Total scan time in seconds
        created_at: Record creation timestamp
    """

    __tablename__ = "mattilsynet_snapshots"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    snapshot_hash: Mapped[str] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=False,
    )

    total_updates: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    relevant_updates: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    feeds_checked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    pages_checked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    scan_duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    updates: Mapped["List[MattilsynetUpdate]"] = relationship(
        "MattilsynetUpdate",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<MattilsynetSnapshot(id={self.id}, total_updates={self.total_updates}, "
            f"hash={self.snapshot_hash})>"
        )


class MattilsynetUpdate(Base):
    """Regulatory update from Mattilsynet monitoring.

    Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.

    Each record represents one regulatory update found during a scan,
    whether from an RSS feed item or a detected page change.

    Attributes:
        id: Unique identifier (UUID)
        snapshot_id: Foreign key to MattilsynetSnapshot
        title: Update headline/title
        url: Source URL of the update
        content_summary: Brief summary of content
        published_at: When the content was published
        source_type: How the update was discovered
        category: Regulatory content category
        keywords_matched: List of matched keywords (JSONB)
        relevance_tier: Keyword tier that matched (0=none, 1=high, 2=medium)
        severity: Alert severity level
        is_relevant: Whether update is relevant to DAWO
        raw_content_hash: SHA-256 hash of raw content
        created_at: Record creation timestamp
    """

    __tablename__ = "mattilsynet_updates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("mattilsynet_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(MAX_TITLE_LENGTH),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=False,
    )

    content_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(MAX_SOURCE_TYPE_LENGTH),
        nullable=False,
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(MAX_CATEGORY_LENGTH),
        nullable=True,
    )

    keywords_matched: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    relevance_tier: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    severity: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ChangeSeverity.LOW.value,
    )

    is_relevant: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    raw_content_hash: Mapped[Optional[str]] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    snapshot: Mapped["MattilsynetSnapshot"] = relationship(
        "MattilsynetSnapshot",
        back_populates="updates",
    )

    __table_args__ = (
        Index("idx_mattilsynet_updates_snapshot", "snapshot_id"),
        Index("idx_mattilsynet_updates_relevant", "is_relevant", "severity"),
        Index("idx_mattilsynet_updates_url", "url", "snapshot_id", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<MattilsynetUpdate(id={self.id}, title={self.title}, "
            f"severity={self.severity})>"
        )


class MattilsynetPageHash(Base):
    """Stored hash for page change detection.

    Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.

    Tracks the SHA-256 hash of monitored page content to detect
    changes between scan cycles.

    Attributes:
        id: Unique identifier (UUID)
        url: URL of the monitored page
        page_name: Human-readable page name
        content_hash: SHA-256 hash of extracted main content
        last_checked: When the page was last checked
        last_changed: When the page content last changed
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """

    __tablename__ = "mattilsynet_page_hashes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    url: Mapped[str] = mapped_column(
        String(MAX_URL_LENGTH),
        nullable=False,
    )

    page_name: Mapped[str] = mapped_column(
        String(MAX_PAGE_NAME_LENGTH),
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=False,
    )

    last_checked: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    last_changed: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_mattilsynet_page_hashes_url", "url", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<MattilsynetPageHash(id={self.id}, url={self.url}, "
            f"hash={self.content_hash})>"
        )


# Story 6-5: Competitor Content Scanner constants
MAX_COMPETITOR_NAME_LENGTH = 200
MAX_COMPETITOR_URL_LENGTH = 2048
MAX_DOMAIN_LENGTH = 500


class CompetitorSourceType(str, Enum):
    """Source type for competitor content.

    Story 6-5: Competitor Content Scanner.

    Values:
        INSTAGRAM: Content from Instagram posts
        WEBSITE: Content from website pages
    """

    INSTAGRAM = "instagram"
    WEBSITE = "website"


class ExtractionStatus(str, Enum):
    """Health claim extraction status for competitor content.

    Story 6-5: Competitor Content Scanner.

    Values:
        PENDING: Awaiting extraction (has health language)
        EXTRACTED: Claims extracted by Story 6-6
        NO_CLAIMS: No health language detected
        ERROR: Extraction failed
    """

    PENDING = "pending"
    EXTRACTED = "extracted"
    NO_CLAIMS = "no_claims"
    ERROR = "error"


class CompetitorScanSnapshot(Base):
    """Point-in-time snapshot of a competitor content scan.

    Epic 6, Story 6-5: Competitor Content Scanner.

    Each snapshot records one scan cycle for a single competitor,
    including aggregate statistics and timing.

    Attributes:
        id: Unique identifier (UUID)
        competitor_name: Name of the competitor scanned
        source_type: Source type (instagram or website)
        scan_started_at: When the scan started
        scan_completed_at: When the scan completed (nullable if in progress)
        total_items_found: Total content items found
        items_with_health_language: Items flagged with health language
        status: Scan status (in_progress, completed, failed)
        error_message: Error details if scan failed
        created_at: Record creation timestamp
    """

    __tablename__ = "competitor_scan_snapshots"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    competitor_name: Mapped[str] = mapped_column(
        String(MAX_COMPETITOR_NAME_LENGTH),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    scan_started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    scan_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    total_items_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    items_with_health_language: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default="in_progress",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    items: Mapped["List[CompetitorContent]"] = relationship(
        "CompetitorContent",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CompetitorScanSnapshot(id={self.id}, "
            f"competitor={self.competitor_name}, status={self.status})>"
        )


class CompetitorContent(Base):
    """Competitor content item for evidence collection.

    Epic 6, Story 6-5: Competitor Content Scanner.

    Each record represents one piece of competitor content (Instagram post
    or website page). Content is stored raw for evidence integrity.
    Images are NOT stored (privacy/copyright).

    Attributes:
        id: Unique identifier (UUID)
        snapshot_id: Foreign key to CompetitorScanSnapshot
        competitor_name: Name of the competitor
        source_type: Source type (instagram or website)
        source_url: URL of the content
        content_text: Full text content
        hashtags: List of hashtags (JSONB, nullable)
        account_or_domain: Instagram account or website domain
        published_at: When content was published (nullable)
        captured_at: When content was captured by scanner
        content_hash: SHA-256 of normalized content for dedup
        has_health_language: Whether health language was detected
        health_keywords_matched: List of matched keywords (JSONB, nullable)
        extraction_status: Status for Story 6-6 claim extraction
        created_at: Record creation timestamp
    """

    __tablename__ = "competitor_content"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("competitor_scan_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    competitor_name: Mapped[str] = mapped_column(
        String(MAX_COMPETITOR_NAME_LENGTH),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        String(MAX_COMPETITOR_URL_LENGTH),
        nullable=False,
    )

    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    hashtags: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    account_or_domain: Mapped[str] = mapped_column(
        String(MAX_DOMAIN_LENGTH),
        nullable=False,
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=False,
    )

    has_health_language: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    health_keywords_matched: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ExtractionStatus.NO_CLAIMS.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    snapshot: Mapped["CompetitorScanSnapshot"] = relationship(
        "CompetitorScanSnapshot",
        back_populates="items",
    )

    extracted_claims: Mapped["List[ExtractedHealthClaim]"] = relationship(
        "ExtractedHealthClaim",
        back_populates="competitor_content",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_competitor_content_snapshot", "snapshot_id"),
        Index("idx_competitor_content_extraction", "extraction_status"),
        Index(
            "idx_competitor_content_hash",
            "content_hash",
            "competitor_name",
            unique=True,
        ),
        Index("idx_competitor_content_source", "source_type", "competitor_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<CompetitorContent(id={self.id}, "
            f"competitor={self.competitor_name}, "
            f"source={self.source_type})>"
        )


# Story 6-6: Health Claim Extraction Engine constants
MAX_CLAIM_TEXT_LENGTH = 1000
MAX_CONTEXT_LENGTH = 500
MAX_REASONING_LENGTH = 2000
MAX_EXTRACTION_METHOD_LENGTH = 30
MAX_ARTICLE_REF_LENGTH = 50
MAX_LANGUAGE_CODE_LENGTH = 10


class ClaimCategory(str, Enum):
    """Extracted health claim category.

    Story 6-6: Health Claim Extraction Engine.

    Values:
        TREATMENT: Medicinal/treatment claim (prohibited under EC 1924/2006)
        PREVENTION: Disease risk reduction (Article 14.1a)
        ENHANCEMENT: Body function enhancement (Article 13.1)
        GENERAL_WELLNESS: General wellbeing claim (Article 13.1, borderline)
    """

    TREATMENT = "treatment"
    PREVENTION = "prevention"
    ENHANCEMENT = "enhancement"
    GENERAL_WELLNESS = "general_wellness"


class ReviewStatus(str, Enum):
    """Review status for extracted health claims.

    Story 6-6: Health Claim Extraction Engine.

    Values:
        AUTO_APPROVED: Confidence >= threshold, auto-proceeds to violation detection
        MANUAL_REVIEW: Confidence < threshold, requires human review
        REVIEWED: Human has reviewed this claim
    """

    AUTO_APPROVED = "auto_approved"
    MANUAL_REVIEW = "manual_review"
    REVIEWED = "reviewed"


class ExtractedHealthClaim(Base):
    """Health claim extracted from competitor content.

    Epic 6, Story 6-6: Health Claim Extraction Engine.

    Each record represents one health claim extracted from competitor content
    using the hybrid regex+LLM extraction engine. Claims are linked to their
    source CompetitorContent record.

    Attributes:
        id: Unique identifier (UUID)
        competitor_content_id: FK to competitor_content.id
        claim_text: Exact extracted phrase
        surrounding_context: Text around the claim for context
        claim_category: Category (treatment/prevention/enhancement/general_wellness)
        confidence_score: Confidence 0-100
        language_detected: Detected language ("en", "no", "unknown")
        extraction_method: Method used ("regex", "llm", "hybrid")
        eu_article_reference: EU article reference (e.g. "13.1", "14.1a", "prohibited")
        matched_pattern: Regex pattern that matched (if any)
        llm_reasoning: LLM classification reasoning (if any)
        review_status: Review status (auto_approved/manual_review/reviewed)
        created_at: Record creation timestamp
    """

    __tablename__ = "extracted_health_claims"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    competitor_content_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("competitor_content.id", ondelete="CASCADE"),
        nullable=False,
    )

    claim_text: Mapped[str] = mapped_column(
        String(MAX_CLAIM_TEXT_LENGTH),
        nullable=False,
    )

    surrounding_context: Mapped[Optional[str]] = mapped_column(
        String(MAX_CONTEXT_LENGTH),
        nullable=True,
    )

    claim_category: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    confidence_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    language_detected: Mapped[str] = mapped_column(
        String(MAX_LANGUAGE_CODE_LENGTH),
        nullable=False,
        default="unknown",
    )

    extraction_method: Mapped[str] = mapped_column(
        String(MAX_EXTRACTION_METHOD_LENGTH),
        nullable=False,
    )

    eu_article_reference: Mapped[Optional[str]] = mapped_column(
        String(MAX_ARTICLE_REF_LENGTH),
        nullable=True,
    )

    matched_pattern: Mapped[Optional[str]] = mapped_column(
        String(MAX_CLAIM_TEXT_LENGTH),
        nullable=True,
    )

    llm_reasoning: Mapped[Optional[str]] = mapped_column(
        String(MAX_REASONING_LENGTH),
        nullable=True,
    )

    review_status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=ReviewStatus.MANUAL_REVIEW.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    competitor_content: Mapped["CompetitorContent"] = relationship(
        "CompetitorContent",
        back_populates="extracted_claims",
    )

    violation: Mapped[Optional["CompetitorViolation"]] = relationship(
        "CompetitorViolation",
        back_populates="extracted_claim",
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_extracted_claims_content", "competitor_content_id"),
        Index("idx_extracted_claims_category", "claim_category"),
        Index("idx_extracted_claims_confidence", "confidence_score"),
        Index("idx_extracted_claims_review", "review_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExtractedHealthClaim(id={self.id}, "
            f"category={self.claim_category}, "
            f"confidence={self.confidence_score})>"
        )


# Story 6-7: EU Violation Detection constants
MAX_VIOLATION_TYPE_LENGTH = 100
MAX_DETECTION_REASONING_LENGTH = 2000
MAX_NEAREST_CLAIM_LENGTH = 1000


class ViolationStatus(str, Enum):
    """Classification of an extracted claim against EU regulations.

    Story 6-7: EU Violation Detection.

    Values:
        VIOLATION: Claim violates EU regulations
        SUSPECT: Borderline claim requiring operator review
        COMPLIANT: Claim is compliant with regulations
    """

    VIOLATION = "violation"
    SUSPECT = "suspect"
    COMPLIANT = "compliant"


class ViolationSeverity(str, Enum):
    """Severity level of a detected violation.

    Story 6-7: EU Violation Detection.

    Values:
        HIGH: High severity (treatment/prevention claims)
        MEDIUM: Medium severity (enhancement claims)
        LOW: Low severity (general wellness claims)
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceCollectionStatus(str, Enum):
    """Status of evidence collection for a violation.

    Story 6-7: EU Violation Detection.

    Values:
        PENDING_COLLECTION: Awaiting evidence screenshot (Story 6-8)
        COLLECTED: Evidence has been captured
        NOT_REQUIRED: No evidence needed (compliant claims)
    """

    PENDING_COLLECTION = "pending_collection"
    COLLECTED = "collected"
    NOT_REQUIRED = "not_required"


class CompetitorViolation(Base):
    """EU regulation violation detected from competitor content.

    Epic 6, Story 6-7: EU Violation Detection.

    Each record represents one violation assessment of an extracted health
    claim against EU regulations (EC 1924/2006). Links to ExtractedHealthClaim
    via one-to-one relationship (unique constraint on extracted_claim_id).

    Attributes:
        id: Unique identifier (UUID)
        extracted_claim_id: FK to extracted_health_claims.id (unique)
        violation_status: Classification result (violation/suspect/compliant)
        severity: Severity level (high/medium/low)
        regulation_article: EU regulation reference
        violation_type: Type descriptor (e.g. unauthorized_treatment_claim)
        detection_reasoning: Why this classification was made
        authorized_claims_checked: Number of EU register claims checked
        nearest_authorized_claim: Closest matching authorized claim (if any)
        competitor_name: Denormalized competitor name for query efficiency
        source_url: Denormalized source URL for query efficiency
        evidence_status: Evidence collection status for Story 6-8
        detected_at: When detection ran
        created_at: Record creation timestamp
    """

    __tablename__ = "competitor_violations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    extracted_claim_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("extracted_health_claims.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    violation_status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    regulation_article: Mapped[str] = mapped_column(
        String(MAX_REGULATION_LENGTH),
        nullable=False,
    )

    violation_type: Mapped[str] = mapped_column(
        String(MAX_VIOLATION_TYPE_LENGTH),
        nullable=False,
    )

    detection_reasoning: Mapped[str] = mapped_column(
        String(MAX_DETECTION_REASONING_LENGTH),
        nullable=False,
    )

    authorized_claims_checked: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    nearest_authorized_claim: Mapped[Optional[str]] = mapped_column(
        String(MAX_NEAREST_CLAIM_LENGTH),
        nullable=True,
    )

    competitor_name: Mapped[str] = mapped_column(
        String(MAX_COMPETITOR_NAME_LENGTH),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        String(MAX_COMPETITOR_URL_LENGTH),
        nullable=False,
    )

    evidence_status: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
        default=EvidenceCollectionStatus.PENDING_COLLECTION.value,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    extracted_claim: Mapped["ExtractedHealthClaim"] = relationship(
        "ExtractedHealthClaim",
        back_populates="violation",
    )

    evidence: Mapped[Optional["Evidence"]] = relationship(
        "Evidence",
        back_populates="violation",
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_violations_claim", "extracted_claim_id", unique=True),
        Index("idx_violations_status", "violation_status"),
        Index("idx_violations_severity", "severity"),
        Index("idx_violations_competitor", "competitor_name"),
        Index("idx_violations_evidence", "evidence_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CompetitorViolation(id={self.id}, "
            f"status={self.violation_status}, "
            f"severity={self.severity})>"
        )


# Story 6-8: Evidence Collection & Screenshots constants
MAX_SOURCE_TYPE_EVIDENCE_LENGTH = 50
MAX_AUDIT_ACTION_LENGTH = 50
MAX_AUDIT_ACTOR_LENGTH = 100


class Evidence(Base):
    """Immutable evidence record for a competitor violation.

    Epic 6, Story 6-8: Evidence Collection & Screenshots.

    Each record represents captured screenshot evidence for a single
    CompetitorViolation. Content fields are protected by three-layer
    immutability: application guard, DB trigger, and file permissions.

    Attributes:
        id: Unique identifier (UUID).
        violation_id: FK to competitor_violations.id (unique, one per violation).
        competitor_name: Denormalized competitor name.
        source_url: Original source URL.
        source_type: 'instagram_post' or 'website_page'.
        claim_text: Extracted health claim text.
        claim_category: treatment/prevention/enhancement/general_wellness.
        violation_type: Violation type descriptor.
        severity: high/medium/low.
        regulation_violated: EU regulation reference (nullable).
        detection_reasoning: Classification reasoning (nullable).
        confidence: Confidence 0.0-1.0 (normalized from 0-100).
        screenshot_path: Relative path to screenshot file.
        screenshot_hash: SHA-256 hex of screenshot bytes.
        screenshot_size_bytes: File size in bytes.
        captured_at: When screenshot was captured (timezone-aware).
        created_at: Record creation timestamp.
        evidence_metadata: JSONB for engagement metrics, hashtags, page title.
    """

    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    violation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("competitor_violations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    competitor_name: Mapped[str] = mapped_column(
        String(MAX_COMPETITOR_NAME_LENGTH),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(MAX_SOURCE_TYPE_EVIDENCE_LENGTH),
        nullable=False,
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    claim_category: Mapped[str] = mapped_column(
        String(MAX_SOURCE_TYPE_EVIDENCE_LENGTH),
        nullable=False,
    )

    violation_type: Mapped[str] = mapped_column(
        String(MAX_SOURCE_TYPE_EVIDENCE_LENGTH),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(MAX_STATUS_LENGTH),
        nullable=False,
    )

    regulation_violated: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    detection_reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    screenshot_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    screenshot_hash: Mapped[str] = mapped_column(
        String(MAX_HASH_LENGTH),
        nullable=False,
    )

    screenshot_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    evidence_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    # Relationships
    violation: Mapped["CompetitorViolation"] = relationship(
        "CompetitorViolation",
        back_populates="evidence",
    )

    audit_logs: Mapped["List[EvidenceAuditLog]"] = relationship(
        "EvidenceAuditLog",
        back_populates="evidence",
    )

    # Indexes
    __table_args__ = (
        Index("ix_evidence_captured_at", "captured_at"),
        Index("ix_evidence_competitor_date", "competitor_name", "captured_at"),
        Index("ix_evidence_violation_id", "violation_id", unique=True),
        Index("ix_evidence_violation_type", "violation_type"),
        Index("ix_evidence_severity", "severity"),
    )

    def __repr__(self) -> str:
        return (
            f"<Evidence(id={self.id}, "
            f"competitor={self.competitor_name}, "
            f"severity={self.severity})>"
        )


class EvidenceAuditLog(Base):
    """Audit log entry for evidence operations.

    Epic 6, Story 6-8: Evidence Collection & Screenshots.

    Tracks all operations on evidence records: creation, verification,
    download, report inclusion, and blocked modification attempts.

    Attributes:
        id: Unique identifier (UUID).
        evidence_id: FK to evidence.id (ondelete RESTRICT).
        action: Operation type (created/verified/downloaded/report_included/modification_blocked).
        actor: Who performed the action (system/operator/report_generator).
        details: JSONB with operation-specific data.
        hash_verified: Whether integrity check passed (nullable).
        created_at: When this log entry was created.
    """

    __tablename__ = "evidence_audit_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(MAX_AUDIT_ACTION_LENGTH),
        nullable=False,
    )

    actor: Mapped[str] = mapped_column(
        String(MAX_AUDIT_ACTOR_LENGTH),
        nullable=False,
    )

    details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    hash_verified: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    evidence: Mapped["Evidence"] = relationship(
        "Evidence",
        back_populates="audit_logs",
    )

    # Indexes
    __table_args__ = (
        Index("ix_evidence_audit_evidence_id", "evidence_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<EvidenceAuditLog(id={self.id}, "
            f"action={self.action}, "
            f"actor={self.actor})>"
        )


__all__ = [
    "HealthClaim",
    "ClaimSnapshot",
    "ClaimChange",
    "ClaimStatus",
    "ChangeType",
    "ChangeSeverity",
    "NovelFoodEntry",
    "NovelFoodSnapshot",
    "NovelFoodChange",
    "NovelFoodStatus",
    "AuthorizationStatus",
    "MattilsynetSnapshot",
    "MattilsynetUpdate",
    "MattilsynetPageHash",
    "MattilsynetSourceType",
    "MattilsynetCategory",
    "CompetitorScanSnapshot",
    "CompetitorContent",
    "CompetitorSourceType",
    "ExtractionStatus",
    "ExtractedHealthClaim",
    "ClaimCategory",
    "ReviewStatus",
    "CompetitorViolation",
    "ViolationStatus",
    "ViolationSeverity",
    "EvidenceCollectionStatus",
    "Evidence",
    "EvidenceAuditLog",
    "MAX_TITLE_LENGTH",
    "MAX_PAGE_NAME_LENGTH",
    "MAX_SUMMARY_LENGTH",
    "MAX_SOURCE_TYPE_LENGTH",
    "MAX_COMPETITOR_NAME_LENGTH",
    "MAX_COMPETITOR_URL_LENGTH",
    "MAX_DOMAIN_LENGTH",
    "MAX_CLAIM_TEXT_LENGTH",
    "MAX_CONTEXT_LENGTH",
    "MAX_REASONING_LENGTH",
    "MAX_EXTRACTION_METHOD_LENGTH",
    "MAX_ARTICLE_REF_LENGTH",
    "MAX_LANGUAGE_CODE_LENGTH",
    "MAX_VIOLATION_TYPE_LENGTH",
    "MAX_DETECTION_REASONING_LENGTH",
    "MAX_NEAREST_CLAIM_LENGTH",
    "MAX_SOURCE_TYPE_EVIDENCE_LENGTH",
    "MAX_AUDIT_ACTION_LENGTH",
    "MAX_AUDIT_ACTOR_LENGTH",
]
