"""Tests for Approval Queue schemas.

Tests validation logic, color calculation, and schema constraints.
"""

from datetime import datetime

import pytest

from ui.backend.schemas.approval import (
    SourcePriority,
    ComplianceStatus,
    QualityColor,
    get_quality_color,
    ComplianceCheckSchema,
    QualityBreakdownSchema,
    ApprovalQueueItemSchema,
    ApprovalQueueResponse,
)


class TestSourcePriority:
    """Tests for SourcePriority enum."""

    def test_priority_values(self):
        """Verify priority order values."""
        assert SourcePriority.TRENDING == 1
        assert SourcePriority.SCHEDULED == 2
        assert SourcePriority.EVERGREEN == 3
        assert SourcePriority.RESEARCH == 4

    def test_priority_ordering(self):
        """Verify TRENDING has highest priority (lowest value)."""
        priorities = list(SourcePriority)
        assert sorted(priorities, key=lambda x: x.value) == [
            SourcePriority.TRENDING,
            SourcePriority.SCHEDULED,
            SourcePriority.EVERGREEN,
            SourcePriority.RESEARCH,
        ]


class TestComplianceStatus:
    """Tests for ComplianceStatus enum."""

    def test_status_values(self):
        """Verify compliance status values."""
        assert ComplianceStatus.COMPLIANT.value == "COMPLIANT"
        assert ComplianceStatus.WARNING.value == "WARNING"
        assert ComplianceStatus.REJECTED.value == "REJECTED"


class TestQualityColor:
    """Tests for quality color calculation."""

    @pytest.mark.parametrize(
        "score,expected_color",
        [
            (10.0, QualityColor.GREEN),
            (9.5, QualityColor.GREEN),
            (8.0, QualityColor.GREEN),
            (7.9, QualityColor.YELLOW),
            (7.0, QualityColor.YELLOW),
            (5.0, QualityColor.YELLOW),
            (4.9, QualityColor.RED),
            (3.0, QualityColor.RED),
            (0.0, QualityColor.RED),
        ],
    )
    def test_get_quality_color(self, score: float, expected_color: QualityColor):
        """Test quality color calculation for various scores."""
        assert get_quality_color(score) == expected_color

    def test_green_threshold_exact(self):
        """Score of exactly 8 should be green."""
        assert get_quality_color(8.0) == QualityColor.GREEN

    def test_yellow_threshold_exact(self):
        """Score of exactly 5 should be yellow."""
        assert get_quality_color(5.0) == QualityColor.YELLOW


class TestComplianceCheckSchema:
    """Tests for ComplianceCheckSchema."""

    def test_create_valid_schema(self):
        """Test creating a valid compliance check schema."""
        check = ComplianceCheckSchema(
            phrase="boosts immune system",
            status="prohibited",
            explanation="Health claim not approved under EC 1924/2006",
            regulation_reference="EC 1924/2006 Art. 10",
        )
        assert check.phrase == "boosts immune system"
        assert check.status == "prohibited"
        assert check.regulation_reference == "EC 1924/2006 Art. 10"

    def test_optional_regulation_reference(self):
        """Regulation reference should be optional."""
        check = ComplianceCheckSchema(
            phrase="functional mushrooms",
            status="permitted",
            explanation="No health claims detected",
        )
        assert check.regulation_reference is None


class TestQualityBreakdownSchema:
    """Tests for QualityBreakdownSchema."""

    def test_create_valid_breakdown(self):
        """Test creating a valid quality breakdown."""
        breakdown = QualityBreakdownSchema(
            compliance_score=9.0,
            brand_voice_score=8.5,
            visual_quality_score=7.0,
            platform_optimization_score=8.0,
            engagement_prediction_score=7.5,
            authenticity_score=8.0,
        )
        assert breakdown.compliance_score == 9.0
        assert breakdown.brand_voice_score == 8.5

    def test_score_bounds_validation(self):
        """Scores should be between 0 and 10."""
        with pytest.raises(ValueError):
            QualityBreakdownSchema(
                compliance_score=11.0,  # Invalid: > 10
                brand_voice_score=8.5,
                visual_quality_score=7.0,
                platform_optimization_score=8.0,
                engagement_prediction_score=7.5,
                authenticity_score=8.0,
            )

    def test_negative_score_validation(self):
        """Negative scores should be rejected."""
        with pytest.raises(ValueError):
            QualityBreakdownSchema(
                compliance_score=-1.0,  # Invalid: < 0
                brand_voice_score=8.5,
                visual_quality_score=7.0,
                platform_optimization_score=8.0,
                engagement_prediction_score=7.5,
                authenticity_score=8.0,
            )


