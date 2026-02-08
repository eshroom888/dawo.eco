"""Individual scoring components for Content Quality Scorer.

These scorers handle specific aspects of quality evaluation:
- ComplianceScorer: EU compliance status scoring
- BrandVoiceScorer: Brand voice alignment scoring
- VisualQualityScorer: Visual quality scoring
- PlatformOptimizationScorer: Platform-specific optimization
- EngagementPredictionScorer: Historical engagement prediction
- AuthenticityScorer: AI detectability analysis

Each scorer follows the single responsibility principle and can be
tested independently via mock injection.
"""

from .compliance import (
    ComplianceScorer,
    ComplianceScorerConfig,
    ComplianceCheckerProtocol,
)
from .brand_voice import (
    BrandVoiceScorer,
    BrandVoiceScorerConfig,
    BrandValidatorProtocol,
)
from .visual_quality import (
    VisualQualityScorer,
    VisualQualityScorerConfig,
)
from .platform import (
    PlatformOptimizationScorer,
    PlatformScorerConfig,
    PLATFORM_RULES,
    CTA_PHRASES,
)
from .engagement import (
    EngagementPredictionScorer,
    EngagementScorerConfig,
    HistoricalDataProviderProtocol,
    SOURCE_TYPE_SCORES,
)
from .authenticity import (
    AuthenticityScorer,
    AuthenticityScorerConfig,
    LLMClientProtocol,
    AI_PATTERN_MARKERS,
)

__all__ = [
    # Compliance
    "ComplianceScorer",
    "ComplianceScorerConfig",
    "ComplianceCheckerProtocol",
    # Brand Voice
    "BrandVoiceScorer",
    "BrandVoiceScorerConfig",
    "BrandValidatorProtocol",
    # Visual Quality
    "VisualQualityScorer",
    "VisualQualityScorerConfig",
    # Platform Optimization
    "PlatformOptimizationScorer",
    "PlatformScorerConfig",
    "PLATFORM_RULES",
    "CTA_PHRASES",
    # Engagement Prediction
    "EngagementPredictionScorer",
    "EngagementScorerConfig",
    "HistoricalDataProviderProtocol",
    "SOURCE_TYPE_SCORES",
    # Authenticity
    "AuthenticityScorer",
    "AuthenticityScorerConfig",
    "LLMClientProtocol",
    "AI_PATTERN_MARKERS",
]
