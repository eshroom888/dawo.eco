"""Research Item Scoring Engine for DAWO research intelligence pipeline.

This module provides composite scoring for research items based on:
- Relevance to DAWO products (mushroom types, wellness themes)
- Recency (newer = higher, decay over 30 days)
- Source quality (peer-reviewed > social media)
- Engagement indicators (upvotes, views, citations)
- Compliance status (COMPLIANT gets +1, WARNING neutral, REJECTED = 0)

Components:
    - ResearchItemScorer: Main composite scoring engine
    - ScoringConfig: Configuration with component weights
    - ScoringWeights: Weight values for each scoring component
    - ScoringResult: Result dataclass with score breakdown
    - ComponentScore: Individual component score result

Usage:
    from teams.dawo.research.scoring import (
        ResearchItemScorer,
        ScoringConfig,
        ScoringResult,
    )
"""

from .config import (
    ScoringConfig,
    ScoringWeights,
    DEFAULT_RELEVANCE_WEIGHT,
    DEFAULT_RECENCY_WEIGHT,
    DEFAULT_SOURCE_QUALITY_WEIGHT,
    DEFAULT_ENGAGEMENT_WEIGHT,
    DEFAULT_COMPLIANCE_WEIGHT,
)
from .schemas import (
    ScoringResult,
    ComponentScore,
    ScoringResultResponse,
    ComponentScoreResponse,
)
from .scorer import ResearchItemScorer
from .components import (
    RelevanceScorer,
    RelevanceConfig,
    RecencyScorer,
    RecencyConfig,
    SourceQualityScorer,
    SourceQualityConfig,
    EngagementScorer,
    EngagementConfig,
    ComplianceAdjuster,
    ComplianceAdjustment,
)
from .service import ResearchScoringService

__all__ = [
    # Main Scorer
    "ResearchItemScorer",
    # Service
    "ResearchScoringService",
    # Config
    "ScoringConfig",
    "ScoringWeights",
    # Schemas (dataclasses)
    "ScoringResult",
    "ComponentScore",
    # Schemas (Pydantic API responses)
    "ScoringResultResponse",
    "ComponentScoreResponse",
    # Components
    "RelevanceScorer",
    "RelevanceConfig",
    "RecencyScorer",
    "RecencyConfig",
    "SourceQualityScorer",
    "SourceQualityConfig",
    "EngagementScorer",
    "EngagementConfig",
    "ComplianceAdjuster",
    "ComplianceAdjustment",
    # Constants
    "DEFAULT_RELEVANCE_WEIGHT",
    "DEFAULT_RECENCY_WEIGHT",
    "DEFAULT_SOURCE_QUALITY_WEIGHT",
    "DEFAULT_ENGAGEMENT_WEIGHT",
    "DEFAULT_COMPLIANCE_WEIGHT",
]
