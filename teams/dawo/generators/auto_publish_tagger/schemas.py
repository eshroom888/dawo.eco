"""Schema definitions for Auto-Publish Eligibility Tagger.

Data classes for tagging requests, results, eligibility, and statistics.
All types use explicit typing for dependency injection compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Protocol


class AutoPublishTag(Enum):
    """Auto-publish eligibility tag status."""

    WOULD_AUTO_PUBLISH = "would_auto_publish"
    NOT_ELIGIBLE = "not_eligible"
    APPROVED_UNCHANGED = "approved_unchanged"
    APPROVED_MODIFIED = "approved_modified"
    REJECTED = "rejected"


@dataclass
class EligibilityResult:
    """Result of eligibility check.

    Attributes:
        is_eligible: Whether content meets auto-publish criteria
        tag: The auto-publish tag to apply
        reason: Human-readable explanation of decision
        quality_score: The quality score that was evaluated
        compliance_status: The compliance status that was evaluated
        threshold: The threshold used for eligibility
    """

    is_eligible: bool
    tag: AutoPublishTag
    reason: str
    quality_score: float
    compliance_status: str
    threshold: float = 9.0


@dataclass
class TaggingRequest:
    """Input for auto-publish tagging.

    Attributes:
        content_id: Unique content identifier
        quality_score: Total quality score from ContentQualityScorer (0-10)
        compliance_status: EU compliance status ("COMPLIANT", "WARNING", "REJECTED")
        content_type: Content type value as string
        created_at: Request creation timestamp
    """

    content_id: str
    quality_score: float
    compliance_status: str
    content_type: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaggingResult:
    """Result of tagging operation.

    Attributes:
        content_id: Unique content identifier
        tag: The applied auto-publish tag
        is_eligible: Whether content is eligible for auto-publish
        reason: Human-readable explanation of decision
        display_message: Message to show in approval queue
        tagged_at: Timestamp when tag was applied
    """

    content_id: str
    tag: AutoPublishTag
    is_eligible: bool
    reason: str
    display_message: str
    tagged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ApprovalOutcome:
    """Record of approval decision for statistics.

    Attributes:
        content_id: Unique content identifier
        original_tag: The tag that was applied before approval
        outcome: The outcome tag (APPROVED_UNCHANGED, APPROVED_MODIFIED, REJECTED)
        content_type: Content type for filtering
        was_edited: True if content was modified before approval
        recorded_at: Timestamp when outcome was recorded
    """

    content_id: str
    original_tag: AutoPublishTag
    outcome: AutoPublishTag
    content_type: str
    was_edited: bool
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AccuracyStats:
    """Auto-publish accuracy statistics.

    Attributes:
        total_with_outcome: Total WOULD_AUTO_PUBLISH items with recorded approval outcomes
        approved_unchanged: Approved without edits
        approved_modified: Approved with edits
        rejected: Rejected count
        accuracy_rate: approved_unchanged / total_with_outcome * 100
        content_type: Filter by content type (None = all)
        period_days: Filter by time period (None = all time)
    """

    total_with_outcome: int
    approved_unchanged: int
    approved_modified: int
    rejected: int
    accuracy_rate: float
    content_type: Optional[str] = None
    period_days: Optional[int] = None


class AutoPublishConfigProtocol(Protocol):
    """Protocol for auto-publish toggle configuration.

    Use this protocol for dependency injection and testing.
    Implementations must provide is_enabled() to check content type status.
    """

    def is_enabled(self, content_type: str) -> bool:
        """Check if auto-publish is enabled for content type.

        Args:
            content_type: Content type to check (instagram_feed, instagram_story, instagram_reel)

        Returns:
            True if auto-publish is enabled for this content type
        """
        ...


@dataclass
class AutoPublishConfig:
    """Auto-publish toggle configuration.

    All toggles default to False for MVP (informational-only mode).

    Attributes:
        instagram_feed_enabled: Whether auto-publish is enabled for feed posts
        instagram_story_enabled: Whether auto-publish is enabled for stories
        instagram_reel_enabled: Whether auto-publish is enabled for reels
    """

    instagram_feed_enabled: bool = False
    instagram_story_enabled: bool = False
    instagram_reel_enabled: bool = False

    def is_enabled(self, content_type: str) -> bool:
        """Check if auto-publish is enabled for content type.

        Args:
            content_type: Content type to check (instagram_feed, instagram_story, instagram_reel)

        Returns:
            True if auto-publish is enabled for this content type
        """
        mapping = {
            "instagram_feed": self.instagram_feed_enabled,
            "instagram_story": self.instagram_story_enabled,
            "instagram_reel": self.instagram_reel_enabled,
        }
        return mapping.get(content_type, False)
