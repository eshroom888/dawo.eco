"""Schema definitions for Compliance Rewrite Suggester.

Data classes for rewrite requests, results, and individual suggestions.
All types use explicit typing for dependency injection compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from teams.dawo.validators.eu_compliance import (
    ComplianceStatus,
    ContentComplianceCheck,
    OverallStatus,
)

if TYPE_CHECKING:
    from teams.dawo.validators.brand_voice import BrandProfile


@dataclass
class RewriteSuggestion:
    """A single phrase rewrite suggestion.

    Contains the original flagged phrase, its compliance status,
    and 2-3 compliant alternative phrasings.

    Attributes:
        original_phrase: The flagged phrase from compliance check
        status: PROHIBITED or BORDERLINE classification
        regulation_reference: EU regulation citation (e.g., "EC 1924/2006 Article 10")
        explanation: Why the original phrase was flagged
        suggestions: 2-3 compliant alternative phrasings
        keep_recommendation: If borderline is acceptable, explain why to keep
        selected: User's chosen alternative (for apply operations)
        start_position: Character position in content for accurate replacement
        end_position: End character position in content
    """

    original_phrase: str
    status: ComplianceStatus
    regulation_reference: str
    explanation: str
    suggestions: list[str] = field(default_factory=list)
    keep_recommendation: Optional[str] = None
    selected: Optional[str] = None
    start_position: int = 0
    end_position: int = 0

    @property
    def has_suggestions(self) -> bool:
        """Check if suggestions are available."""
        return len(self.suggestions) > 0 or self.keep_recommendation is not None

    @property
    def is_prohibited(self) -> bool:
        """Check if this is a prohibited phrase."""
        return self.status == ComplianceStatus.PROHIBITED

    @property
    def is_borderline(self) -> bool:
        """Check if this is a borderline phrase."""
        return self.status == ComplianceStatus.BORDERLINE


@dataclass
class RewriteRequest:
    """Input for rewrite suggestion generation.

    Combines content, compliance check results, and brand profile
    for generating appropriate suggestions.

    Attributes:
        content: Full caption/content text to rewrite
        compliance_check: ContentComplianceCheck result from EU Compliance Checker
        brand_profile: BrandProfile for maintaining brand voice in suggestions
        language: Content language ("no" for Norwegian, "en" for English)
    """

    content: str
    compliance_check: ContentComplianceCheck
    brand_profile: BrandProfile
    language: str = "no"


@dataclass
class RewriteResult:
    """Output from rewrite suggestion generation.

    Contains all suggestions, the rewritten content (if selected),
    and validation history for audit trail.

    Attributes:
        original_content: Original content before any rewrites
        suggestions: List of RewriteSuggestion for each flagged phrase
        all_prohibited_addressed: Whether all PROHIBITED phrases have suggestions
        rewritten_content: Content with selected suggestions applied (None if not applied)
        validation_history: List of compliance checks for audit trail
        final_status: Overall compliance status after applying suggestions
        generation_time_ms: Time taken to generate suggestions in milliseconds
        created_at: Timestamp when result was created
    """

    original_content: str
    suggestions: list[RewriteSuggestion] = field(default_factory=list)
    all_prohibited_addressed: bool = False
    rewritten_content: Optional[str] = None
    validation_history: list[ContentComplianceCheck] = field(default_factory=list)
    final_status: OverallStatus = OverallStatus.REJECTED
    generation_time_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def prohibited_count(self) -> int:
        """Count of prohibited phrases in suggestions."""
        return sum(1 for s in self.suggestions if s.is_prohibited)

    @property
    def borderline_count(self) -> int:
        """Count of borderline phrases in suggestions."""
        return sum(1 for s in self.suggestions if s.is_borderline)

    @property
    def is_compliant(self) -> bool:
        """Check if final status is compliant."""
        return self.final_status == OverallStatus.COMPLIANT

    @property
    def validation_iterations(self) -> int:
        """Number of validation iterations performed."""
        return len(self.validation_history)
