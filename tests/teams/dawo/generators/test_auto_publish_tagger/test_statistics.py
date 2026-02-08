"""Unit tests for statistics tracking and accuracy calculation.

Tests Task 8.6-8.7: Statistics tracking with various approval outcomes
and accuracy calculation with sample data.
"""

import pytest
from datetime import datetime, timezone, timedelta

from teams.dawo.generators.auto_publish_tagger import (
    AutoPublishStatisticsService,
    AutoPublishTag,
)


class TestRecordTagging:
    """Tests for record_tagging method."""

    def test_record_tagging_stores_content(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Recording a tagging should store content info."""
        statistics_service.record_tagging(
            content_id="content-001",
            content_type="instagram_feed",
        )

        assert len(statistics_service._tagged_content) == 1
        assert statistics_service._tagged_content[0]["content_id"] == "content-001"
        assert statistics_service._tagged_content[0]["content_type"] == "instagram_feed"

    def test_record_multiple_taggings(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Recording multiple taggings should store all."""
        statistics_service.record_tagging("content-001", "instagram_feed")
        statistics_service.record_tagging("content-002", "instagram_story")
        statistics_service.record_tagging("content-003", "instagram_reel")

        assert len(statistics_service._tagged_content) == 3


class TestRecordApprovalOutcome:
    """Tests for record_approval_outcome method (Task 8.6)."""

    def test_record_approved_unchanged(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Approved without edits should record APPROVED_UNCHANGED."""
        statistics_service.record_approval_outcome(
            content_id="content-001",
            content_type="instagram_feed",
            was_edited=False,
            was_approved=True,
        )

        assert len(statistics_service._outcomes) == 1
        outcome = statistics_service._outcomes[0]
        assert outcome.outcome == AutoPublishTag.APPROVED_UNCHANGED
        assert outcome.was_edited is False

    def test_record_approved_modified(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Approved with edits should record APPROVED_MODIFIED."""
        statistics_service.record_approval_outcome(
            content_id="content-001",
            content_type="instagram_feed",
            was_edited=True,
            was_approved=True,
        )

        assert len(statistics_service._outcomes) == 1
        outcome = statistics_service._outcomes[0]
        assert outcome.outcome == AutoPublishTag.APPROVED_MODIFIED
        assert outcome.was_edited is True

    def test_record_rejected(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Rejected should record REJECTED outcome."""
        statistics_service.record_approval_outcome(
            content_id="content-001",
            content_type="instagram_feed",
            was_edited=False,
            was_approved=False,
        )

        assert len(statistics_service._outcomes) == 1
        outcome = statistics_service._outcomes[0]
        assert outcome.outcome == AutoPublishTag.REJECTED

    def test_record_rejected_even_with_edits(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Rejected with edits should still be REJECTED."""
        statistics_service.record_approval_outcome(
            content_id="content-001",
            content_type="instagram_feed",
            was_edited=True,
            was_approved=False,
        )

        assert statistics_service._outcomes[0].outcome == AutoPublishTag.REJECTED

    def test_record_mixed_outcomes(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Multiple outcomes should all be recorded."""
        statistics_service.record_approval_outcome("c1", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c2", "instagram_feed", True, True)
        statistics_service.record_approval_outcome("c3", "instagram_feed", False, False)

        assert len(statistics_service._outcomes) == 3


class TestGetAccuracyStats:
    """Tests for get_accuracy_stats method (Task 8.7)."""

    def test_empty_stats_returns_zero(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """No outcomes should return 0% accuracy without division error."""
        stats = statistics_service.get_accuracy_stats()

        assert stats.total_with_outcome == 0
        assert stats.approved_unchanged == 0
        assert stats.approved_modified == 0
        assert stats.rejected == 0
        assert stats.accuracy_rate == 0.0

    def test_all_approved_unchanged_100_percent(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """All approved unchanged should be 100% accuracy."""
        statistics_service.record_approval_outcome("c1", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c2", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c3", "instagram_feed", False, True)

        stats = statistics_service.get_accuracy_stats()

        assert stats.total_with_outcome == 3
        assert stats.approved_unchanged == 3
        assert stats.accuracy_rate == 100.0

    def test_mixed_outcomes_accuracy(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Mixed outcomes should calculate correct accuracy."""
        # 2 unchanged, 1 modified, 1 rejected = 2/4 = 50%
        statistics_service.record_approval_outcome("c1", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c2", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c3", "instagram_feed", True, True)
        statistics_service.record_approval_outcome("c4", "instagram_feed", False, False)

        stats = statistics_service.get_accuracy_stats()

        assert stats.total_with_outcome == 4
        assert stats.approved_unchanged == 2
        assert stats.approved_modified == 1
        assert stats.rejected == 1
        assert stats.accuracy_rate == 50.0

    def test_filter_by_content_type(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Filtering by content type should only count matching."""
        statistics_service.record_approval_outcome("c1", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c2", "instagram_story", False, True)
        statistics_service.record_approval_outcome("c3", "instagram_feed", True, True)
        statistics_service.record_approval_outcome("c4", "instagram_reel", False, False)

        feed_stats = statistics_service.get_accuracy_stats(content_type="instagram_feed")
        story_stats = statistics_service.get_accuracy_stats(content_type="instagram_story")
        reel_stats = statistics_service.get_accuracy_stats(content_type="instagram_reel")

        assert feed_stats.total_with_outcome == 2
        assert feed_stats.approved_unchanged == 1
        assert feed_stats.content_type == "instagram_feed"

        assert story_stats.total_with_outcome == 1
        assert story_stats.approved_unchanged == 1

        assert reel_stats.total_with_outcome == 1
        assert reel_stats.rejected == 1

    def test_filter_by_period_days(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Filtering by period should only count recent outcomes."""
        # Record outcome
        statistics_service.record_approval_outcome("c1", "instagram_feed", False, True)

        # Get stats for last 7 days
        stats_7d = statistics_service.get_accuracy_stats(period_days=7)
        assert stats_7d.total_with_outcome == 1
        assert stats_7d.period_days == 7

        # Get stats for all time
        stats_all = statistics_service.get_accuracy_stats()
        assert stats_all.total_with_outcome == 1
        assert stats_all.period_days is None

    def test_accuracy_rounded_to_one_decimal(
        self,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Accuracy should be rounded to 1 decimal place."""
        # 1 unchanged out of 3 = 33.333...%
        statistics_service.record_approval_outcome("c1", "instagram_feed", False, True)
        statistics_service.record_approval_outcome("c2", "instagram_feed", True, True)
        statistics_service.record_approval_outcome("c3", "instagram_feed", False, False)

        stats = statistics_service.get_accuracy_stats()

        assert stats.accuracy_rate == 33.3  # Rounded


class TestStatisticsIntegrationWithTagger:
    """Integration tests for statistics with tagger."""

    def test_tagger_records_eligible_content(
        self,
        default_tagger,
        eligible_request,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Tagging eligible content should record to statistics."""
        # Tag content
        default_tagger.tag_content(eligible_request)

        # Verify recorded
        assert len(statistics_service._tagged_content) == 1
        assert statistics_service._tagged_content[0]["content_id"] == eligible_request.content_id

    def test_tagger_does_not_record_ineligible_content(
        self,
        default_tagger,
        ineligible_score_request,
        statistics_service: AutoPublishStatisticsService,
    ) -> None:
        """Tagging ineligible content should NOT record to statistics."""
        # Tag content
        default_tagger.tag_content(ineligible_score_request)

        # Verify not recorded
        assert len(statistics_service._tagged_content) == 0
