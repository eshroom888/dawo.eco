# Story 3.9: Asset Usage Tracking

Status: done

---

## Story

As an **operator**,
I want asset usage history tracked with performance correlation,
So that I know which visuals work best.

---

## Acceptance Criteria

1. **Given** an asset is used in a published post
   **When** the post is published
   **Then** asset record is updated with: post ID, publish date, platform

2. **Given** performance data is collected (Epic 7)
   **When** post metrics are available
   **Then** asset record is updated with: engagement rate, conversions
   **And** asset receives a performance score

3. **Given** asset performance is tracked
   **When** content team selects visuals
   **Then** they can see: past usage count, average performance
   **And** high-performing assets are suggested first

4. **Given** an asset is archived
   **When** moved to Archive folder
   **Then** full performance history is preserved
   **And** asset remains searchable for analytics

---

## Tasks / Subtasks

- [x] Task 1: Create AssetUsageTracker package structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/generators/asset_usage/` package
  - [x] 1.2 Implement `AssetUsageTrackerProtocol` for testability
  - [x] 1.3 Implement `AssetUsageTracker` class with constructor injection
  - [x] 1.4 Accept `GoogleDriveClientProtocol` via injection (from integrations/)
  - [x] 1.5 Create `AssetUsageRecord`, `UsageEvent`, `PerformanceMetrics` dataclasses
  - [x] 1.6 Export all types in `__init__.py` with complete `__all__` list

- [x] Task 2: Implement usage recording (AC: #1)
  - [x] 2.1 Create `record_usage()` method accepting asset_id, post_id, platform
  - [x] 2.2 Store usage event with timestamp, post_id, platform
  - [x] 2.3 Increment usage_count on asset record
  - [x] 2.4 Create `UsageEvent` dataclass with asset_id, post_id, publish_date, platform
  - [x] 2.5 Handle concurrent usage recording (multiple posts same asset)

- [x] Task 3: Implement performance metrics tracking (AC: #2)
  - [x] 3.1 Create `update_performance()` method accepting asset_id, metrics
  - [x] 3.2 Store engagement_rate (0.0-1.0), conversions (int), performance_score (0-10)
  - [x] 3.3 Calculate running average performance across all usages
  - [x] 3.4 Create `PerformanceMetrics` dataclass with engagement_rate, conversions, score
  - [x] 3.5 Handle delayed performance updates (Epic 7 collects at 24h/48h/7d intervals)

- [x] Task 4: Implement asset performance scoring (AC: #2)
  - [x] 4.1 Create `calculate_performance_score()` method for individual usage
  - [x] 4.2 Weight factors: engagement_rate (40%), conversions (30%), reach (30%)
  - [x] 4.3 Calculate overall asset performance as average of all usage scores
  - [x] 4.4 Update asset record with latest performance score
  - [x] 4.5 Return `AssetPerformanceResult` with score and breakdown

- [x] Task 5: Implement asset query and suggestion (AC: #3)
  - [x] 5.1 Create `get_asset_usage_stats()` returning usage_count, avg_performance
  - [x] 5.2 Create `suggest_assets()` method returning sorted list by performance
  - [x] 5.3 Filter suggestions by content_type, topic, unused_days_threshold
  - [x] 5.4 Return `AssetSuggestion` with asset_id, score, usage_count, last_used
  - [x] 5.5 Implement `list_assets_by_performance()` for dashboard view

- [x] Task 6: Implement archive management (AC: #4)
  - [x] 6.1 Create `archive_asset()` method moving asset to Archive folder
  - [x] 6.2 Preserve full performance history on archive
  - [x] 6.3 Update Google Drive metadata with archive status
  - [x] 6.4 Maintain asset searchability via index
  - [x] 6.5 Create `ArchiveRecord` with original_path, archive_date, performance_summary

- [x] Task 7: Implement storage layer (AC: #1, #4)
  - [x] 7.1 Create `AssetUsageRepository` with Protocol pattern for persistence
  - [x] 7.2 Implement in-memory storage for MVP (interface for future DB)
  - [x] 7.3 Create index for fast asset lookup by id, topic, performance
  - [x] 7.4 Implement `sync_with_drive()` to reconcile with Google Drive state (via get_asset_by_post lookup)
  - [x] 7.5 Handle orphaned usage records (asset deleted from Drive) - raises ValueError

- [x] Task 8: Register AssetUsageTracker in team_spec.py (AC: #1)
  - [x] 8.1 Add `AssetUsageTracker` as RegisteredAgent with tier="generate"
  - [x] 8.2 Add capability tags: "asset_tracking", "usage_analytics", "performance_metrics"
  - [x] 8.3 Add `AssetUsageRepository` as service registration
  - [x] 8.4 Update `teams/dawo/generators/__init__.py` with exports

- [x] Task 9: Create unit tests
  - [x] 9.1 Test usage recording with valid asset and post
  - [x] 9.2 Test usage count increment on multiple uses
  - [x] 9.3 Test performance update with engagement metrics
  - [x] 9.4 Test performance score calculation weights
  - [x] 9.5 Test average performance across multiple usages
  - [x] 9.6 Test asset suggestion sorting by performance
  - [x] 9.7 Test archive with performance history preservation
  - [x] 9.8 Test concurrent usage recording

- [x] Task 10: Create integration tests
  - [x] 10.1 Test full usage lifecycle: create -> use -> performance -> archive
  - [x] 10.2 Test Google Drive integration with mock client
  - [x] 10.3 Test suggestion API with realistic asset pool
  - [x] 10.4 Test archive and searchability

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story creates the Asset Usage Tracker that completes the Epic 3 content generation pipeline. It tracks how generated assets (from Stories 3.4 Orshot and 3.5 Nano Banana) perform in published posts, enabling data-driven visual selection.

**Key Pattern:** This is a **generator** agent that produces asset analytics and suggestions. It integrates with Google Drive for storage and prepares for Epic 7 performance tracking integration.

### Existing Integration Interfaces (MUST USE)

**Source:** [integrations/google_drive/], [teams/dawo/generators/orshot_graphics/], [teams/dawo/generators/nano_banana/]

```python
# Google Drive Client (from Story 3.2)
from integrations.google_drive import (
    GoogleDriveClientProtocol,
    GoogleDriveClient,
    DriveFile,
    FolderPath,
)

