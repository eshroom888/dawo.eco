"""DAWO Validator agents - Compliance and quality.

Validator agents ensure content meets requirements:
- EU Health Claims compliance (EC 1924/2006)
- Brand voice consistency
- Research compliance validation (Story 2.8)

All validators operate at the 'generate' tier (defaults to sonnet for accurate judgment).

LLMClient Protocol:
    Both EU Compliance and Brand Voice validators use an identical LLMClient Protocol
    for LLM integration. The LLMClient exported here (from eu_compliance) is compatible
    with both validators. Any client implementing this protocol can be used:

    ```python
    class LLMClient(Protocol):
        async def generate(self, prompt: str, system: Optional[str] = None) -> str: ...
    ```
"""

from .eu_compliance import (
    EUComplianceChecker,
    ComplianceStatus,
    OverallStatus,
    ComplianceResult,
    ContentComplianceCheck,
    NovelFoodCheck,
    RegulationRef,
    LLMClient,
    ComplianceScoring,
)

from .brand_voice import (
    BrandVoiceValidator,
    ValidationStatus,
    IssueType,
    BrandIssue,
    BrandValidationResult,
    ScoringWeights,
    BrandProfile,
    TonePillar,
    validate_profile,
)

from .research_compliance import (
    ResearchComplianceValidator,
    ValidatedResearch,
    CitationInfo,
    ComplianceValidationResult,
    ValidationContext,
    ValidationStats,
    ValidationError,
)

__all__: list[str] = [
    # EU Compliance exports
    "EUComplianceChecker",
    "ComplianceStatus",
    "OverallStatus",
    "ComplianceResult",
    "ContentComplianceCheck",
    "NovelFoodCheck",
    "RegulationRef",
    "ComplianceScoring",
    # Shared protocol (identical in both modules, exported from eu_compliance)
    "LLMClient",
    # Brand Voice exports
    "BrandVoiceValidator",
    "ValidationStatus",
    "IssueType",
    "BrandIssue",
    "BrandValidationResult",
    "ScoringWeights",
    # Brand Profile configuration types
    "BrandProfile",
    "TonePillar",
    "validate_profile",
    # Research Compliance exports (Story 2.8)
    "ResearchComplianceValidator",
    "ValidatedResearch",
    "CitationInfo",
    "ComplianceValidationResult",
    "ValidationContext",
    "ValidationStats",
    "ValidationError",
]
