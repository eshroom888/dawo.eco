"""Brand Voice Validator - DAWO brand voice and authenticity validator.

This module provides brand voice validation for DAWO content.
All content should pass brand validation to ensure consistent voice
and authenticity before publishing.

Exports:
    BrandVoiceValidator: Main validator agent class
    ValidationStatus: Validation status enum (PASS, NEEDS_REVISION, FAIL)
    IssueType: Type of brand issue enum
    BrandIssue: Individual issue result dataclass
    BrandValidationResult: Full validation result dataclass
    LLMClient: Protocol for LLM client interface
    ScoringWeights: Constants for brand score calculations
    BrandProfile: Typed brand profile configuration (from profile.py)
    TonePillar: Single tone pillar configuration (from profile.py)
    validate_profile: Profile validation utility (from profile.py)
"""

from .agent import (
    BrandVoiceValidator,
    ValidationStatus,
    IssueType,
    BrandIssue,
    BrandValidationResult,
    LLMClient,
    ScoringWeights,
)

from .profile import (
    BrandProfile,
    TonePillar,
    validate_profile,
)

__all__: list[str] = [
    # Core validator
    "BrandVoiceValidator",
    # Result types
    "ValidationStatus",
    "IssueType",
    "BrandIssue",
    "BrandValidationResult",
    # Protocols and utilities
    "LLMClient",
    "ScoringWeights",
    # Profile configuration types
    "BrandProfile",
    "TonePillar",
    "validate_profile",
]