# Asset generation outputs (from Stories 3.4, 3.5)
from teams.dawo.generators.orshot_graphics import (
    OrshotGraphicResult,  # Contains asset_id, file_path, quality_score
)
from teams.dawo.generators.nano_banana import (
    NanoBananaImageResult,  # Contains asset_id, file_path, quality_score
)

# Google Drive folder structure (from project-context.md)
ASSET_FOLDERS = {
    "generated": "DAWO.ECO/Assets/Generated/",     # Nano Banana AI images
    "orshot": "DAWO.ECO/Assets/Orshot/",           # Branded graphics
    "archive": "DAWO.ECO/Assets/Archive/",          # Used assets + performance
}

# Filename pattern: {date}_{type}_{topic}_{id}.{ext}
# Example: 2026-02-08_orshot_lionsmane_abc123.png
```

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
teams/dawo/generators/
├── __init__.py                       # Add asset_usage exports
├── asset_usage/                      # NEW package
│   ├── __init__.py                   # Package exports with __all__
│   ├── agent.py                      # AssetUsageTracker class
│   ├── schemas.py                    # All dataclasses
│   ├── repository.py                 # AssetUsageRepository (storage layer)
│   ├── scoring.py                    # Performance score calculation
│   └── constants.py                  # Weights, thresholds, folder paths
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

```python
# This agent does NOT need LLM - pure data tracking and calculation
# Registered as tier=TIER_GENERATE for consistency with other generators
tier=TIER_GENERATE

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - "claude-haiku", "claude-sonnet", "claude-opus"
```

### Schema Design

**Source:** Design based on AC requirements

```python
# schemas.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class Platform(Enum):
    """Publishing platform for asset usage."""

    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_REEL = "instagram_reel"


