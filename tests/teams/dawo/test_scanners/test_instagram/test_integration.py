"""Integration tests for Instagram Research Pipeline.

Tests the data flow and component interactions.
Verifies Research Pool schema compliance and CleanMarket flagging.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from teams.dawo.scanners.instagram import (
    InstagramScanner,
    InstagramScannerConfig,
    InstagramHarvester,
    InstagramResearchPipeline,
    PipelineStatus,
    RawInstagramPost,
    HarvestedPost,
    ThemeResult,
    ClaimDetectionResult,
    DetectedClaim,
    ClaimCategory,
)
from teams.dawo.research import ResearchSource, ComplianceStatus, TransformedResearch


class TestResearchPoolSchemaCompliance:
    """Tests for Research Pool schema compliance."""

    def test_transformed_research_has_instagram_source(self):
        """Test that transformed items have source=instagram."""
        item = TransformedResearch(
            source=ResearchSource.INSTAGRAM,
            title="Test Instagram Post",
            content="Test content",
            url="https://instagram.com/p/TEST/",
            tags=["test"],
            source_metadata={},
            created_at=datetime.now(timezone.utc),
            score=5.0,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        assert item.source == ResearchSource.INSTAGRAM

    def test_transformed_research_has_all_required_fields(self):
        """Test that TransformedResearch has all required fields for Research Pool."""
        item = TransformedResearch(
            source=ResearchSource.INSTAGRAM,
            title="Test Instagram Post from @testuser",
            content="Test caption with #hashtags",
            url="https://instagram.com/p/ABC123/",
            tags=["hashtags", "test"],
            source_metadata={
                "account_name": "testuser",
                "likes": 100,
                "comments": 10,
                "is_competitor": False,
            },
            created_at=datetime.now(timezone.utc),
            score=7.5,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        # Verify all required fields exist and are correct types
        assert item.source is not None
        assert isinstance(item.title, str) and len(item.title) > 0
        assert isinstance(item.content, str)
        assert isinstance(item.url, str) and item.url.startswith("http")
        assert isinstance(item.tags, list)
        assert isinstance(item.source_metadata, dict)
        assert isinstance(item.created_at, datetime)
        assert isinstance(item.score, float) and 0 <= item.score <= 10
        assert item.compliance_status in [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.WARNING,
            ComplianceStatus.REJECTED,
        ]

    def test_instagram_metadata_fields(self):
        """Test that Instagram-specific metadata fields are captured."""
        metadata = {
            "media_id": "17841563789012345",
            "account_name": "wellness_brand",
            "account_type": "business",
            "likes": 1500,
            "comments": 45,
            "media_type": "IMAGE",
            "is_competitor": True,
            "hashtag_source": "lionsmane",
        }

        item = TransformedResearch(
            source=ResearchSource.INSTAGRAM,
            title="Test Post",
            content="Test content",
            url="https://instagram.com/p/TEST/",
            tags=["lionsmane"],
            source_metadata=metadata,
            created_at=datetime.now(timezone.utc),
            score=5.0,
            compliance_status=ComplianceStatus.COMPLIANT,
        )

        assert item.source_metadata["account_name"] == "wellness_brand"
        assert item.source_metadata["likes"] == 1500
        assert item.source_metadata["is_competitor"] is True


class TestCleanMarketFlagging:
    """Tests for CleanMarket integration point."""

    def test_claim_detection_result_with_claims(self, sample_claim_detection_result):
        """Test that ClaimDetectionResult properly flags claims for review."""
        result = sample_claim_detection_result

        assert result.requires_cleanmarket_review is True
        assert len(result.claims_detected) > 0
        assert result.overall_risk_level in ["low", "medium", "high"]

    def test_claim_detection_result_clean(self, sample_claim_detection_result_clean):
        """Test that clean content doesn't get flagged."""
        result = sample_claim_detection_result_clean

        assert result.requires_cleanmarket_review is False
        assert len(result.claims_detected) == 0
        assert result.overall_risk_level == "none"

    def test_detected_claim_structure(self):
        """Test DetectedClaim structure for CleanMarket queue."""
        claim = DetectedClaim(
            claim_text="boosts brain power",
            category=ClaimCategory.ENHANCEMENT,
            confidence=0.92,
            severity="medium",
        )

        assert claim.claim_text == "boosts brain power"
        assert claim.category == ClaimCategory.ENHANCEMENT
        assert 0 <= claim.confidence <= 1.0
        assert claim.severity in ["low", "medium", "high"]

    def test_cleanmarket_metadata_structure(self):
        """Test metadata structure expected by CleanMarket (Epic 6)."""
        # Metadata format expected when claims are detected
        detected_claims = [
            {
                "text": "boosts immunity",
                "category": "enhancement",
                "severity": "medium",
            },
            {
                "text": "prevents cognitive decline",
                "category": "prevention",
                "severity": "high",
            },
        ]

        item = TransformedResearch(
            source=ResearchSource.INSTAGRAM,
            title="Competitor Post with Claims",
            content="Our mushroom extract boosts immunity and prevents cognitive decline!",
            url="https://instagram.com/p/COMPETITOR/",
            tags=["competitor", "health_claims"],
            source_metadata={
                "account_name": "competitor_brand",
                "is_competitor": True,
                "detected_claims": detected_claims,
                "cleanmarket_summary": "Multiple health claims detected - review required",
            },
            created_at=datetime.now(timezone.utc),
            score=6.0,
            compliance_status=ComplianceStatus.WARNING,
        )

        # Verify CleanMarket can access claim data
        assert item.source_metadata.get("detected_claims") is not None
        assert len(item.source_metadata["detected_claims"]) == 2
        assert item.source_metadata["detected_claims"][0]["severity"] == "medium"
        assert item.source_metadata["cleanmarket_summary"] is not None


