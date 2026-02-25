"""Health Claims Monitor data transfer objects.

Epic 6, Story 6-1: EU Health Claims Register Monitor.

Dataclasses for passing data between pipeline stages.
These are NOT SQLAlchemy models — they are plain data containers.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional


class MonitorStatus(str, Enum):
    """Pipeline execution result status.

    Values:
        COMPLETE: All stages succeeded
        INCOMPLETE: Download or parse failed, previous snapshot preserved
        PARTIAL: Some stages succeeded, partial data saved
        FAILED: Critical failure, no data saved
    """

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class ClaimChangeRecord:
    """Change detected between two register snapshots.

    Used as intermediate data between ChangeDetector and Repository.
    NOT a SQLAlchemy model.

    Attributes:
        claim_id: EU register claim identifier
        change_type: Type of change (new, removed, modified, status_changed)
        field_changed: Which field changed (None for NEW/REMOVED)
        old_value: Previous value (None for NEW)
        new_value: New value (None for REMOVED)
        is_relevant: Whether change affects DAWO keywords
        severity: Alert severity level
    """

    claim_id: str
    change_type: str
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_relevant: bool = False
    severity: str = "low"


@dataclass
class FilterStats:
    """Statistics from relevance filtering.

    Attributes:
        total_claims: Total claims in dataset
        relevant_claims: Claims matching DAWO keywords
        mushroom_matches: Claims matching mushroom keywords
        adaptogen_matches: Claims matching adaptogen keywords
        vitamin_mineral_matches: Claims matching vitamin/mineral keywords
    """

    total_claims: int = 0
    relevant_claims: int = 0
    mushroom_matches: int = 0
    adaptogen_matches: int = 0
    vitamin_mineral_matches: int = 0


@dataclass
class MonitorResult:
    """Result of a monitor pipeline execution.

    Attributes:
        status: Execution result status
        claim_count: Total claims in downloaded dataset
        relevant_count: Claims matching DAWO keywords
        changes_detected: Number of changes vs previous snapshot
        new_claims: Number of new claims
        removed_claims: Number of removed claims
        modified_claims: Number of modified claims
        status_changes: Number of status changes
        errors: List of error messages
        snapshot_hash: SHA-256 hash of downloaded data
        executed_at: When the pipeline ran
    """

    status: MonitorStatus = MonitorStatus.COMPLETE
    claim_count: int = 0
    relevant_count: int = 0
    changes_detected: int = 0
    new_claims: int = 0
    removed_claims: int = 0
    modified_claims: int = 0
    status_changes: int = 0
    errors: list[str] = field(default_factory=list)
    snapshot_hash: str = ""
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "status": self.status.value,
            "claim_count": self.claim_count,
            "relevant_count": self.relevant_count,
            "changes_detected": self.changes_detected,
            "new_claims": self.new_claims,
            "removed_claims": self.removed_claims,
            "modified_claims": self.modified_claims,
            "status_changes": self.status_changes,
            "errors": self.errors,
            "snapshot_hash": self.snapshot_hash,
            "executed_at": self.executed_at.isoformat(),
        }


__all__ = [
    "ClaimChangeRecord",
    "FilterStats",
    "MonitorResult",
    "MonitorStatus",
]