class AssetType(Enum):
    """Type of generated asset."""

    ORSHOT_GRAPHIC = "orshot_graphic"
    NANO_BANANA_IMAGE = "nano_banana_image"
    PRODUCT_PHOTO = "product_photo"


class AssetStatus(Enum):
    """Asset lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class UsageEvent:
    """Record of a single asset usage in a published post."""

    event_id: str
    asset_id: str
    post_id: str
    platform: Platform
    publish_date: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PerformanceMetrics:
    """Performance data for an asset usage."""

    engagement_rate: float          # 0.0-1.0 (likes+comments+shares / reach)
    conversions: int                # Number of attributed conversions
    reach: int                      # Total audience reached
    performance_score: float        # 0-10 calculated score
    collected_at: datetime
    collection_interval: str        # "24h", "48h", "7d"


@dataclass
class AssetPerformanceResult:
    """Calculated performance score for an asset."""

    asset_id: str
    overall_score: float            # 0-10 weighted average
    usage_count: int
    avg_engagement_rate: float
    total_conversions: int
    avg_reach: int
    score_breakdown: dict[str, float]  # engagement, conversions, reach scores


@dataclass
class AssetUsageRecord:
    """Complete usage history for an asset."""

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
    """Asset suggestion for content selection."""

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
    """Record of archived asset."""

    asset_id: str
    original_path: str
    archive_path: str
    archive_date: datetime
    performance_summary: AssetPerformanceResult
    total_usages: int
    metadata: dict[str, any]
```

### Performance Score Calculation

**Source:** Design based on AC #2

```python
# scoring.py

# Performance score weights (must sum to 1.0)
PERFORMANCE_WEIGHTS = {
    "engagement_rate": 0.40,    # Engagement is primary indicator
    "conversions": 0.30,        # Revenue impact
    "reach": 0.30,              # Visibility impact
}

def calculate_performance_score(metrics: PerformanceMetrics) -> float:
    """Calculate performance score from metrics.

    Args:
        metrics: PerformanceMetrics with engagement, conversions, reach

    Returns:
        Float score 0-10
    """
    # Normalize each metric to 0-10 scale
    # Engagement rate: 0.0-0.10 is typical, 0.05+ is good
    engagement_score = min(10.0, metrics.engagement_rate * 100)

    # Conversions: 0-10+ per post is good
    conversion_score = min(10.0, metrics.conversions)

    # Reach: 0-10000 typical, normalize
    reach_score = min(10.0, metrics.reach / 1000)

    # Weighted sum
    total = (
        engagement_score * PERFORMANCE_WEIGHTS["engagement_rate"] +
        conversion_score * PERFORMANCE_WEIGHTS["conversions"] +
        reach_score * PERFORMANCE_WEIGHTS["reach"]
    )

    return round(total, 1)
```

### AssetUsageTracker Agent Pattern

**Source:** [teams/dawo/generators/auto_publish_tagger/agent.py]

```python
# agent.py
from typing import Protocol, Optional
from datetime import datetime, timezone
import logging

from integrations.google_drive import GoogleDriveClientProtocol

from .schemas import (
    AssetUsageRecord,
    UsageEvent,
    PerformanceMetrics,
    AssetSuggestion,
    ArchiveRecord,
    Platform,
    AssetType,
    AssetStatus,
)
from .repository import AssetUsageRepository
from .scoring import calculate_performance_score, calculate_overall_performance

logger = logging.getLogger(__name__)


class AssetUsageTrackerProtocol(Protocol):
    """Protocol for asset usage tracker."""

    async def record_usage(
        self,
        asset_id: str,
        post_id: str,
        platform: Platform,
        publish_date: datetime,
    ) -> UsageEvent:
        """Record asset usage in a published post."""
        ...

    async def update_performance(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Update performance metrics for an asset usage."""
        ...

    async def get_usage_stats(
        self,
        asset_id: str,
    ) -> AssetUsageRecord:
        """Get usage statistics for an asset."""
        ...

    async def suggest_assets(
        self,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        limit: int = 10,
    ) -> list[AssetSuggestion]:
        """Get suggested assets sorted by performance."""
        ...

    async def archive_asset(
        self,
        asset_id: str,
    ) -> ArchiveRecord:
        """Archive asset while preserving performance history."""
        ...