class TestEngagementScoring:
    """Tests for engagement-based score boosting."""

    def test_low_engagement_no_boost(self):
        """Test that low engagement posts get no boost."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline

        # Create minimal pipeline for testing scoring method
        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        boost = pipeline._calculate_engagement_boost({"likes": 100, "comments": 10})
        assert boost == 0.0

    def test_medium_engagement_small_boost(self):
        """Test that medium engagement posts get small boost."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline

        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        # 500 likes + 50 comments*5 = 750 engagement
        boost = pipeline._calculate_engagement_boost({"likes": 500, "comments": 50})
        assert boost == 0.5

    def test_high_engagement_full_boost(self):
        """Test that viral posts get maximum boost."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline

        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        # 10000 likes = viral level engagement
        boost = pipeline._calculate_engagement_boost({"likes": 10000, "comments": 500})
        assert boost == 2.0

    def test_engagement_boost_caps_at_max(self):
        """Test that engagement boost doesn't exceed 2.0."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline

        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        # Massive engagement should still cap at 2.0
        boost = pipeline._calculate_engagement_boost({"likes": 1000000, "comments": 50000})
        assert boost <= 2.0


class TestPipelineStatusDetermination:
    """Tests for pipeline status determination logic."""

    def test_complete_status_all_published(self):
        """Test COMPLETE status when all items are published."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline
        from teams.dawo.scanners.instagram.schemas import PipelineStatistics

        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        stats = PipelineStatistics(
            total_found=10,
            harvested=10,
            transformed=10,
            validated=10,
            scored=10,
            published=10,
            failed=0,
        )

        status = pipeline._determine_status(stats)
        assert status == PipelineStatus.COMPLETE

    def test_partial_status_some_failed(self):
        """Test PARTIAL status when some items failed."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline
        from teams.dawo.scanners.instagram.schemas import PipelineStatistics

        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        stats = PipelineStatistics(
            total_found=10,
            harvested=10,
            transformed=10,
            validated=10,
            scored=10,
            published=8,
            failed=2,
        )

        status = pipeline._determine_status(stats)
        assert status == PipelineStatus.PARTIAL

    def test_failed_status_none_published(self):
        """Test FAILED status when no items were published."""
        from teams.dawo.scanners.instagram.pipeline import InstagramResearchPipeline
        from teams.dawo.scanners.instagram.schemas import PipelineStatistics

        pipeline = InstagramResearchPipeline(
            scanner=MagicMock(),
            harvester=MagicMock(),
            transformer=MagicMock(),
            validator=MagicMock(),
            scorer=MagicMock(),
            publisher=MagicMock(),
        )

        stats = PipelineStatistics(
            total_found=10,
            harvested=0,
            transformed=0,
            validated=0,
            scored=0,
            published=0,
            failed=10,
        )

        status = pipeline._determine_status(stats)
        assert status == PipelineStatus.FAILED


class TestThemeExtractionSchemas:
    """Tests for theme extraction data structures."""

    def test_theme_result_structure(self, sample_theme_result):
        """Test ThemeResult structure matches expected format."""
        result = sample_theme_result

        assert result.content_type in ["educational", "promotional", "lifestyle", "testimonial"]
        assert isinstance(result.messaging_patterns, list)
        assert isinstance(result.detected_products, list)
        assert isinstance(result.influencer_indicators, bool)
        assert isinstance(result.key_topics, list)
        assert 0 <= result.confidence_score <= 1.0

    def test_theme_result_content_types(self):
        """Test all valid content types."""
        valid_types = ["educational", "promotional", "lifestyle", "testimonial"]

        for content_type in valid_types:
            result = ThemeResult(
                content_type=content_type,
                messaging_patterns=[],
                detected_products=[],
                influencer_indicators=False,
                key_topics=[],
                confidence_score=0.8,
            )
            assert result.content_type == content_type


class TestPrivacyCompliance:
    """Tests for privacy/copyright compliance."""

    def test_harvested_post_no_image_url(self, sample_harvested_post):
        """Test that HarvestedPost does not have image_url field."""
        post = sample_harvested_post

        # Verify no image storage fields exist
        assert not hasattr(post, "image_url")
        assert not hasattr(post, "media_data")
        assert not hasattr(post, "image_data")

    def test_harvested_post_stores_text_only(self, sample_harvested_post):
        """Test that HarvestedPost only stores text and metadata."""
        post = sample_harvested_post

        # These fields should exist (text/metadata)
        assert hasattr(post, "caption")
        assert hasattr(post, "hashtags")
        assert hasattr(post, "likes")
        assert hasattr(post, "comments")
        assert hasattr(post, "account_name")
        assert hasattr(post, "permalink")

        # media_type is for stats only, not content storage
        assert post.media_type in ["IMAGE", "VIDEO", "CAROUSEL_ALBUM"]


class TestRateLimitHandling:
    """Tests for rate limit status handling."""

    def test_rate_limited_status_value(self):
        """Test that RATE_LIMITED status exists."""
        assert PipelineStatus.RATE_LIMITED.value == "RATE_LIMITED"

    def test_incomplete_status_value(self):
        """Test that INCOMPLETE status exists for API failures."""
        assert PipelineStatus.INCOMPLETE.value == "INCOMPLETE"
