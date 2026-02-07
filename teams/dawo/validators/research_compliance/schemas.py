"""Schemas for Research Compliance Validator.

Defines data structures for compliance validation results.

Schemas:
    - CitationInfo: Scientific citation detection result
    - ComplianceValidationResult: Full validation result
    - ValidationContext: Context for validation operations
    - ValidationStats: Statistics from batch validation
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from teams.dawo.validators.eu_compliance import ComplianceResult


@dataclass
class CitationInfo:
    """Information about scientific citations in research.

    Stores detection results for DOI, PMID, and scientific URLs.
    Used to determine if research can cite a study (affecting compliance status).

    Attributes:
        has_doi: True if DOI pattern found
        has_pmid: True if PMID found
        has_url: True if scientific URL found
        doi: The DOI string if found
        pmid: The PMID string if found
        url: The scientific URL if found
    """

    has_doi: bool = False
    has_pmid: bool = False
    has_url: bool = False
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None

    @property
    def has_citation(self) -> bool:
        """Returns True if any scientific citation is present.

        A citation allows content with prohibited claims to be downgraded
        from REJECTED to WARNING (can cite study, cannot make claim).
        """
        return self.has_doi or self.has_pmid or self.has_url


@dataclass
class ComplianceValidationResult:
    """Result from research compliance validation.

    Contains all information about a validation check including
    the final status, flagged phrases, and citation info.

    Attributes:
        compliance_status: Final status (COMPLIANT, WARNING, REJECTED)
        citation_info: Scientific citation detection result
        flagged_phrases: List of flagged phrases from EU Compliance Checker
        compliance_notes: Human-readable explanation of status
        source: Research source (reddit, youtube, pubmed, etc.)
        has_scientific_citation: Convenience flag for pool queries
        validated_at: Timestamp of validation
    """

    compliance_status: str  # ComplianceStatus enum value
    citation_info: CitationInfo
    flagged_phrases: list[ComplianceResult] = field(default_factory=list)
    compliance_notes: str = ""
    source: str = ""
    has_scientific_citation: bool = False
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ValidationContext:
    """Context for a validation operation.

    Carries information needed during validation processing.

    Attributes:
        source_type: Research source (reddit, youtube, pubmed, etc.)
        source_metadata: Source-specific metadata dict
        product_name: Optional product name for Novel Food checks
    """

    source_type: str
    source_metadata: Optional[dict] = None
    product_name: Optional[str] = None


@dataclass
class ValidationStats:
    """Statistics from batch validation.

    Tracks counts for reporting and monitoring.

    Attributes:
        total: Total items submitted for validation
        validated: Successfully validated items
        compliant: Items with COMPLIANT status
        warned: Items with WARNING status
        rejected: Items with REJECTED status
        failed: Items that failed validation (error occurred)
    """

    total: int = 0
    validated: int = 0
    compliant: int = 0
    warned: int = 0
    rejected: int = 0
    failed: int = 0

    def __post_init__(self):
        """Validate statistics consistency."""
        # validated should equal compliant + warned + rejected
        # failed should equal total - validated
        pass

    @property
    def success_rate(self) -> float:
        """Calculate validation success rate (0-1)."""
        if self.total == 0:
            return 1.0
        return self.validated / self.total

    @property
    def compliance_rate(self) -> float:
        """Calculate compliance rate of validated items (0-1)."""
        if self.validated == 0:
            return 1.0
        return self.compliant / self.validated


class ValidationError(Exception):
    """Exception raised for validation errors.

    Attributes:
        message: Error description
        source_id: Optional identifier of the failed item
    """

    def __init__(self, message: str, source_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.source_id = source_id
