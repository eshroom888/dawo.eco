"""Auto-Publish Eligibility Tagger agent.

Tags content with auto-publish eligibility status based on quality score
and EU compliance status. Uses pure logic-based evaluation (no LLM required).

Registered as tier='generate' for consistency and future enhancements.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
import logging

from .schemas import (
    TaggingRequest,
    TaggingResult,
    EligibilityResult,
    AutoPublishTag,
    AutoPublishConfig,
)
from .statistics import AutoPublishStatisticsService
from .constants import DEFAULT_THRESHOLD, ELIGIBLE_MESSAGE, REQUIRED_COMPLIANCE_STATUS

logger = logging.getLogger(__name__)


class AutoPublishTaggerProtocol(Protocol):
    """Protocol for auto-publish tagger.

    Defines the interface for auto-publish eligibility tagging.
    Use this protocol for dependency injection and testing.
    """

    def tag_content(
        self,
        request: TaggingRequest
    ) -> TaggingResult:
        """Apply auto-publish eligibility tag to content.

        Args:
            request: TaggingRequest with content details

        Returns:
            TaggingResult with tag and display information
        """
        ...

    def check_eligibility(
        self,
        quality_score: float,
        compliance_status: str,
    ) -> EligibilityResult:
        """Check if content meets auto-publish eligibility criteria.

        Args:
            quality_score: Total quality score from ContentQualityScorer (0-10)
            compliance_status: EU compliance status ("COMPLIANT", "WARNING", "REJECTED")

        Returns:
            EligibilityResult with eligibility decision and reason
        """
        ...


class AutoPublishTagger:
    """Tags content with auto-publish eligibility status.

    Evaluates content quality score and EU compliance status to determine
    if content would qualify for auto-publishing (score >= 9, COMPLIANT).

    Uses 'generate' tier (defaults to configured model) for future LLM enhancements.
    Configuration is received via dependency injection - NEVER loads config directly.

    Attributes:
        _statistics: Service for tracking tagging statistics
        _config: Auto-publish toggle configuration
        _threshold: Quality score threshold for eligibility
    """

    def __init__(
        self,
        statistics_service: AutoPublishStatisticsService,
        config: AutoPublishConfig | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            statistics_service: Service for tracking tagging statistics
            config: Auto-publish toggle configuration
            threshold: Quality score threshold for eligibility (default: 9.0)
        """
        self._statistics = statistics_service
        self._config = config or AutoPublishConfig()
        self._threshold = threshold

    def check_eligibility(
        self,
        quality_score: float,
        compliance_status: str,
    ) -> EligibilityResult:
        """Check if content meets auto-publish eligibility criteria.

        Content is eligible when:
        1. Quality score >= threshold (default 9.0)
        2. Compliance status == "COMPLIANT"

        Args:
            quality_score: Total quality score from ContentQualityScorer (0-10)
            compliance_status: EU compliance status ("COMPLIANT", "WARNING", "REJECTED")

        Returns:
            EligibilityResult with eligibility decision and reason
        """
        score_eligible = quality_score >= self._threshold
        compliance_eligible = compliance_status == REQUIRED_COMPLIANCE_STATUS
        is_eligible = score_eligible and compliance_eligible

        if is_eligible:
            tag = AutoPublishTag.WOULD_AUTO_PUBLISH
            reason = f"Quality score {quality_score} >= {self._threshold} and compliance COMPLIANT"
        elif not score_eligible:
            tag = AutoPublishTag.NOT_ELIGIBLE
            reason = f"Quality score {quality_score} below threshold {self._threshold}"
        else:
            tag = AutoPublishTag.NOT_ELIGIBLE
            reason = f"Compliance status {compliance_status} is not COMPLIANT"

        return EligibilityResult(
            is_eligible=is_eligible,
            tag=tag,
            reason=reason,
            quality_score=quality_score,
            compliance_status=compliance_status,
            threshold=self._threshold,
        )

    def tag_content(
        self,
        request: TaggingRequest
    ) -> TaggingResult:
        """Apply auto-publish eligibility tag to content.

        Evaluates the request against eligibility criteria and applies
        the appropriate tag. Records statistics for eligible content.

        Args:
            request: TaggingRequest with content details

        Returns:
            TaggingResult with tag and display information

        Raises:
            Exception: If tagging fails (logged before raising)
        """
        try:
            eligibility = self.check_eligibility(
                quality_score=request.quality_score,
                compliance_status=request.compliance_status,
            )

            # Record for statistics tracking
            if eligibility.is_eligible:
                self._statistics.record_tagging(
                    content_id=request.content_id,
                    content_type=request.content_type,
                )

            display_message = ELIGIBLE_MESSAGE if eligibility.is_eligible else ""

            return TaggingResult(
                content_id=request.content_id,
                tag=eligibility.tag,
                is_eligible=eligibility.is_eligible,
                reason=eligibility.reason,
                display_message=display_message,
                tagged_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error("Auto-publish tagging failed for content %s: %s", request.content_id, e)
            raise

    def is_auto_publish_enabled(self, content_type: str) -> bool:
        """Check if auto-publish is enabled for content type.

        Args:
            content_type: Content type to check

        Returns:
            True if auto-publish is enabled for this content type
        """
        return self._config.is_enabled(content_type)
