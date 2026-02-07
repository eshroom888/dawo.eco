"""Research Compliance Validator for DAWO research intelligence pipeline.

Validates research items for EU compliance before pool entry.
Bridges EU Compliance Checker (Story 1.2) with all scanner validators.

This module is a SHARED COMPONENT used by all research scanners
(Reddit, YouTube, Instagram, News, PubMed) for consistent EU compliance checking.

Key Features:
    - Scientific citation detection (DOI, PMID, scientific URLs)
    - Source-specific validation rules (PubMed vs social sources)
    - Batch validation with partial failure handling
    - Citation-aware status adjustment

Exports:
    ResearchComplianceValidator: Main validator class
    ValidatedResearch: Validated research item output
    CitationInfo: Citation detection result
    ComplianceValidationResult: Full validation result
    ValidationContext: Validation operation context
    ValidationStats: Batch validation statistics
    ValidationError: Validation exception

Usage:
    from teams.dawo.validators.research_compliance import (
        ResearchComplianceValidator,
        ValidatedResearch,
    )

    # Create validator with injected EU Compliance Checker
    validator = ResearchComplianceValidator(eu_compliance_checker)

    # Validate single item
    result = await validator.validate(transformed_research_item)

    # Validate batch
    results = await validator.validate_batch(items)
"""

from .validator import (
    ResearchComplianceValidator,
    ValidatedResearch,
)
from .schemas import (
    CitationInfo,
    ComplianceValidationResult,
    ValidationContext,
    ValidationStats,
    ValidationError,
)

__all__: list[str] = [
    # Main validator
    "ResearchComplianceValidator",
    # Output type
    "ValidatedResearch",
    # Schemas
    "CitationInfo",
    "ComplianceValidationResult",
    "ValidationContext",
    "ValidationStats",
    # Exceptions
    "ValidationError",
]
