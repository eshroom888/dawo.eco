"""Statistics service for auto-publish tagging.

Tracks tagging operations and approval outcomes to calculate accuracy.
Uses in-memory storage for MVP with interface for future database persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from .schemas import ApprovalOutcome, AccuracyStats, AutoPublishTag

logger = logging.getLogger(__name__)


class AutoPublishStatisticsService:
    """Service for tracking auto-publish tagging statistics.

    Maintains in-memory statistics for tagging operations.
    Can be extended with database persistence in the future.
    """

    def __init__(self) -> None:
        """Initialize with empty statistics."""
        self._tagged_content: list[dict] = []
        self._outcomes: list[ApprovalOutcome] = []

    def record_tagging(
        self,
        content_id: str,
        content_type: str,
    ) -> None:
        """Record when content is tagged WOULD_AUTO_PUBLISH.

        Args:
            content_id: Unique content identifier
            content_type: Content type (instagram_feed, etc.)
        """
        self._tagged_content.append({
            "content_id": content_id,
            "content_type": content_type,
            "tagged_at": datetime.now(timezone.utc),
        })
        logger.info(
            "Recorded auto-publish tagging for content %s (type: %s)",
            content_id, content_type
        )

    def record_approval_outcome(
        self,
        content_id: str,
        content_type: str,
        was_edited: bool,
        was_approved: bool,
    ) -> None:
        """Record approval decision for tagged content.

        Only call this for content that was tagged WOULD_AUTO_PUBLISH.
        A warning is logged if the content_id was not previously recorded as tagged.

        Args:
            content_id: Unique content identifier
            content_type: Content type
            was_edited: True if content was modified before approval
            was_approved: True if approved, False if rejected
        """
        # Validate that this content was actually tagged WOULD_AUTO_PUBLISH
        was_tagged = any(
            t["content_id"] == content_id for t in self._tagged_content
        )
        if not was_tagged:
            logger.warning(
                "Recording outcome for content %s that was not previously tagged as WOULD_AUTO_PUBLISH",
                content_id
            )

        if was_approved:
            outcome = (
                AutoPublishTag.APPROVED_UNCHANGED
                if not was_edited
                else AutoPublishTag.APPROVED_MODIFIED
            )
        else:
            outcome = AutoPublishTag.REJECTED

        self._outcomes.append(ApprovalOutcome(
            content_id=content_id,
            original_tag=AutoPublishTag.WOULD_AUTO_PUBLISH,
            outcome=outcome,
            content_type=content_type,
            was_edited=was_edited,
            recorded_at=datetime.now(timezone.utc),
        ))
        logger.info(
            "Recorded approval outcome %s for content %s",
            outcome.value, content_id
        )

    def get_accuracy_stats(
        self,
        content_type: Optional[str] = None,
        period_days: Optional[int] = None,
    ) -> AccuracyStats:
        """Calculate accuracy statistics for auto-publish tagging.

        Args:
            content_type: Filter by content type (None = all)
            period_days: Filter by time period in days (None = all time)

        Returns:
            AccuracyStats with accuracy rate and breakdown
        """
        cutoff = None
        if period_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Filter outcomes
        filtered = [
            o for o in self._outcomes
            if (content_type is None or o.content_type == content_type)
            and (cutoff is None or o.recorded_at >= cutoff)
        ]

        # Count outcomes
        total = len(filtered)
        unchanged = sum(1 for o in filtered if o.outcome == AutoPublishTag.APPROVED_UNCHANGED)
        modified = sum(1 for o in filtered if o.outcome == AutoPublishTag.APPROVED_MODIFIED)
        rejected = sum(1 for o in filtered if o.outcome == AutoPublishTag.REJECTED)

        # Calculate accuracy rate (avoid division by zero)
        accuracy = (unchanged / total * 100) if total > 0 else 0.0

        return AccuracyStats(
            total_with_outcome=total,
            approved_unchanged=unchanged,
            approved_modified=modified,
            rejected=rejected,
            accuracy_rate=round(accuracy, 1),
            content_type=content_type,
            period_days=period_days,
        )

    def get_tagging_count(
        self,
        content_type: Optional[str] = None,
        period_days: Optional[int] = None,
    ) -> int:
        """Get count of content items tagged as WOULD_AUTO_PUBLISH.

        Args:
            content_type: Filter by content type (None = all)
            period_days: Filter by time period in days (None = all time)

        Returns:
            Count of tagged items matching the filters
        """
        cutoff = None
        if period_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        return sum(
            1 for t in self._tagged_content
            if (content_type is None or t["content_type"] == content_type)
            and (cutoff is None or t["tagged_at"] >= cutoff)
        )
