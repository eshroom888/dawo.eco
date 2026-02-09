"""Integration tests for Approval Queue API router.

Tests API endpoint behavior, schema validation, sorting, and pagination.
Uses pytest-asyncio for async test support.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ui.backend.routers.approval_queue import (
    router,
    get_approval_queue,
    get_approval_item,
    approve_item,
    reject_item,
    edit_item,
    apply_rewrite,
    get_edit_history,
    _transform_to_queue_item,
)
from ui.backend.schemas.approval import (
    SourcePriority,
    ComplianceStatus,
    QualityColor,
    ApprovalQueueResponse,
    ApprovalQueueItemSchema,
)
from ui.backend.schemas.approval_actions import (
    RejectReason,
    ApproveActionSchema,
    RejectActionSchema,
    EditActionSchema,
    ApplyRewriteSchema,
)


class MockApprovalItem:
    """Mock approval item for testing."""

    def __init__(
        self,
        id=None,
        thumbnail_url="https://example.com/thumb.jpg",
        full_caption="Test caption with #hashtags",
        hashtags=None,
        quality_score=8.5,
        compliance_status="COMPLIANT",
        compliance_details=None,
        quality_breakdown=None,
        would_auto_publish=True,
        suggested_publish_time=None,
        source_type="instagram_post",
        source_priority=1,
        created_at=None,
        # Story 4-2 fields
        status="pending",
        original_caption=None,
        rewrite_suggestions=None,
        rejection_reason=None,
        rejection_text=None,
        approved_at=None,
        approved_by=None,
        scheduled_publish_time=None,
    ):
        self.id = id or uuid4()
        self.thumbnail_url = thumbnail_url
        self.full_caption = full_caption
        self.hashtags = hashtags or ["#test", "#DAWO"]
        self.quality_score = quality_score
        self.compliance_status = compliance_status
        self.compliance_details = compliance_details
        self.quality_breakdown = quality_breakdown
        self.would_auto_publish = would_auto_publish
        self.suggested_publish_time = suggested_publish_time or datetime.now()
        self.source_type = source_type
        self.source_priority = source_priority
        self.created_at = created_at or datetime.now()
        # Story 4-2 fields
        self.status = status
        self.original_caption = original_caption
        self.rewrite_suggestions = rewrite_suggestions
        self.rejection_reason = rejection_reason
        self.rejection_text = rejection_text
        self.approved_at = approved_at
        self.approved_by = approved_by
        self.scheduled_publish_time = scheduled_publish_time


class MockEditHistoryItem:
    """Mock edit history item for testing."""

    def __init__(
        self,
        id=None,
        previous_caption="Previous caption",
        new_caption="New caption",
        edited_at=None,
        editor="operator",
    ):
        self.id = id or uuid4()
        self.previous_caption = previous_caption
        self.new_caption = new_caption
        self.edited_at = edited_at or datetime.now()
        self.editor = editor


class TestTransformToQueueItem:
    """Tests for _transform_to_queue_item function."""

    def test_transforms_basic_fields(self):
        """Test basic field transformation."""
        mock_item = MockApprovalItem()
        result = _transform_to_queue_item(mock_item)

        assert result.id == str(mock_item.id)
        assert result.thumbnail_url == mock_item.thumbnail_url
        assert result.full_caption == mock_item.full_caption
        assert result.quality_score == mock_item.quality_score

    def test_calculates_quality_color_green(self):
        """Test green quality color for score >= 8."""
        mock_item = MockApprovalItem(quality_score=8.5)
        result = _transform_to_queue_item(mock_item)
        assert result.quality_color == QualityColor.GREEN

    def test_calculates_quality_color_yellow(self):
        """Test yellow quality color for score >= 5 and < 8."""
        mock_item = MockApprovalItem(quality_score=6.0)
        result = _transform_to_queue_item(mock_item)
        assert result.quality_color == QualityColor.YELLOW

    def test_calculates_quality_color_red(self):
        """Test red quality color for score < 5."""
        mock_item = MockApprovalItem(quality_score=3.0)
        result = _transform_to_queue_item(mock_item)
        assert result.quality_color == QualityColor.RED

    def test_truncates_caption_excerpt(self):
        """Test caption excerpt is truncated to 100 chars."""
        long_caption = "x" * 150
        mock_item = MockApprovalItem(full_caption=long_caption)
        result = _transform_to_queue_item(mock_item)

        assert len(result.caption_excerpt) == 100
        assert result.full_caption == long_caption

    def test_preserves_short_caption_excerpt(self):
        """Test short captions are preserved in excerpt."""
        short_caption = "Short caption"
        mock_item = MockApprovalItem(full_caption=short_caption)
        result = _transform_to_queue_item(mock_item)

        assert result.caption_excerpt == short_caption

    def test_excludes_details_by_default(self):
        """Test compliance_details and quality_breakdown excluded by default."""
        mock_item = MockApprovalItem(
            compliance_details=[{"phrase": "test", "status": "permitted", "explanation": "ok"}],
            quality_breakdown={"compliance_score": 9.0},
        )
        result = _transform_to_queue_item(mock_item, include_details=False)

        assert result.compliance_details is None
        assert result.quality_breakdown is None

    def test_includes_details_when_requested(self):
        """Test details included when include_details=True."""
        details = [{"phrase": "test", "status": "permitted", "explanation": "ok"}]
        breakdown = {
            "compliance_score": 9.0,
            "brand_voice_score": 8.5,
            "visual_quality_score": 7.0,
            "platform_optimization_score": 8.0,
            "engagement_prediction_score": 7.5,
            "authenticity_score": 8.0,
        }
        mock_item = MockApprovalItem(
            compliance_details=details,
            quality_breakdown=breakdown,
        )
        result = _transform_to_queue_item(mock_item, include_details=True)

        # Check compliance details are included
        assert result.compliance_details is not None
        assert len(result.compliance_details) == 1
        assert result.compliance_details[0].phrase == "test"
        # Check quality breakdown is included
        assert result.quality_breakdown is not None
        assert result.quality_breakdown.compliance_score == 9.0


class TestApprovalQueueResponse:
    """Tests for ApprovalQueueResponse schema."""

    def test_response_with_items(self):
        """Test response schema with items."""
        item = ApprovalQueueItemSchema(
            id="test-id",
            thumbnail_url="https://example.com/thumb.jpg",
            caption_excerpt="Test caption",
            full_caption="Test caption with more text",
            quality_score=8.0,
            quality_color=QualityColor.GREEN,
            compliance_status=ComplianceStatus.COMPLIANT,
            would_auto_publish=True,
            source_type="instagram_post",
            source_priority=SourcePriority.TRENDING,
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
        assert response.has_more is False

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


class TestSourcePrioritySorting:
    """Tests for source priority ordering."""

    def test_priority_enum_values(self):
        """Test priority enum has correct values."""
        assert SourcePriority.TRENDING == 1
        assert SourcePriority.SCHEDULED == 2
        assert SourcePriority.EVERGREEN == 3
        assert SourcePriority.RESEARCH == 4

    def test_priority_comparison(self):
        """Test priority comparison for sorting."""
        assert SourcePriority.TRENDING < SourcePriority.SCHEDULED
        assert SourcePriority.SCHEDULED < SourcePriority.EVERGREEN
        assert SourcePriority.EVERGREEN < SourcePriority.RESEARCH


class TestPaginationCursor:
    """Tests for cursor-based pagination."""

    def test_cursor_encoding_decoding(self):
        """Test cursor encoding and decoding."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        repo = ApprovalItemRepository(mock_session)

        # Encode cursor
        test_time = datetime(2026, 2, 8, 12, 0, 0)
        cursor = repo._encode_cursor(
            priority=1,
            time=test_time,
            item_id="test-uuid",
        )

        # Decode cursor
        decoded = repo._decode_cursor(cursor)

        assert decoded["priority"] == 1
        assert decoded["id"] == "test-uuid"
        assert decoded["time"] == test_time

    def test_invalid_cursor_returns_none(self):
        """Test invalid cursor returns None."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        repo = ApprovalItemRepository(mock_session)

        result = repo._decode_cursor("invalid-cursor")
        assert result is None


class TestApprovalItemSchema:
    """Tests for ApprovalQueueItemSchema validation."""

    def test_valid_schema(self):
        """Test creating valid schema."""
        item = ApprovalQueueItemSchema(
            id="test-id",
            thumbnail_url="https://example.com/thumb.jpg",
            caption_excerpt="Test caption",
            full_caption="Test caption with more text",
            quality_score=8.0,
            quality_color=QualityColor.GREEN,
            compliance_status=ComplianceStatus.COMPLIANT,
            would_auto_publish=True,
            source_type="instagram_post",
            source_priority=SourcePriority.TRENDING,
            created_at=datetime.now(),
        )
        assert item.quality_score == 8.0

    def test_quality_score_max_validation(self):
        """Test quality score max of 10."""
        with pytest.raises(ValueError):
            ApprovalQueueItemSchema(
                id="test-id",
                thumbnail_url="https://example.com/thumb.jpg",
                caption_excerpt="Test caption",
                full_caption="Test caption with more text",
                quality_score=11.0,  # Invalid: > 10
                quality_color=QualityColor.GREEN,
                compliance_status=ComplianceStatus.COMPLIANT,
                would_auto_publish=True,
                source_type="instagram_post",
                source_priority=SourcePriority.TRENDING,
                created_at=datetime.now(),
            )

    def test_caption_excerpt_max_length(self):
        """Test caption excerpt max length of 100."""
        with pytest.raises(ValueError):
            ApprovalQueueItemSchema(
                id="test-id",
                thumbnail_url="https://example.com/thumb.jpg",
                caption_excerpt="x" * 101,  # Invalid: > 100
                full_caption="Test caption with more text",
                quality_score=8.0,
                quality_color=QualityColor.GREEN,
                compliance_status=ComplianceStatus.COMPLIANT,
                would_auto_publish=True,
                source_type="instagram_post",
                source_priority=SourcePriority.TRENDING,
                created_at=datetime.now(),
            )


# Story 4-2: Approval Action Tests
class TestApproveAction:
    """Tests for approve_item endpoint."""

    @pytest.mark.asyncio
    async def test_approve_success(self):
        """Test successful approval."""
        mock_item = MockApprovalItem(status="approved")
        mock_item.scheduled_publish_time = datetime.now() + timedelta(hours=2)

        mock_repository = AsyncMock()
        mock_repository.approve_item.return_value = mock_item

        request = ApproveActionSchema()
        result = await approve_item(
            item_id=str(mock_item.id),
            request=request,
            repository=mock_repository,
        )

        assert result.success is True
        assert result.item_id == str(mock_item.id)
        assert "approved" in result.message.lower()
        mock_repository.approve_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_with_custom_time(self):
        """Test approval with custom publish time."""
        mock_item = MockApprovalItem(status="approved")
        custom_time = datetime.now() + timedelta(days=1)
        mock_item.scheduled_publish_time = custom_time

        mock_repository = AsyncMock()
        mock_repository.approve_item.return_value = mock_item

        request = ApproveActionSchema(scheduled_publish_time=custom_time)
        result = await approve_item(
            item_id=str(mock_item.id),
            request=request,
            repository=mock_repository,
        )

        assert result.success is True
        mock_repository.approve_item.assert_called_once_with(
            item_id=str(mock_item.id),
            scheduled_publish_time=custom_time,
            operator_id="operator",
        )

    @pytest.mark.asyncio
    async def test_approve_invalid_state(self):
        """Test approval fails for already approved item."""
        from fastapi import HTTPException

        mock_repository = AsyncMock()
        mock_repository.approve_item.side_effect = ValueError("Item already approved")

        request = ApproveActionSchema()

        with pytest.raises(HTTPException) as exc_info:
            await approve_item(
                item_id="test-id",
                request=request,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 400


class TestRejectAction:
    """Tests for reject_item endpoint."""

    @pytest.mark.asyncio
    async def test_reject_success(self):
        """Test successful rejection with reason."""
        mock_item = MockApprovalItem(
            status="rejected",
            rejection_reason="compliance_issue",
        )

        mock_repository = AsyncMock()
        mock_repository.reject_item.return_value = mock_item

        request = RejectActionSchema(
            reason=RejectReason.COMPLIANCE_ISSUE,
            reason_text="Contains prohibited health claims",
        )
        result = await reject_item(
            item_id=str(mock_item.id),
            request=request,
            repository=mock_repository,
        )

        assert result.success is True
        assert result.item_id == str(mock_item.id)
        assert "rejected" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reject_other_requires_text(self):
        """Test OTHER reason requires reason_text."""
        from fastapi import HTTPException

        mock_repository = AsyncMock()

        request = RejectActionSchema(
            reason=RejectReason.OTHER,
            reason_text=None,  # Missing required text
        )

        with pytest.raises(HTTPException) as exc_info:
            await reject_item(
                item_id="test-id",
                request=request,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 400
        assert "details" in exc_info.value.detail.lower()


class TestEditAction:
    """Tests for edit_item endpoint."""

    @pytest.mark.asyncio
    async def test_edit_success(self):
        """Test successful caption edit."""
        mock_item = MockApprovalItem(
            full_caption="Updated caption text",
            status="pending",
        )

        mock_repository = AsyncMock()
        mock_repository.update_caption.return_value = mock_item

        request = EditActionSchema(
            caption="Updated caption text",
            hashtags=["DAWO", "wellness"],
        )
        result = await edit_item(
            item_id=str(mock_item.id),
            request=request,
            repository=mock_repository,
        )

        assert result.success is True
        assert result.item_id == str(mock_item.id)
        assert "updated" in result.message.lower()

    @pytest.mark.asyncio
    async def test_edit_empty_caption_fails(self):
        """Test edit fails with empty caption."""
        # Pydantic validation should fail for empty caption
        with pytest.raises(ValueError):
            EditActionSchema(
                caption="",  # Empty - should fail validation
            )


class TestApplyRewriteAction:
    """Tests for apply_rewrite endpoint."""

    @pytest.mark.asyncio
    async def test_apply_rewrite_success(self):
        """Test applying AI rewrite suggestions."""
        original_caption = "Original text that needs improvement in the middle here."
        mock_item = MockApprovalItem(
            full_caption=original_caption,
            rewrite_suggestions=[
                {
                    "id": "sug-1",
                    "original_text": "needs improvement",
                    "suggested_text": "is now improved",
                    "reason": "Better compliance",
                    "type": "compliance",
                }
            ],
        )

        updated_item = MockApprovalItem(
            full_caption="Original text that is now improved in the middle here.",
        )

        mock_repository = AsyncMock()
        mock_repository.get_by_id.return_value = mock_item
        mock_repository.update_caption.return_value = updated_item

        request = ApplyRewriteSchema(suggestion_ids=["sug-1"])
        result = await apply_rewrite(
            item_id=str(mock_item.id),
            request=request,
            repository=mock_repository,
        )

        assert result.success is True
        assert "1" in result.message  # "Applied 1 suggestion(s)"
        mock_repository.update_caption.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_rewrite_invalid_suggestion_id(self):
        """Test applying invalid suggestion ID fails."""
        from fastapi import HTTPException

        mock_item = MockApprovalItem(
            rewrite_suggestions=[
                {"id": "sug-1", "original_text": "test", "suggested_text": "test2"}
            ],
        )

        mock_repository = AsyncMock()
        mock_repository.get_by_id.return_value = mock_item

        request = ApplyRewriteSchema(suggestion_ids=["invalid-id"])

        with pytest.raises(HTTPException) as exc_info:
            await apply_rewrite(
                item_id=str(mock_item.id),
                request=request,
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 400
        assert "invalid" in exc_info.value.detail.lower()


class TestEditHistory:
    """Tests for get_edit_history endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_success(self):
        """Test retrieving edit history."""
        mock_item = MockApprovalItem()
        mock_edits = [
            MockEditHistoryItem(
                previous_caption="Version 1",
                new_caption="Version 2",
                edited_at=datetime.now() - timedelta(hours=2),
            ),
            MockEditHistoryItem(
                previous_caption="Version 2",
                new_caption="Version 3",
                edited_at=datetime.now() - timedelta(hours=1),
            ),
        ]

        mock_repository = AsyncMock()
        mock_repository.get_by_id.return_value = mock_item
        mock_repository.get_edit_history.return_value = mock_edits

        result = await get_edit_history(
            item_id=str(mock_item.id),
            repository=mock_repository,
        )

        assert len(result) == 2
        assert result[0].previous_caption == "Version 1"
        assert result[1].new_caption == "Version 3"

    @pytest.mark.asyncio
    async def test_get_history_item_not_found(self):
        """Test history request for non-existent item."""
        from fastapi import HTTPException

        mock_repository = AsyncMock()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_edit_history(
                item_id="non-existent-id",
                repository=mock_repository,
            )

        assert exc_info.value.status_code == 404


