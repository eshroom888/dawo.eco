"""Integration tests for Auto-Publish Eligibility Tagger.

Tests Task 9.1-9.4: Full tagging flow, statistics accumulation,
accuracy calculation, and content type filtering.
"""

import pytest

from teams.dawo.generators.auto_publish_tagger import (
    AutoPublishTagger,
    AutoPublishStatisticsService,
    AutoPublishConfig,
    TaggingRequest,
    AutoPublishTag,
    ELIGIBLE_MESSAGE,
)


class TestFullTaggingFlow:
    """Integration tests for complete tagging flow (Task 9.1)."""

    def test_full_eligible_tagging_flow(self) -> None:
        """Test complete flow: request -> tag -> stats for eligible content."""
        # Setup
        stats_service = AutoPublishStatisticsService()
        tagger = AutoPublishTagger(
            statistics_service=stats_service,
            config=AutoPublishConfig(),
            threshold=9.0,
        )

        # Create eligible request
        request = TaggingRequest(
            content_id="integration-test-001",
            quality_score=9.5,
            compliance_status="COMPLIANT",
            content_type="instagram_feed",
        )

        # Execute tagging
        result = tagger.tag_content(request)

        # Verify result
        assert result.content_id == "integration-test-001"
        assert result.tag == AutoPublishTag.WOULD_AUTO_PUBLISH
        assert result.is_eligible is True
        assert result.display_message == ELIGIBLE_MESSAGE
        assert result.tagged_at is not None

        # Verify statistics recorded
        assert len(stats_service._tagged_content) == 1
        assert stats_service._tagged_content[0]["content_id"] == "integration-test-001"
        assert stats_service._tagged_content[0]["content_type"] == "instagram_feed"

    def test_full_ineligible_tagging_flow(self) -> None:
        """Test complete flow for ineligible content."""
        # Setup
        stats_service = AutoPublishStatisticsService()
        tagger = AutoPublishTagger(
            statistics_service=stats_service,
            config=AutoPublishConfig(),
            threshold=9.0,
        )

        # Create ineligible request (low score)
        request = TaggingRequest(
            content_id="integration-test-002",
            quality_score=8.0,
            compliance_status="COMPLIANT",
            content_type="instagram_feed",
        )

        # Execute tagging
        result = tagger.tag_content(request)

        # Verify result
        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert result.is_eligible is False
        assert result.display_message == ""

        # Verify NO statistics recorded for ineligible
        assert len(stats_service._tagged_content) == 0


class TestStatisticsAccumulation:
    """Integration tests for statistics accumulation (Task 9.2)."""

    def test_statistics_accumulate_over_multiple_operations(self) -> None:
        """Statistics should accumulate correctly over multiple tagging operations."""
        # Setup
        stats_service = AutoPublishStatisticsService()
        tagger = AutoPublishTagger(
            statistics_service=stats_service,
            config=AutoPublishConfig(),
            threshold=9.0,
        )

        # Tag multiple eligible items
        for i in range(5):
            request = TaggingRequest(
                content_id=f"content-{i:03d}",
                quality_score=9.5,
                compliance_status="COMPLIANT",
                content_type="instagram_feed",
            )
            tagger.tag_content(request)

        # Verify all recorded
        assert len(stats_service._tagged_content) == 5

        # Record approval outcomes
        stats_service.record_approval_outcome("content-000", "instagram_feed", False, True)  # unchanged
        stats_service.record_approval_outcome("content-001", "instagram_feed", False, True)  # unchanged
        stats_service.record_approval_outcome("content-002", "instagram_feed", True, True)   # modified
        stats_service.record_approval_outcome("content-003", "instagram_feed", False, False) # rejected
        stats_service.record_approval_outcome("content-004", "instagram_feed", False, True)  # unchanged

        # Verify outcomes recorded
        assert len(stats_service._outcomes) == 5

        # Calculate accuracy
        stats = stats_service.get_accuracy_stats()
        assert stats.total_with_outcome == 5
        assert stats.approved_unchanged == 3
        assert stats.approved_modified == 1
        assert stats.rejected == 1
        assert stats.accuracy_rate == 60.0  # 3/5 = 60%


