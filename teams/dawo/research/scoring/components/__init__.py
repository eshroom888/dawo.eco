"""Scoring component implementations.

Each component calculates a 0-10 score for a specific dimension:
- RelevanceScorer: Product and theme keyword matching
- RecencyScorer: Time decay (30-day window)
- SourceQualityScorer: Source tier and study type bonuses
- EngagementScorer: Normalized engagement metrics
- ComplianceAdjuster: Compliance status adjustments
"""

from .relevance import (
    RelevanceScorer,
    RelevanceConfig,
    PRIMARY_KEYWORD_BONUS,
    SECONDARY_KEYWORD_BONUS,
    MAX_PRIMARY_BONUS,
    MAX_SECONDARY_BONUS,
    MAX_SCORE,
)
from .recency import (
    RecencyScorer,
    RecencyConfig,
    RECENCY_DECAY_DAYS,
    MAX_RECENCY_SCORE,
    MIN_RECENCY_SCORE,
)
from .source_quality import (
    SourceQualityScorer,
    SourceQualityConfig,
    SOURCE_TIER_SCORES,
    PUBMED_STUDY_BONUSES,
)
from .engagement import (
    EngagementScorer,
    EngagementConfig,
    DEFAULT_ENGAGEMENT_SCORE,
)
from .compliance import (
    ComplianceAdjuster,
    ComplianceAdjustment,
    COMPLIANT_BONUS,
)

__all__ = [
    # Relevance
    "RelevanceScorer",
    "RelevanceConfig",
    "PRIMARY_KEYWORD_BONUS",
    "SECONDARY_KEYWORD_BONUS",
    "MAX_PRIMARY_BONUS",
    "MAX_SECONDARY_BONUS",
    "MAX_SCORE",
    # Recency
    "RecencyScorer",
    "RecencyConfig",
    "RECENCY_DECAY_DAYS",
    "MAX_RECENCY_SCORE",
    "MIN_RECENCY_SCORE",
    # Source Quality
    "SourceQualityScorer",
    "SourceQualityConfig",
    "SOURCE_TIER_SCORES",
    "PUBMED_STUDY_BONUSES",
    # Engagement
    "EngagementScorer",
    "EngagementConfig",
    "DEFAULT_ENGAGEMENT_SCORE",
    # Compliance
    "ComplianceAdjuster",
    "ComplianceAdjustment",
    "COMPLIANT_BONUS",
]