class TestRejectReasonSchema:
    """Tests for RejectActionSchema validation."""

    def test_valid_reject_schema(self):
        """Test creating valid reject schema."""
        schema = RejectActionSchema(
            reason=RejectReason.COMPLIANCE_ISSUE,
            reason_text="Contains prohibited claims",
        )
        assert schema.reason == RejectReason.COMPLIANCE_ISSUE

    def test_reason_text_max_length(self):
        """Test reason_text max length of 500."""
        with pytest.raises(ValueError):
            RejectActionSchema(
                reason=RejectReason.OTHER,
                reason_text="x" * 501,  # Invalid: > 500
            )

    def test_all_reject_reasons_valid(self):
        """Test all rejection reasons are valid."""
        for reason in RejectReason:
            schema = RejectActionSchema(
                reason=reason,
                reason_text="Test reason" if reason == RejectReason.OTHER else None,
            )
            assert schema.reason == reason


class TestApplyRewriteSchema:
    """Tests for ApplyRewriteSchema validation."""

    def test_valid_apply_rewrite_schema(self):
        """Test creating valid apply rewrite schema."""
        schema = ApplyRewriteSchema(suggestion_ids=["sug-1", "sug-2"])
        assert len(schema.suggestion_ids) == 2

    def test_empty_suggestion_ids_fails(self):
        """Test empty suggestion_ids fails validation."""
        with pytest.raises(ValueError):
            ApplyRewriteSchema(suggestion_ids=[])