class AssetUsageTracker:
    """Tracks asset usage and performance across published content.

    Records when assets are used in posts, collects performance metrics,
    calculates performance scores, and provides asset suggestions based
    on historical performance data.

    Uses 'generate' tier (defaults to configured model) for consistency.
    Configuration is received via dependency injection - NEVER loads config directly.
    """

    def __init__(
        self,
        drive_client: GoogleDriveClientProtocol,
        repository: AssetUsageRepository,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            drive_client: Google Drive client for asset operations
            repository: Storage layer for usage records
        """
        self._drive = drive_client
        self._repository = repository

    async def record_usage(
        self,
        asset_id: str,
        post_id: str,
        platform: Platform,
        publish_date: datetime,
    ) -> UsageEvent:
        """Record asset usage in a published post.

        Args:
            asset_id: Unique asset identifier
            post_id: Published post identifier
            platform: Publishing platform (instagram_feed, etc.)
            publish_date: When the post was published

        Returns:
            UsageEvent record
        """
        try:
            event = UsageEvent(
                event_id=f"{asset_id}_{post_id}",
                asset_id=asset_id,
                post_id=post_id,
                platform=platform,
                publish_date=publish_date,
            )

            await self._repository.add_usage_event(event)
            logger.info(
                "Recorded usage for asset %s in post %s on %s",
                asset_id, post_id, platform.value
            )

            return event

        except Exception as e:
            logger.error("Failed to record usage for asset %s: %s", asset_id, e)
            raise

    async def update_performance(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Update performance metrics for an asset usage.

        Called when Epic 7 collects post performance data at 24h/48h/7d intervals.

        Args:
            asset_id: Asset identifier
            post_id: Post identifier for the usage
            metrics: Performance metrics collected
        """
        try:
            # Calculate performance score from metrics
            metrics.performance_score = calculate_performance_score(metrics)

            await self._repository.add_performance_metrics(asset_id, post_id, metrics)

            # Recalculate overall asset performance
            record = await self._repository.get_asset(asset_id)
            if record:
                record.overall_performance = calculate_overall_performance(record)
                await self._repository.update_asset(record)

            logger.info(
                "Updated performance for asset %s (post %s): score=%.1f",
                asset_id, post_id, metrics.performance_score
            )

        except Exception as e:
            logger.error("Failed to update performance for asset %s: %s", asset_id, e)
            raise

    async def get_usage_stats(
        self,
        asset_id: str,
    ) -> AssetUsageRecord:
        """Get usage statistics for an asset.

        Args:
            asset_id: Asset identifier

        Returns:
            AssetUsageRecord with full usage history
        """
        record = await self._repository.get_asset(asset_id)
        if not record:
            raise ValueError(f"Asset not found: {asset_id}")
        return record

    async def suggest_assets(
        self,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        limit: int = 10,
    ) -> list[AssetSuggestion]:
        """Get suggested assets sorted by performance.

        High-performing assets are suggested first.

        Args:
            topic: Filter by content topic (optional)
            asset_type: Filter by asset type (optional)
            limit: Maximum suggestions to return

        Returns:
            List of AssetSuggestion sorted by performance score (descending)
        """
        try:
            assets = await self._repository.list_assets(
                status=AssetStatus.ACTIVE,
                topic=topic,
                asset_type=asset_type,
            )

            # Build suggestions with ranking
            suggestions = []
            for asset in assets:
                perf = asset.overall_performance
                score = perf.overall_score if perf else asset.original_quality_score
                usage_count = len(asset.usage_events)
                last_used = (
                    max(e.publish_date for e in asset.usage_events)
                    if asset.usage_events
                    else None
                )

                suggestions.append(AssetSuggestion(
                    asset_id=asset.asset_id,
                    file_path=asset.file_path,
                    asset_type=asset.asset_type,
                    topic=asset.topic,
                    performance_score=score,
                    usage_count=usage_count,
                    last_used=last_used,
                    quality_score=asset.original_quality_score,
                    rank=0,  # Set after sorting
                ))

            # Sort by performance score descending
            suggestions.sort(key=lambda s: s.performance_score, reverse=True)

            # Assign ranks and limit
            for i, suggestion in enumerate(suggestions[:limit]):
                suggestion.rank = i + 1

            return suggestions[:limit]

        except Exception as e:
            logger.error("Failed to get asset suggestions: %s", e)
            raise

    async def archive_asset(
        self,
        asset_id: str,
    ) -> ArchiveRecord:
        """Archive asset while preserving performance history.

        Moves asset to Archive folder in Google Drive, maintains full
        usage and performance history for analytics.

        Args:
            asset_id: Asset identifier

        Returns:
            ArchiveRecord with preserved history
        """
        try:
            record = await self._repository.get_asset(asset_id)
            if not record:
                raise ValueError(f"Asset not found: {asset_id}")

            # Move file in Google Drive
            archive_path = await self._drive.move_file(
                source_path=record.file_path,
                destination_folder="DAWO.ECO/Assets/Archive/",
            )

            # Update record status
            record.status = AssetStatus.ARCHIVED
            record.archived_at = datetime.now(timezone.utc)

            archive_record = ArchiveRecord(
                asset_id=asset_id,
                original_path=record.file_path,
                archive_path=archive_path,
                archive_date=record.archived_at,
                performance_summary=record.overall_performance,
                total_usages=len(record.usage_events),
                metadata={
                    "asset_type": record.asset_type.value,
                    "topic": record.topic,
                    "original_quality_score": record.original_quality_score,
                },
            )

            # Update file path and persist
            record.file_path = archive_path
            await self._repository.update_asset(record)

            logger.info(
                "Archived asset %s with %d usages, score=%.1f",
                asset_id,
                len(record.usage_events),
                record.overall_performance.overall_score if record.overall_performance else 0,
            )

            return archive_record

        except Exception as e:
            logger.error("Failed to archive asset %s: %s", asset_id, e)
            raise
```

### Repository Pattern

**Source:** [teams/dawo/generators/auto_publish_tagger/statistics.py]

```python
# repository.py
from typing import Protocol, Optional
from datetime import datetime, timezone
import logging

from .schemas import (
    AssetUsageRecord,
    UsageEvent,
    PerformanceMetrics,
    AssetType,
    AssetStatus,
)

logger = logging.getLogger(__name__)


class AssetUsageRepositoryProtocol(Protocol):
    """Protocol for asset usage persistence."""

    async def create_asset(self, record: AssetUsageRecord) -> None:
        """Create a new asset record."""
        ...

    async def get_asset(self, asset_id: str) -> Optional[AssetUsageRecord]:
        """Get asset by ID."""
        ...

    async def update_asset(self, record: AssetUsageRecord) -> None:
        """Update asset record."""
        ...

    async def add_usage_event(self, event: UsageEvent) -> None:
        """Add usage event to asset."""
        ...

    async def add_performance_metrics(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Add performance metrics for usage."""
        ...

    async def list_assets(
        self,
        status: Optional[AssetStatus] = None,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
    ) -> list[AssetUsageRecord]:
        """List assets with optional filters."""
        ...


class AssetUsageRepository:
    """In-memory repository for asset usage records.

    MVP implementation stores data in memory. Future enhancement will
    persist to database via the same Protocol interface.
    """

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._assets: dict[str, AssetUsageRecord] = {}

    async def create_asset(self, record: AssetUsageRecord) -> None:
        """Create a new asset record."""
        self._assets[record.asset_id] = record
        logger.info("Created asset record: %s", record.asset_id)

    async def get_asset(self, asset_id: str) -> Optional[AssetUsageRecord]:
        """Get asset by ID."""
        return self._assets.get(asset_id)

    async def update_asset(self, record: AssetUsageRecord) -> None:
        """Update asset record."""
        self._assets[record.asset_id] = record
        logger.debug("Updated asset record: %s", record.asset_id)

    async def add_usage_event(self, event: UsageEvent) -> None:
        """Add usage event to asset."""
        record = await self.get_asset(event.asset_id)
        if not record:
            raise ValueError(f"Asset not found: {event.asset_id}")
        record.usage_events.append(event)

    async def add_performance_metrics(
        self,
        asset_id: str,
        post_id: str,
        metrics: PerformanceMetrics,
    ) -> None:
        """Add performance metrics for usage."""
        record = await self.get_asset(asset_id)
        if not record:
            raise ValueError(f"Asset not found: {asset_id}")
        record.performance_history.append(metrics)

    async def list_assets(
        self,
        status: Optional[AssetStatus] = None,
        topic: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
    ) -> list[AssetUsageRecord]:
        """List assets with optional filters."""
        results = list(self._assets.values())

        if status:
            results = [r for r in results if r.status == status]
        if topic:
            results = [r for r in results if r.topic == topic]
        if asset_type:
            results = [r for r in results if r.asset_type == asset_type]

        return results
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-8-auto-publish-eligibility-tagging.md], [3-7-content-quality-scoring.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export AssetUsageTracker, Protocol, all schemas |
| Config injection pattern | Accept drive_client, repository via constructor |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all errors with `%` formatting before raising |
| F-string logging anti-pattern | Use `%` formatting: `logger.error("Failed: %s", e)` |
| Protocol pattern for testability | Create Protocol for tracker and repository |
| In-memory + Protocol for MVP | Repository uses in-memory, interface supports future DB |
| Boundary value testing | Test empty usage, single usage, many usages |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER load Google Drive credentials directly** - Accept client via injection
2. **NEVER hardcode folder paths** - Use constants.py
3. **NEVER mutate input data** - Create new records
4. **NEVER swallow exceptions without logging** - Log all errors
5. **NEVER bypass repository layer** - All persistence through repository

### Integration Points

**Source:** [epics.md#Epic-3], [architecture.md#Data-Flow]

```python
# Asset Usage Tracker integrates into content publishing pipeline:

# 1. When content is generated (Story 3.4 or 3.5)
orshot_result = await orshot_generator.generate(request)
# OR
nano_result = await nano_banana.generate(request)

# 2. Register asset in tracker (this story)
await repository.create_asset(
    AssetUsageRecord(
        asset_id=orshot_result.asset_id,
        asset_type=AssetType.ORSHOT_GRAPHIC,
        file_path=orshot_result.file_path,
        original_quality_score=orshot_result.quality_score,
        topic=request.topic,
    )
)

# 3. When post is published (Epic 4)
await usage_tracker.record_usage(
    asset_id=asset_id,
    post_id=instagram_post_id,
    platform=Platform.INSTAGRAM_FEED,
    publish_date=publish_time,
)

# 4. When performance data collected (Epic 7 - 24h/48h/7d intervals)
await usage_tracker.update_performance(
    asset_id=asset_id,
    post_id=post_id,
    metrics=PerformanceMetrics(
        engagement_rate=0.05,
        conversions=3,
        reach=2340,
        collected_at=datetime.now(timezone.utc),
        collection_interval="24h",
    ),
)

# 5. When content team needs visuals
suggestions = await usage_tracker.suggest_assets(
    topic="lions_mane",
    asset_type=AssetType.ORSHOT_GRAPHIC,
    limit=5,
)
# Returns: sorted by performance_score descending
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.asset_usage import (
    AssetUsageTracker,
    AssetUsageTrackerProtocol,
    AssetUsageRepository,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="asset_usage_tracker",
        agent_class=AssetUsageTracker,
        capabilities=["asset_tracking", "usage_analytics", "performance_metrics"],
        tier=TIER_GENERATE,  # For future LLM enhancements
    ),
]

SERVICES: List[RegisteredService] = [
    # ... existing services ...
    RegisteredService(
        name="asset_usage_repository",
        service_class=AssetUsageRepository,
    ),
]
```

### Test Fixtures

**Source:** [tests/teams/dawo/generators/test_auto_publish_tagger/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_asset_usage/conftest.py
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from teams.dawo.generators.asset_usage import (
    AssetUsageTracker,
    AssetUsageRepository,
    AssetUsageRecord,
    UsageEvent,
    PerformanceMetrics,
    Platform,
    AssetType,
    AssetStatus,
)


@pytest.fixture
def mock_drive_client():
    """Mock Google Drive client."""
    client = AsyncMock()
    client.move_file.return_value = "DAWO.ECO/Assets/Archive/test_asset.png"
    return client


@pytest.fixture
def repository():
    """Fresh repository for each test."""
    return AssetUsageRepository()


@pytest.fixture
def tracker(mock_drive_client, repository):
    """AssetUsageTracker with mocked dependencies."""
    return AssetUsageTracker(
        drive_client=mock_drive_client,
        repository=repository,
    )


@pytest.fixture
def sample_asset_record():
    """Sample asset for testing."""
    return AssetUsageRecord(
        asset_id="asset-001",
        asset_type=AssetType.ORSHOT_GRAPHIC,
        file_path="DAWO.ECO/Assets/Orshot/2026-02-08_orshot_lionsmane_001.png",
        original_quality_score=8.5,
        topic="lions_mane",
    )


@pytest.fixture
def sample_usage_event():
    """Sample usage event."""
    return UsageEvent(
        event_id="asset-001_post-abc123",
        asset_id="asset-001",
        post_id="post-abc123",
        platform=Platform.INSTAGRAM_FEED,
        publish_date=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_performance_metrics():
    """Sample performance metrics."""
    return PerformanceMetrics(
        engagement_rate=0.05,
        conversions=3,
        reach=2340,
        performance_score=0.0,  # Will be calculated
        collected_at=datetime.now(timezone.utc),
        collection_interval="24h",
    )
```

### Edge Cases to Handle

1. **No usage history**: Asset never used - return original quality score for suggestions
2. **Multiple performance updates**: Handle 24h/48h/7d updates for same usage
3. **Concurrent usage**: Same asset used in multiple posts simultaneously
4. **Orphaned records**: Asset deleted from Drive but usage records exist
5. **Archive with no performance**: Archive asset that was never used
6. **Zero metrics**: Handle engagement_rate=0, conversions=0, reach=0

### Project Structure Notes

- **Location**: `teams/dawo/generators/asset_usage/` (new package)
- **Dependencies**: GoogleDriveClient (Story 3.2), Orshot (Story 3.4), Nano Banana (Story 3.5)
- **Used by**: Content Team orchestrator, Approval Manager (Epic 4), Analytics (Epic 7)
- **LLM Tier**: generate (for future enhancements, currently pure logic)
- **Persistence**: In-memory (MVP), future: database-backed via Protocol pattern
- **Google Drive folders**: Generated/, Orshot/, Archive/

### References

- [Source: epics.md#Story-3.9] - Original story requirements (FR50)
- [Source: architecture.md#Agent-Package-Structure] - Package patterns
- [Source: project-context.md#LLM-Tier-Assignment] - Tier system
- [Source: project-context.md#Agent-Registration] - Registration pattern
- [Source: project-context.md#Asset-Storage-Folders] - Google Drive structure
- [Source: integrations/google_drive/] - Google Drive client integration
- [Source: teams/dawo/generators/orshot_graphics/] - Orshot asset generation
- [Source: teams/dawo/generators/nano_banana/] - Nano Banana asset generation
- [Source: 3-8-auto-publish-eligibility-tagging.md] - Previous story patterns
- [Source: 3-7-content-quality-scoring.md] - Scoring patterns

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - all tests pass without issues.

### Completion Notes List

- Created `teams/dawo/generators/asset_usage/` package with 6 modules: agent.py, schemas.py, repository.py, scoring.py, constants.py, __init__.py
- Implemented AssetUsageTracker with Protocol pattern for dependency injection
- Implemented AssetUsageRepository with in-memory storage for MVP (Protocol-based for future DB migration)
- Created 10 dataclasses/enums: UsageEvent, PerformanceMetrics, AssetUsageRecord, AssetPerformanceResult, AssetSuggestion, ArchiveRecord, Platform, AssetType, AssetStatus
- Performance scoring uses weighted formula: 40% engagement_rate, 30% conversions, 30% reach
- All scores normalized to 0-10 scale with caps for each component
- Integrated with existing GoogleDriveClientProtocol.move_to_archive() method
- Added register_asset() method for integration with Orshot (3.4) and Nano Banana (3.5) generators
- Registered agent in team_spec.py with tier=TIER_GENERATE and capabilities: asset_tracking, usage_analytics, performance_metrics
- All 88 unit and integration tests pass (after code review fixes)

### Code Review Fixes Applied (2026-02-08)

| Issue | Fix Applied |
|-------|-------------|
| Task 5.3 incomplete: missing `unused_days_threshold` | Added parameter to `suggest_assets()` with filtering logic |
| Task 7.4 incomplete: missing `sync_with_drive()` | Implemented method in repository with orphan detection |
| Bug: `archive_asset()` original_path captured after modification | Captured `original_file_path` before modifying `record.file_path` |
| No validation on `engagement_rate` bounds | Added `__post_init__` validation to PerformanceMetrics (0.0-1.0 range) |
| `DEFAULT_UNUSED_DAYS_THRESHOLD` not exported | Added to `__init__.py` exports |
| Missing tests for new features | Added 11 new tests for threshold filtering, sync, and validation |

### File List

**New Files:**
- teams/dawo/generators/asset_usage/__init__.py
- teams/dawo/generators/asset_usage/agent.py
- teams/dawo/generators/asset_usage/schemas.py
- teams/dawo/generators/asset_usage/repository.py
- teams/dawo/generators/asset_usage/scoring.py
- teams/dawo/generators/asset_usage/constants.py
- tests/teams/dawo/generators/test_asset_usage/__init__.py
- tests/teams/dawo/generators/test_asset_usage/conftest.py
- tests/teams/dawo/generators/test_asset_usage/test_schemas.py
- tests/teams/dawo/generators/test_asset_usage/test_scoring.py
- tests/teams/dawo/generators/test_asset_usage/test_repository.py
- tests/teams/dawo/generators/test_asset_usage/test_agent.py
- tests/teams/dawo/generators/test_asset_usage/test_integration.py

**Modified Files:**
- teams/dawo/team_spec.py (added AssetUsageTracker agent and AssetUsageRepository service)
- teams/dawo/generators/__init__.py (added asset_usage exports)
- teams/dawo/__init__.py (updated exports)
- integrations/__init__.py (updated exports)
- config/dawo_brand_profile.json (updated configuration)
- _bmad-output/project-context.md (updated context)
- _bmad-output/implementation-artifacts/sprint-status.yaml (status: in-progress → review)
- _bmad-output/implementation-artifacts/3-9-asset-usage-tracking.md (code review fixes)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-08 | Implemented Asset Usage Tracker with full test coverage (77 tests) | Claude Opus 4.5 |
| 2026-02-08 | Code review fixes: added missing features, fixed bugs, expanded tests (88 tests) | Claude Opus 4.5 |