class TestAccuracyCalculationMixedOutcomes:
    """Integration tests for accuracy with mixed outcomes (Task 9.3)."""

    def test_accuracy_with_realistic_mixed_outcomes(self) -> None:
        """Accuracy calculation with realistic mixed scenario."""
        stats_service = AutoPublishStatisticsService()

        # Simulate realistic approval pattern:
        # 10 items tagged, various outcomes
        outcomes = [
            ("c01", "instagram_feed", False, True),   # unchanged
            ("c02", "instagram_feed", False, True),   # unchanged
            ("c03", "instagram_feed", False, True),   # unchanged
            ("c04", "instagram_feed", False, True),   # unchanged
            ("c05", "instagram_feed", False, True),   # unchanged
            ("c06", "instagram_feed", False, True),   # unchanged
            ("c07", "instagram_feed", True, True),    # modified
            ("c08", "instagram_feed", True, True),    # modified
            ("c09", "instagram_feed", False, False),  # rejected
            ("c10", "instagram_feed", False, False),  # rejected
        ]

        for content_id, content_type, was_edited, was_approved in outcomes:
            stats_service.record_approval_outcome(
                content_id=content_id,
                content_type=content_type,
                was_edited=was_edited,
                was_approved=was_approved,
            )

        # Calculate
        stats = stats_service.get_accuracy_stats()

        # Verify: 6 unchanged / 10 total = 60%
        assert stats.total_with_outcome == 10
        assert stats.approved_unchanged == 6
        assert stats.approved_modified == 2
        assert stats.rejected == 2
        assert stats.accuracy_rate == 60.0

    def test_accuracy_with_all_rejected(self) -> None:
        """Accuracy should be 0% when all rejected."""
        stats_service = AutoPublishStatisticsService()

        for i in range(5):
            stats_service.record_approval_outcome(
                content_id=f"content-{i}",
                content_type="instagram_feed",
                was_edited=False,
                was_approved=False,
            )

        stats = stats_service.get_accuracy_stats()
        assert stats.accuracy_rate == 0.0
        assert stats.rejected == 5


class TestContentTypeFiltering:
    """Integration tests for content type filtering (Task 9.4)."""

    def test_filter_statistics_by_content_type(self) -> None:
        """Statistics should filter correctly by content type."""
        stats_service = AutoPublishStatisticsService()
        tagger = AutoPublishTagger(
            statistics_service=stats_service,
            config=AutoPublishConfig(),
            threshold=9.0,
        )

        # Tag different content types
        content_types = ["instagram_feed", "instagram_story", "instagram_reel"]
        for i, content_type in enumerate(content_types):
            # 2 items per content type
            for j in range(2):
                request = TaggingRequest(
                    content_id=f"{content_type}-{j}",
                    quality_score=9.5,
                    compliance_status="COMPLIANT",
                    content_type=content_type,
                )
                tagger.tag_content(request)

        # Verify tagged counts
        assert len(stats_service._tagged_content) == 6

        # Record outcomes with different patterns per type
        # Feed: 2 unchanged (100% accuracy)
        stats_service.record_approval_outcome("instagram_feed-0", "instagram_feed", False, True)
        stats_service.record_approval_outcome("instagram_feed-1", "instagram_feed", False, True)

        # Story: 1 unchanged, 1 modified (50% accuracy)
        stats_service.record_approval_outcome("instagram_story-0", "instagram_story", False, True)
        stats_service.record_approval_outcome("instagram_story-1", "instagram_story", True, True)

        # Reel: 0 unchanged, 1 modified, 1 rejected (0% accuracy)
        stats_service.record_approval_outcome("instagram_reel-0", "instagram_reel", True, True)
        stats_service.record_approval_outcome("instagram_reel-1", "instagram_reel", False, False)

        # Verify filtered stats
        feed_stats = stats_service.get_accuracy_stats(content_type="instagram_feed")
        assert feed_stats.total_with_outcome == 2
        assert feed_stats.approved_unchanged == 2
        assert feed_stats.accuracy_rate == 100.0

        story_stats = stats_service.get_accuracy_stats(content_type="instagram_story")
        assert story_stats.total_with_outcome == 2
        assert story_stats.approved_unchanged == 1
        assert story_stats.approved_modified == 1
        assert story_stats.accuracy_rate == 50.0

        reel_stats = stats_service.get_accuracy_stats(content_type="instagram_reel")
        assert reel_stats.total_with_outcome == 2
        assert reel_stats.approved_unchanged == 0
        assert reel_stats.accuracy_rate == 0.0

    def test_all_content_types_aggregated(self) -> None:
        """Stats without filter should aggregate all content types."""
        stats_service = AutoPublishStatisticsService()

        # Record outcomes for different types
        stats_service.record_approval_outcome("c1", "instagram_feed", False, True)
        stats_service.record_approval_outcome("c2", "instagram_story", False, True)
        stats_service.record_approval_outcome("c3", "instagram_reel", False, False)

        # Get all stats
        all_stats = stats_service.get_accuracy_stats()

        assert all_stats.total_with_outcome == 3
        assert all_stats.approved_unchanged == 2
        assert all_stats.rejected == 1
        assert all_stats.content_type is None  # No filter applied


