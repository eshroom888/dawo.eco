"""Content Quality Scorer - Unified quality scoring for content items.

This module provides comprehensive quality scoring for content before
it enters the approval queue. Aggregates scores from compliance,
brand voice, visual quality, platform optimization, engagement prediction,
and authenticity analysis.

Uses the 'generate' tier for AI detectability analysis.

Exports:
    ContentQualityScorer: Main scorer agent class
    ContentQualityScorerProtocol: Protocol for dependency injection
    LLMClientProtocol: Protocol for LLM client interface
    QualityScoreRequest: Input dataclass for scoring
    QualityScoreResult: Output dataclass with total and component scores
    ComponentScore: Individual component scoring result
    ContentType: Content format enum (feed, story, reel)
    AuthenticityResult: AI detectability analysis result
    PlatformOptimizationResult: Platform-specific optimization check result
    EngagementPrediction: Engagement prediction based on historical data
    DEFAULT_WEIGHTS: Default scoring weight configuration
    validate_weights: Weight validation utility

Scorer Classes (individual components):
    ComplianceScorer: EU compliance status scoring
    BrandVoiceScorer: Brand voice alignment scoring
    VisualQualityScorer: Visual quality scoring
    PlatformOptimizationScorer: Platform-specific optimization
    EngagementPredictionScorer: Historical engagement prediction
    AuthenticityScorer: AI detectability analysis
"""

from .agent import (
    ContentQualityScorer,
    ContentQualityScorerProtocol,
)
from .schemas import (
    QualityScoreRequest,
    QualityScoreResult,
    ComponentScore,
    ContentType,
    AuthenticityResult,
    PlatformOptimizationResult,
    EngagementPrediction,
    DEFAULT_WEIGHTS,
    validate_weights,
)
from .scorers import (
    LLMClientProtocol,
    ComplianceScorer,
    ComplianceScorerConfig,
    BrandVoiceScorer,
    BrandVoiceScorerConfig,
    VisualQualityScorer,
    VisualQualityScorerConfig,
    PlatformOptimizationScorer,
    PlatformScorerConfig,
    EngagementPredictionScorer,
    EngagementScorerConfig,
    AuthenticityScorer,
    AuthenticityScorerConfig,
)

__all__: list[str] = [
    # Core agent
    "ContentQualityScorer",
    # Protocols
    "ContentQualityScorerProtocol",
    "LLMClientProtocol",
    # Data classes
    "QualityScoreRequest",
    "QualityScoreResult",
    "ComponentScore",
    # Enums
    "ContentType",
    # Result types
    "AuthenticityResult",
    "PlatformOptimizationResult",
    "EngagementPrediction",
    # Constants and utilities
    "DEFAULT_WEIGHTS",
    "validate_weights",
    # Scorer classes
    "ComplianceScorer",
    "ComplianceScorerConfig",
    "BrandVoiceScorer",
    "BrandVoiceScorerConfig",
    "VisualQualityScorer",
    "VisualQualityScorerConfig",
    "PlatformOptimizationScorer",
    "PlatformScorerConfig",
    "EngagementPredictionScorer",
    "EngagementScorerConfig",
    "AuthenticityScorer",
    "AuthenticityScorerConfig",
]
