"""Asset Usage Tracking - Tracks asset usage and performance across published content.

This module provides asset usage tracking with performance correlation per FR50.
Records when assets are used in posts, collects performance metrics,
calculates performance scores, and provides asset suggestions based
on historical performance data.

Uses the 'generate' tier for future LLM enhancements (currently pure logic).

Exports:
    AssetUsageTracker: Main tracker class
    AssetUsageTrackerProtocol: Protocol for dependency injection
    AssetUsageRepository: Storage layer for usage records
    AssetUsageRepositoryProtocol: Protocol for repository
    UsageEvent: Record of single asset usage
    PerformanceMetrics: Performance data for asset usage
    AssetUsageRecord: Complete usage history for an asset
    AssetPerformanceResult: Calculated performance score
    AssetSuggestion: Asset suggestion for content selection
    ArchiveRecord: Record of archived asset
    Platform: Publishing platform enum
    AssetType: Type of generated asset enum
    AssetStatus: Asset lifecycle status enum
    calculate_performance_score: Score calculation function
    calculate_overall_performance: Overall asset performance calculation
    PERFORMANCE_WEIGHTS: Score weight configuration
    ASSET_FOLDERS: Google Drive folder paths
    DEFAULT_UNUSED_DAYS_THRESHOLD: Default threshold for unused asset filtering
"""

from .agent import (
    AssetUsageTracker,
    AssetUsageTrackerProtocol,
)
from .schemas import (
    UsageEvent,
    PerformanceMetrics,
    AssetUsageRecord,
    AssetPerformanceResult,
    AssetSuggestion,
    ArchiveRecord,
    Platform,
    AssetType,
    AssetStatus,
)
from .repository import (
    AssetUsageRepository,
    AssetUsageRepositoryProtocol,
)
from .scoring import (
    calculate_performance_score,
    calculate_overall_performance,
    PERFORMANCE_WEIGHTS,
)
from .constants import (
    ASSET_FOLDERS,
    DEFAULT_UNUSED_DAYS_THRESHOLD,
)

__all__: list[str] = [
    # Core agent
    "AssetUsageTracker",
    # Protocols
    "AssetUsageTrackerProtocol",
    "AssetUsageRepositoryProtocol",
    # Repository
    "AssetUsageRepository",
    # Data classes
    "UsageEvent",
    "PerformanceMetrics",
    "AssetUsageRecord",
    "AssetPerformanceResult",
    "AssetSuggestion",
    "ArchiveRecord",
    # Enums
    "Platform",
    "AssetType",
    "AssetStatus",
    # Functions
    "calculate_performance_score",
    "calculate_overall_performance",
    # Constants
    "PERFORMANCE_WEIGHTS",
    "ASSET_FOLDERS",
    "DEFAULT_UNUSED_DAYS_THRESHOLD",
]
