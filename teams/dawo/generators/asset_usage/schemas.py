"""Data schemas for Asset Usage Tracking.

Defines all dataclasses and enums for usage events, performance metrics,
and asset records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Platform(Enum):
    """Publishing platform for asset usage."""

    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_REEL = "instagram_reel"


class AssetType(Enum):
    """Type of generated asset.

    Note: This is distinct from integrations.google_drive.AssetType which
    defines folder routing. This enum tracks content generation source.
    """

    ORSHOT_GRAPHIC = "orshot_graphic"
    NANO_BANANA_IMAGE = "nano_banana_image"
    PRODUCT_PHOTO = "product_photo"


class AssetStatus(Enum):
    """Asset lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class UsageEvent:
    """Record of a single asset usage in a published post.

    Attributes:
        event_id: Unique identifier for this usage event
        asset_id: Reference to the asset used
        post_id: Published post identifier
        platform: Publishing platform
        publish_date: When the post was published
        created_at: When this record was created
    """

    event_id: str
    asset_id: str
    post_id: str
    platform: Platform
    publish_date: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PerformanceMetrics:
    """Performance data for an asset usage.

    Collected by Epic 7 at 24h/48h/7d intervals after publishing.

    Attributes:
        engagement_rate: 0.0-1.0 (likes+comments+shares / reach)
        conversions: Number of attributed conversions (>= 0)
        reach: Total audience reached (>= 0)
        performance_score: 0-10 calculated score
        collected_at: When metrics were collected
        collection_interval: Time since publish ("24h", "48h", "7d")

    Raises:
        ValueError: If engagement_rate not in [0.0, 1.0] range
        ValueError: If conversions or reach is negative
    """

    engagement_rate: float          # 0.0-1.0 (likes+comments+shares / reach)
    conversions: int                # Number of attributed conversions
    reach: int                      # Total audience reached
    performance_score: float        # 0-10 calculated score
    collected_at: datetime
    collection_interval: str        # "24h", "48h", "7d"

    def __post_init__(self) -> None:
        """Validate metric bounds after initialization."""
        if not 0.0 <= self.engagement_rate <= 1.0:
            raise ValueError(
                f"engagement_rate must be between 0.0 and 1.0, got {self.engagement_rate}"
            )
        if self.conversions < 0:
            raise ValueError(
                f"conversions must be non-negative, got {self.conversions}"
            )
        if self.reach < 0:
            raise ValueError(
                f"reach must be non-negative, got {self.reach}"
            )


@dataclass
class AssetPerformanceResult:
    """Calculated performance score for an asset.

    Aggregates all usage performance into overall metrics.

    Attributes:
        asset_id: Asset identifier
        overall_score: 0-10 weighted average across all usages
        usage_count: Total number of times asset was used
        avg_engagement_rate: Average engagement across usages
        total_conversions: Sum of conversions from all usages
        avg_reach: Average reach across usages
        score_breakdown: Component scores (engagement, conversions, reach)
    """

    asset_id: str
    overall_score: float            # 0-10 weighted average
    usage_count: int
    avg_engagement_rate: float
    total_conversions: int
    avg_reach: int
    score_breakdown: dict[str, float]  # engagement, conversions, reach scores


@dataclass
class AssetUsageRecord:
    """Complete usage history for an asset.

    Tracks all usage events and performance metrics for a single asset.

    Attributes:
        asset_id: Unique asset identifier
        asset_type: Type of generated asset
        file_path: Google Drive path to asset
        original_quality_score: Score from generator (Orshot/Nano Banana)
        topic: Content topic for filtering
        usage_events: List of all usage events
        performance_history: List of all performance metrics
        overall_performance: Aggregated performance result
        status: Current lifecycle status
        created_at: When asset was first registered
        archived_at: When asset was archived (if applicable)
    """

    asset_id: str
    asset_type: AssetType
    file_path: str
    original_quality_score: float   # From generator (Orshot/Nano Banana)
    topic: str                      # Content topic for filtering
    usage_events: list[UsageEvent] = field(default_factory=list)
    performance_history: list[PerformanceMetrics] = field(default_factory=list)
    overall_performance: Optional[AssetPerformanceResult] = None
    status: AssetStatus = AssetStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    archived_at: Optional[datetime] = None


@dataclass
class AssetSuggestion:
    """Asset suggestion for content selection.

    Returned when content team requests asset suggestions,
    sorted by performance score descending.

    Attributes:
        asset_id: Asset identifier
        file_path: Google Drive path
        asset_type: Type of asset
        topic: Content topic
        performance_score: 0-10 score (or original quality if unused)
        usage_count: Number of times used
        last_used: Most recent usage date
        quality_score: Original generator quality score
        rank: Suggestion ranking (1 = best)
    """

    asset_id: str
    file_path: str
    asset_type: AssetType
    topic: str
    performance_score: float        # 0-10
    usage_count: int
    last_used: Optional[datetime]
    quality_score: float            # Original from generator
    rank: int                       # Suggestion ranking (1 = best)


@dataclass
class ArchiveRecord:
    """Record of archived asset.

    Preserves full history when asset is moved to archive.

    Attributes:
        asset_id: Asset identifier
        original_path: Original Google Drive path
        archive_path: New path in Archive folder
        archive_date: When asset was archived
        performance_summary: Final performance summary
        total_usages: Total usage count at archive time
        metadata: Additional metadata (asset_type, topic, etc.)
    """

    asset_id: str
    original_path: str
    archive_path: str
    archive_date: datetime
    performance_summary: Optional[AssetPerformanceResult]
    total_usages: int
    metadata: dict[str, Any]
