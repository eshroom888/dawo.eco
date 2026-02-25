"""Violation Detection Schemas and DTOs (Story 6-7, Task 4).

Data transfer objects for the violation detection pipeline.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ViolationResult:
    """Result of classifying a single claim against EU regulations.

    Attributes:
        extracted_claim_id: UUID of the source ExtractedHealthClaim.
        claim_text: The claim text that was evaluated.
        claim_category: Category of the claim (treatment/prevention/etc).
        confidence_score: Confidence of the original extraction (0-100).
        violation_status: Classification result (violation/suspect/compliant).
        severity: Severity level (high/medium/low).
        regulation_article: EU regulation reference.
        violation_type: Type descriptor (e.g. unauthorized_treatment_claim).
        detection_reasoning: Why this classification was made.
        authorized_claims_checked: Number of EU register claims checked.
        nearest_authorized_claim: Closest matching authorized claim, or None.
        competitor_name: Name of the competitor.
        source_url: URL of the competitor content.
        evidence_status: Evidence collection status for Story 6-8.
    """

    extracted_claim_id: UUID
    claim_text: str
    claim_category: str
    confidence_score: int
    violation_status: str
    severity: str
    regulation_article: str
    violation_type: str
    detection_reasoning: str
    authorized_claims_checked: int
    nearest_authorized_claim: str | None
    competitor_name: str
    source_url: str
    evidence_status: str = "pending_collection"


@dataclass
class DetectionBatchResult:
    """Aggregate result of a violation detection batch run.

    Attributes:
        total_processed: Total claims processed in this batch.
        violations_found: Number classified as VIOLATION.
        suspects_found: Number classified as SUSPECT.
        compliant_found: Number classified as COMPLIANT.
        skipped_already_evaluated: Number skipped (already have violation record).
        errors: Number of per-claim errors.
    """

    total_processed: int = 0
    violations_found: int = 0
    suspects_found: int = 0
    compliant_found: int = 0
    skipped_already_evaluated: int = 0
    errors: int = 0


@dataclass
class AuthorizedClaimInfo:
    """Represents an EU Register entry for cross-reference.

    Attributes:
        claim_id: EU register claim identifier.
        substance: Substance or nutrient name.
        claim_text: Full authorized claim text.
        status: Authorization status (authorised/non_authorised/etc).
        food_category: Functional food category, or None.
    """

    claim_id: str
    substance: str
    claim_text: str
    status: str
    food_category: str | None = None


__all__ = [
    "ViolationResult",
    "DetectionBatchResult",
    "AuthorizedClaimInfo",
]
