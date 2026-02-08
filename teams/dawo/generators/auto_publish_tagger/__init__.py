"""Auto-Publish Eligibility Tagger - Tags content for potential auto-publishing.

This module provides eligibility tagging for content based on quality score
and EU compliance status. Content meeting criteria (score >= 9, COMPLIANT)
is tagged as WOULD_AUTO_PUBLISH for operator visibility.

MVP mode: All tags are informational only - human approval still required.

Uses the 'generate' tier for future LLM enhancements (currently pure logic).

Exports:
    AutoPublishTagger: Main tagger agent class
    AutoPublishTaggerProtocol: Protocol for dependency injection
    AutoPublishStatisticsService: Service for tracking tagging accuracy
    TaggingRequest: Input dataclass for tagging
    TaggingResult: Output dataclass with tag and display message
    EligibilityResult: Eligibility check result
    ApprovalOutcome: Record of approval decision
    AccuracyStats: Accuracy statistics result
    AutoPublishConfig: Toggle configuration for auto-publish
    AutoPublishConfigProtocol: Protocol for config dependency injection
    AutoPublishTag: Enum of possible tags
    DEFAULT_THRESHOLD: Default quality score threshold (9.0)
    ELIGIBLE_MESSAGE: Display message for eligible content
    REQUIRED_COMPLIANCE_STATUS: Required status for eligibility
"""

from .agent import (
    AutoPublishTagger,
    AutoPublishTaggerProtocol,
)
from .schemas import (
    TaggingRequest,
    TaggingResult,
    EligibilityResult,
    ApprovalOutcome,
    AccuracyStats,
    AutoPublishConfig,
    AutoPublishConfigProtocol,
    AutoPublishTag,
)
from .statistics import (
    AutoPublishStatisticsService,
)
from .constants import (
    DEFAULT_THRESHOLD,
    ELIGIBLE_MESSAGE,
    REQUIRED_COMPLIANCE_STATUS,
)

__all__: list[str] = [
    # Core agent
    "AutoPublishTagger",
    # Protocols
    "AutoPublishTaggerProtocol",
    "AutoPublishConfigProtocol",
    # Services
    "AutoPublishStatisticsService",
    # Data classes
    "TaggingRequest",
    "TaggingResult",
    "EligibilityResult",
    "ApprovalOutcome",
    "AccuracyStats",
    "AutoPublishConfig",
    # Enums
    "AutoPublishTag",
    # Constants
    "DEFAULT_THRESHOLD",
    "ELIGIBLE_MESSAGE",
    "REQUIRED_COMPLIANCE_STATUS",
]
