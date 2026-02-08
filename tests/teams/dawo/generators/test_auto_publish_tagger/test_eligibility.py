"""Unit tests for eligibility checking logic.

Tests Task 8.1-8.5: Eligibility criteria validation including
boundary values and various compliance/score combinations.
"""

import pytest

from teams.dawo.generators.auto_publish_tagger import (
    AutoPublishTagger,
    AutoPublishStatisticsService,
    AutoPublishConfig,
    TaggingRequest,
    AutoPublishTag,
    DEFAULT_THRESHOLD,
    ELIGIBLE_MESSAGE,
)


class TestEligibilityCheck:
    """Tests for check_eligibility method."""

    def test_eligible_with_high_score_and_compliant(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """Test 8.1: Score >= 9 AND COMPLIANT should be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=9.5,
            compliance_status="COMPLIANT",
        )

        assert result.is_eligible is True
        assert result.tag == AutoPublishTag.WOULD_AUTO_PUBLISH
        assert "COMPLIANT" in result.reason
        assert result.quality_score == 9.5
        assert result.compliance_status == "COMPLIANT"
        assert result.threshold == DEFAULT_THRESHOLD

    def test_not_eligible_with_high_score_and_warning(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """Test 8.2: Score >= 9 AND WARNING should NOT be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=9.5,
            compliance_status="WARNING",
        )

        assert result.is_eligible is False
        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert "WARNING" in result.reason
        assert "not COMPLIANT" in result.reason

    def test_not_eligible_with_low_score_and_compliant(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """Test 8.3: Score < 9 AND COMPLIANT should NOT be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=8.5,
            compliance_status="COMPLIANT",
        )

        assert result.is_eligible is False
        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert "below threshold" in result.reason
        assert result.quality_score == 8.5

    def test_boundary_exactly_at_threshold_eligible(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """Test 8.4: Score = 9.0 exactly should be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=9.0,
            compliance_status="COMPLIANT",
        )

        assert result.is_eligible is True
        assert result.tag == AutoPublishTag.WOULD_AUTO_PUBLISH

    def test_boundary_just_below_threshold_not_eligible(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """Test 8.5: Score = 8.9 should NOT be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=8.9,
            compliance_status="COMPLIANT",
        )

        assert result.is_eligible is False
        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert "below threshold" in result.reason

    def test_not_eligible_with_rejected_compliance(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """REJECTED compliance should NOT be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=10.0,
            compliance_status="REJECTED",
        )

        assert result.is_eligible is False
        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert "REJECTED" in result.reason

    def test_both_conditions_fail(
        self,
        default_tagger: AutoPublishTagger,
    ) -> None:
        """Low score AND non-compliant should NOT be eligible."""
        result = default_tagger.check_eligibility(
            quality_score=7.0,
            compliance_status="WARNING",
        )

        assert result.is_eligible is False
        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        # Should mention score issue (first check)
        assert "below threshold" in result.reason

    def test_custom_threshold_eligibility(
        self,
        custom_threshold_tagger: AutoPublishTagger,
    ) -> None:
        """Custom threshold (8.0) should change eligibility."""
        result = custom_threshold_tagger.check_eligibility(
            quality_score=8.5,
            compliance_status="COMPLIANT",
        )

        assert result.is_eligible is True
        assert result.tag == AutoPublishTag.WOULD_AUTO_PUBLISH
        assert result.threshold == 8.0


class TestTagContent:
    """Tests for tag_content method."""

    def test_eligible_content_tagged_correctly(
        self,
        default_tagger: AutoPublishTagger,
        eligible_request: TaggingRequest,
    ) -> None:
        """Eligible content should be tagged WOULD_AUTO_PUBLISH."""
        result = default_tagger.tag_content(eligible_request)

        assert result.content_id == eligible_request.content_id
        assert result.tag == AutoPublishTag.WOULD_AUTO_PUBLISH
        assert result.is_eligible is True
        assert result.display_message == ELIGIBLE_MESSAGE
        assert result.tagged_at is not None

    def test_ineligible_score_content_tagged_correctly(
        self,
        default_tagger: AutoPublishTagger,
        ineligible_score_request: TaggingRequest,
    ) -> None:
        """Low score content should be tagged NOT_ELIGIBLE."""
        result = default_tagger.tag_content(ineligible_score_request)

        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert result.is_eligible is False
        assert result.display_message == ""

    def test_ineligible_compliance_content_tagged_correctly(
        self,
        default_tagger: AutoPublishTagger,
        ineligible_compliance_request: TaggingRequest,
    ) -> None:
        """Non-compliant content should be tagged NOT_ELIGIBLE."""
        result = default_tagger.tag_content(ineligible_compliance_request)

        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert result.is_eligible is False
        assert result.display_message == ""

    def test_boundary_eligible_tagged(
        self,
        default_tagger: AutoPublishTagger,
        boundary_eligible_request: TaggingRequest,
    ) -> None:
        """Score at exactly 9.0 should be tagged WOULD_AUTO_PUBLISH."""
        result = default_tagger.tag_content(boundary_eligible_request)

        assert result.tag == AutoPublishTag.WOULD_AUTO_PUBLISH
        assert result.is_eligible is True

    def test_boundary_ineligible_tagged(
        self,
        default_tagger: AutoPublishTagger,
        boundary_ineligible_request: TaggingRequest,
    ) -> None:
        """Score at 8.9 should be tagged NOT_ELIGIBLE."""
        result = default_tagger.tag_content(boundary_ineligible_request)

        assert result.tag == AutoPublishTag.NOT_ELIGIBLE
        assert result.is_eligible is False


class TestConfigToggle:
    """Tests for auto-publish config toggles (Task 8.8)."""

    def test_config_default_all_disabled(self) -> None:
        """All content types should be disabled by default."""
        config = AutoPublishConfig()

        assert config.is_enabled("instagram_feed") is False
        assert config.is_enabled("instagram_story") is False
        assert config.is_enabled("instagram_reel") is False

    def test_config_explicit_enable_feed(self) -> None:
        """Explicitly enabled feed should return True."""
        config = AutoPublishConfig(instagram_feed_enabled=True)

        assert config.is_enabled("instagram_feed") is True
        assert config.is_enabled("instagram_story") is False
        assert config.is_enabled("instagram_reel") is False

    def test_config_explicit_enable_all(self) -> None:
        """All enabled should return True for all types."""
        config = AutoPublishConfig(
            instagram_feed_enabled=True,
            instagram_story_enabled=True,
            instagram_reel_enabled=True,
        )

        assert config.is_enabled("instagram_feed") is True
        assert config.is_enabled("instagram_story") is True
        assert config.is_enabled("instagram_reel") is True

    def test_config_unknown_content_type(self) -> None:
        """Unknown content type should return False."""
        config = AutoPublishConfig(instagram_feed_enabled=True)

        assert config.is_enabled("unknown_type") is False
        assert config.is_enabled("") is False

    def test_tagger_respects_config(
        self,
        enabled_config_tagger: AutoPublishTagger,
    ) -> None:
        """Tagger should delegate to config for enable check."""
        assert enabled_config_tagger.is_auto_publish_enabled("instagram_feed") is True
        assert enabled_config_tagger.is_auto_publish_enabled("instagram_story") is False