class TestApprovalQueueItemSchema:
    """Tests for ApprovalQueueItemSchema."""

    @pytest.fixture
    def valid_item_data(self):
        """Create valid item data for testing."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "caption_excerpt": "Sample caption text",
            "full_caption": "Sample caption text with more details and hashtags #DAWO",
            "quality_score": 8.5,
            "quality_color": QualityColor.GREEN,
            "compliance_status": ComplianceStatus.COMPLIANT,
            "would_auto_publish": True,
            "suggested_publish_time": datetime(2026, 2, 10, 14, 0, 0),
            "source_type": "instagram_post",
            "source_priority": SourcePriority.TRENDING,
            "hashtags": ["#DAWO", "#mushrooms"],
            "created_at": datetime(2026, 2, 8, 10, 0, 0),
        }

    def test_create_valid_item(self, valid_item_data):
        """Test creating a valid approval queue item."""
        item = ApprovalQueueItemSchema(**valid_item_data)
        assert item.id == valid_item_data["id"]
        assert item.quality_score == 8.5
        assert item.quality_color == QualityColor.GREEN
        assert item.would_auto_publish is True
        assert len(item.hashtags) == 2

    def test_caption_excerpt_max_length(self, valid_item_data):
        """Caption excerpt should be max 100 characters."""
        valid_item_data["caption_excerpt"] = "x" * 101  # 101 chars
        with pytest.raises(ValueError):
            ApprovalQueueItemSchema(**valid_item_data)

    def test_optional_fields(self, valid_item_data):
        """Test optional fields can be None."""
        valid_item_data["suggested_publish_time"] = None
        valid_item_data["compliance_details"] = None
        valid_item_data["quality_breakdown"] = None
        item = ApprovalQueueItemSchema(**valid_item_data)
        assert item.suggested_publish_time is None
        assert item.compliance_details is None
        assert item.quality_breakdown is None

    def test_quality_score_bounds(self, valid_item_data):
        """Quality score should be between 0 and 10."""
        valid_item_data["quality_score"] = 11.0
        with pytest.raises(ValueError):
            ApprovalQueueItemSchema(**valid_item_data)


class TestApprovalQueueResponse:
    """Tests for ApprovalQueueResponse."""

    def test_create_empty_response(self):
        """Test creating an empty response."""
        response = ApprovalQueueResponse(
            items=[],
            total_count=0,
            next_cursor=None,
            has_more=False,
        )
        assert len(response.items) == 0
        assert response.total_count == 0
        assert response.has_more is False

    def test_create_response_with_items(self):
        """Test creating a response with items."""
        item = ApprovalQueueItemSchema(
            id="123e4567-e89b-12d3-a456-426614174000",
            thumbnail_url="https://example.com/thumb.jpg",
            caption_excerpt="Sample caption",
            full_caption="Sample caption with details",
            quality_score=7.0,
            quality_color=QualityColor.YELLOW,
            compliance_status=ComplianceStatus.WARNING,
            would_auto_publish=False,
            source_type="instagram_post",
            source_priority=SourcePriority.EVERGREEN,
            created_at=datetime.now(),
        )
        response = ApprovalQueueResponse(
            items=[item],
            total_count=1,
            next_cursor=None,
            has_more=False,
        )
        assert len(response.items) == 1
        assert response.total_count == 1

    def test_response_with_pagination(self):
        """Test response with pagination cursor."""
        response = ApprovalQueueResponse(
            items=[],
            total_count=100,
            next_cursor="eyJwcmlvcml0eSI6MX0=",
            has_more=True,
        )
        assert response.has_more is True
        assert response.next_cursor is not None
