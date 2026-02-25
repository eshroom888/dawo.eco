"""Evidence Collection Schemas and DTOs (Story 6-8, Task 4).

Data transfer objects for evidence capture pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


class ImmutableEvidenceError(ValueError):
    """Raised when attempting to modify immutable evidence fields.

    Evidence records are legally defensible documents. Once created,
    content fields (screenshot_hash, claim_text, source_url, screenshot_path)
    must never be modified.
    """


@dataclass
class CaptureResult:
    """Result from a screenshot capture operation.

    Attributes:
        screenshot_bytes: Raw screenshot image bytes.
        url: URL that was captured.
        captured_at: Timestamp of capture (timezone-aware).
        page_title: HTML page title at time of capture.
        metadata: Additional capture metadata.
    """

    screenshot_bytes: bytes
    url: str
    captured_at: datetime
    page_title: str
    metadata: dict = field(default_factory=dict)


@dataclass
class EvidenceCreateDTO:
    """Data for creating an Evidence record.

    Attributes:
        violation_id: FK to competitor_violations.id.
        competitor_name: Name of the competitor.
        source_url: Original source URL.
        source_type: 'instagram_post' or 'website_page'.
        claim_text: Extracted health claim text.
        claim_category: Claim category (treatment/prevention/etc).
        violation_type: Violation type descriptor.
        severity: Severity level (high/medium/low).
        regulation_violated: EU regulation reference (nullable).
        detection_reasoning: Why classified as violation (nullable).
        confidence: Confidence score 0.0-1.0 (normalized from 0-100).
        screenshot_path: Relative file path to screenshot.
        screenshot_hash: SHA-256 hex digest of screenshot bytes.
        screenshot_size_bytes: File size in bytes.
        captured_at: When screenshot was captured.
        evidence_metadata: Additional JSONB metadata.
    """

    violation_id: UUID
    competitor_name: str
    source_url: str
    source_type: str
    claim_text: str
    claim_category: str
    violation_type: str
    severity: str
    regulation_violated: str | None
    detection_reasoning: str | None
    confidence: float
    screenshot_path: str
    screenshot_hash: str
    screenshot_size_bytes: int
    captured_at: datetime
    evidence_metadata: dict = field(default_factory=dict)


@dataclass
class CollectionBatchResult:
    """Result from a batch evidence collection run.

    Attributes:
        total_processed: Total violations examined.
        collected: Successfully captured and stored.
        failed: Capture or storage failures.
        skipped_already_collected: Violations with existing evidence.
        errors: Error descriptions for failed captures.
    """

    total_processed: int = 0
    collected: int = 0
    failed: int = 0
    skipped_already_collected: int = 0
    errors: list[str] = field(default_factory=list)


__all__ = [
    "CaptureResult",
    "CollectionBatchResult",
    "EvidenceCreateDTO",
    "ImmutableEvidenceError",
]