class TestEndToEndScenario:
    """End-to-end scenario testing full workflow."""

    def test_complete_workflow_simulation(self) -> None:
        """Simulate a realistic workflow with tagging and approval cycle."""
        # Setup
        stats_service = AutoPublishStatisticsService()
        tagger = AutoPublishTagger(
            statistics_service=stats_service,
            config=AutoPublishConfig(),
            threshold=9.0,
        )

        # Phase 1: Tag batch of content
        eligible_items = []
        for i in range(10):
            score = 9.0 + (i * 0.1)  # 9.0 to 9.9
            request = TaggingRequest(
                content_id=f"batch-{i:03d}",
                quality_score=score,
                compliance_status="COMPLIANT",
                content_type="instagram_feed",
            )
            result = tagger.tag_content(request)
            eligible_items.append(result)

        # Verify all tagged as eligible
        assert all(item.is_eligible for item in eligible_items)
        assert len(stats_service._tagged_content) == 10

        # Phase 2: Also tag some ineligible (shouldn't affect stats)
        for i in range(5):
            request = TaggingRequest(
                content_id=f"ineligible-{i}",
                quality_score=7.0,  # Below threshold
                compliance_status="COMPLIANT",
                content_type="instagram_feed",
            )
            tagger.tag_content(request)

        # Verify only eligible were recorded
        assert len(stats_service._tagged_content) == 10  # Still 10

        # Phase 3: Simulate approval workflow
        # 7 approved unchanged, 2 approved with edits, 1 rejected
        for i in range(7):
            stats_service.record_approval_outcome(
                f"batch-{i:03d}", "instagram_feed", False, True
            )
        stats_service.record_approval_outcome("batch-007", "instagram_feed", True, True)
        stats_service.record_approval_outcome("batch-008", "instagram_feed", True, True)
        stats_service.record_approval_outcome("batch-009", "instagram_feed", False, False)

        # Phase 4: Verify accuracy
        stats = stats_service.get_accuracy_stats()

        assert stats.total_with_outcome == 10
        assert stats.approved_unchanged == 7
        assert stats.approved_modified == 2
        assert stats.rejected == 1
        assert stats.accuracy_rate == 70.0  # 7/10 = 70%

        # Phase 5: Dashboard view - check if accuracy is ready for auto-publish
        # (simulating AC #3: operator can enable when confident)
        if stats.accuracy_rate >= 90.0:
            # Would enable auto-publish
            pass
        else:
            # Keep in simulation mode
            assert not tagger.is_auto_publish_enabled("instagram_feed")
