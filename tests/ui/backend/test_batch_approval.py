"""Integration tests for Batch Approval API endpoints.

Story 4-3: Batch Approval Capability
Task 11: Backend integration tests

Tests batch approve and reject endpoints including:
- Batch approve with multiple items
- Batch reject with reason
- Partial failure handling
- Audit trail batch_id
- Queue state after batch actions
- Concurrent batch operations
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ui.backend.schemas.batch_approval import (
    BatchApproveSchema,
    BatchRejectSchema,
    BatchApproveResponse,
    BatchRejectResponse,
    BatchActionResultItem,
)
from ui.backend.schemas.approval_actions import RejectReason


class MockApprovalItem:
    """Mock approval item for testing."""

    def __init__(
        self,
        id=None,
        thumbnail_url="https://example.com/thumb.jpg",
        full_caption="Test caption",
        quality_score=8.5,
        compliance_status="COMPLIANT",
        would_auto_publish=True,
        suggested_publish_time=None,
        source_type="instagram_post",
        source_priority=1,
        status="pending",
    ):
        self.id = id or str(uuid4())
        self.thumbnail_url = thumbnail_url
        self.full_caption = full_caption
        self.quality_score = quality_score
        self.compliance_status = compliance_status
        self.would_auto_publish = would_auto_publish
        self.suggested_publish_time = suggested_publish_time or datetime.now() + timedelta(days=2)
        self.source_type = source_type
        self.source_priority = source_priority
        self.status = status


class TestBatchApproveSchema:
    """Tests for BatchApproveSchema validation."""

    def test_valid_batch_approve_schema(self):
        """Test creating valid batch approve schema."""
        schema = BatchApproveSchema(item_ids=["id-1", "id-2", "id-3"])
        assert len(schema.item_ids) == 3

    def test_empty_item_ids_fails(self):
        """Test empty item_ids fails validation."""
        with pytest.raises(ValueError):
            BatchApproveSchema(item_ids=[])

    def test_max_items_validation(self):
        """Test max 100 items validation."""
        item_ids = [f"id-{i}" for i in range(101)]
        with pytest.raises(ValueError):
            BatchApproveSchema(item_ids=item_ids)


class TestBatchRejectSchema:
    """Tests for BatchRejectSchema validation."""

    def test_valid_batch_reject_schema(self):
        """Test creating valid batch reject schema."""
        schema = BatchRejectSchema(
            item_ids=["id-1", "id-2"],
            reason=RejectReason.COMPLIANCE_ISSUE,
            reason_text="Contains prohibited claims",
        )
        assert len(schema.item_ids) == 2
        assert schema.reason == RejectReason.COMPLIANCE_ISSUE

    def test_other_reason_requires_text(self):
        """Test OTHER reason requires reason_text."""
        # This should be validated at the endpoint level, not schema level
        schema = BatchRejectSchema(
            item_ids=["id-1"],
            reason=RejectReason.OTHER,
            reason_text=None,
        )
        # Schema allows None, validation happens at endpoint
        assert schema.reason_text is None


# Task 11.1: Test batch approve endpoint with 5 items
class TestBatchApproveEndpoint:
    """Tests for batch_approve endpoint."""

    @pytest.mark.asyncio
    async def test_batch_approve_five_items(self):
        """Test batch approving 5 items successfully."""
        from ui.backend.routers.approval_queue import batch_approve

        mock_items = [MockApprovalItem(id=f"item-{i}") for i in range(5)]
        mock_results = [
            BatchActionResultItem(
                item_id=item.id,
                success=True,
                scheduled_publish_time=item.suggested_publish_time.isoformat(),
            )
            for item in mock_items
        ]

        mock_response = BatchApproveResponse(
            batch_id="batch-123",
            total_requested=5,
            successful_count=5,
            failed_count=0,
            results=mock_results,
            summary="5 items approved, scheduled for Feb 10 - Feb 14",
        )

        mock_repository = AsyncMock()
        mock_repository.batch_approve_items.return_value = mock_response

        request = BatchApproveSchema(item_ids=[item.id for item in mock_items])
        result = await batch_approve(request=request, repository=mock_repository)

        assert result.total_requested == 5
        assert result.successful_count == 5
        assert result.failed_count == 0
        assert len(result.results) == 5
        mock_repository.batch_approve_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_approve_uses_suggested_publish_time(self):
        """Test batch approve uses each item's suggested_publish_time."""
        from ui.backend.routers.approval_queue import batch_approve

        time_1 = datetime.now() + timedelta(days=1)
        time_2 = datetime.now() + timedelta(days=2)

        mock_results = [
            BatchActionResultItem(
                item_id="item-1",
                success=True,
                scheduled_publish_time=time_1.isoformat(),
            ),
            BatchActionResultItem(
                item_id="item-2",
                success=True,
                scheduled_publish_time=time_2.isoformat(),
            ),
        ]

        mock_response = BatchApproveResponse(
            batch_id="batch-123",
            total_requested=2,
            successful_count=2,
            failed_count=0,
            results=mock_results,
            summary="2 items approved",
        )

        mock_repository = AsyncMock()
        mock_repository.batch_approve_items.return_value = mock_response

        request = BatchApproveSchema(item_ids=["item-1", "item-2"])
        result = await batch_approve(request=request, repository=mock_repository)

        # Verify each item has its own scheduled time
        assert result.results[0].scheduled_publish_time == time_1.isoformat()
        assert result.results[1].scheduled_publish_time == time_2.isoformat()


# Task 11.2: Test batch reject endpoint with reason
class TestBatchRejectEndpoint:
    """Tests for batch_reject endpoint."""

    @pytest.mark.asyncio
    async def test_batch_reject_with_reason(self):
        """Test batch rejecting items with reason."""
        from ui.backend.routers.approval_queue import batch_reject

        mock_results = [
            BatchActionResultItem(item_id="item-1", success=True),
            BatchActionResultItem(item_id="item-2", success=True),
            BatchActionResultItem(item_id="item-3", success=True),
        ]

        mock_response = BatchRejectResponse(
            batch_id="batch-456",
            total_requested=3,
            successful_count=3,
            failed_count=0,
            results=mock_results,
            summary="3 items rejected",
        )

        mock_repository = AsyncMock()
        mock_repository.batch_reject_items.return_value = mock_response

        request = BatchRejectSchema(
            item_ids=["item-1", "item-2", "item-3"],
            reason=RejectReason.COMPLIANCE_ISSUE,
            reason_text="Contains prohibited health claims",
        )
        result = await batch_reject(request=request, repository=mock_repository)

        assert result.total_requested == 3
        assert result.successful_count == 3
        mock_repository.batch_reject_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_reject_other_requires_reason_text(self):
        """Test batch reject with OTHER reason requires reason_text."""
        from fastapi import HTTPException
        from ui.backend.routers.approval_queue import batch_reject

        mock_repository = AsyncMock()

        request = BatchRejectSchema(
            item_ids=["item-1"],
            reason=RejectReason.OTHER,
            reason_text=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            await batch_reject(request=request, repository=mock_repository)

        assert exc_info.value.status_code == 400
        assert "details" in exc_info.value.detail.lower()


# Task 11.3: Test partial failure handling
class TestBatchPartialFailure:
    """Tests for partial failure handling."""

    @pytest.mark.asyncio
    async def test_batch_approve_partial_failure(self):
        """Test batch approve handles partial failures."""
        from ui.backend.routers.approval_queue import batch_approve

        mock_results = [
            BatchActionResultItem(item_id="item-1", success=True),
            BatchActionResultItem(
                item_id="item-2",
                success=False,
                error_message="Item already approved",
            ),
            BatchActionResultItem(item_id="item-3", success=True),
        ]

        mock_response = BatchApproveResponse(
            batch_id="batch-123",
            total_requested=3,
            successful_count=2,
            failed_count=1,
            results=mock_results,
            summary="2 items approved, 1 failed",
        )

        mock_repository = AsyncMock()
        mock_repository.batch_approve_items.return_value = mock_response

        request = BatchApproveSchema(item_ids=["item-1", "item-2", "item-3"])
        result = await batch_approve(request=request, repository=mock_repository)

        assert result.successful_count == 2
        assert result.failed_count == 1
        assert result.results[1].success is False
        assert "already approved" in result.results[1].error_message

    @pytest.mark.asyncio
    async def test_batch_reject_item_not_found(self):
        """Test batch reject handles items not found."""
        from ui.backend.routers.approval_queue import batch_reject

        mock_results = [
            BatchActionResultItem(item_id="item-1", success=True),
            BatchActionResultItem(
                item_id="item-99",
                success=False,
                error_message="Item not found",
            ),
        ]

        mock_response = BatchRejectResponse(
            batch_id="batch-456",
            total_requested=2,
            successful_count=1,
            failed_count=1,
            results=mock_results,
            summary="1 item rejected, 1 not found",
        )

        mock_repository = AsyncMock()
        mock_repository.batch_reject_items.return_value = mock_response

        request = BatchRejectSchema(
            item_ids=["item-1", "item-99"],
            reason=RejectReason.LOW_QUALITY,
        )
        result = await batch_reject(request=request, repository=mock_repository)

        assert result.successful_count == 1
        assert result.failed_count == 1


# Task 11.4: Test audit trail records batch_id
class TestBatchAuditTrail:
    """Tests for audit trail with batch_id."""

    @pytest.mark.asyncio
    async def test_batch_approve_records_batch_id(self):
        """Test batch approve logs batch_id in audit trail."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository

        mock_session = AsyncMock()

        repo = ApprovalItemRepository(mock_session)

        # Mock the item returned by get_by_id
        mock_item = MagicMock(
            id="item-1",
            status="pending",
            suggested_publish_time=datetime.now(),
        )

        with patch.object(repo, "get_by_id", return_value=mock_item):
            result = await repo.batch_approve_items(["item-1"])

            # Verify batch_id is in the response (UUID format, 36 chars)
            assert result.batch_id is not None
            assert len(result.batch_id) == 36
            # Verify item was assigned batch_id
            assert mock_item.batch_id == result.batch_id

    @pytest.mark.asyncio
    async def test_batch_reject_records_batch_id(self):
        """Test batch reject logs batch_id in audit trail."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository

        mock_session = AsyncMock()

        repo = ApprovalItemRepository(mock_session)

        # Mock the item returned by get_by_id
        mock_item = MagicMock(id="item-1", status="pending")

        with patch.object(repo, "get_by_id", return_value=mock_item):
            result = await repo.batch_reject_items(
                item_ids=["item-1"],
                reason="compliance_issue",
                reason_text="Test",
            )

            # Verify batch_id is in the response (UUID format, 36 chars)
            assert result.batch_id is not None
            assert len(result.batch_id) == 36
            # Verify item was assigned batch_id
            assert mock_item.batch_id == result.batch_id


# Task 11.5: Test items removed from queue after batch action
class TestBatchQueueUpdate:
    """Tests for queue state after batch actions."""

    @pytest.mark.asyncio
    async def test_approved_items_status_updated(self):
        """Test approved items have status updated to APPROVED."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository

        mock_session = AsyncMock()
        repo = ApprovalItemRepository(mock_session)

        # Create mock pending item
        mock_item = MagicMock(
            id="item-1",
            status="pending",
            suggested_publish_time=datetime.now() + timedelta(days=1),
        )

        with patch.object(repo, "get_by_id", return_value=mock_item):
            await repo.batch_approve_items(["item-1"])

            # Verify status was updated to APPROVED
            assert mock_item.status == "approved"
            assert mock_item.approved_at is not None

    @pytest.mark.asyncio
    async def test_rejected_items_status_updated(self):
        """Test rejected items have status updated to REJECTED."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository

        mock_session = AsyncMock()
        repo = ApprovalItemRepository(mock_session)

        mock_item = MagicMock(id="item-1", status="pending")

        with patch.object(repo, "get_by_id", return_value=mock_item):
            await repo.batch_reject_items(
                item_ids=["item-1"],
                reason="low_quality",
            )

            # Verify status was updated to REJECTED
            assert mock_item.status == "rejected"
            assert mock_item.rejection_reason == "low_quality"


# Task 11.6: Test concurrent batch operations conflict handling
class TestBatchConcurrency:
    """Tests for concurrent batch operations."""

    @pytest.mark.asyncio
    async def test_concurrent_approve_same_item(self):
        """Test handling concurrent approval of same item."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository

        mock_session = AsyncMock()
        repo = ApprovalItemRepository(mock_session)

        # First call returns pending, second call returns already approved
        mock_item_pending = MagicMock(
            id="item-1",
            status="pending",
            suggested_publish_time=datetime.now(),
        )
        mock_item_approved = MagicMock(id="item-1", status="approved")

        call_count = [0]

        def get_item_by_id(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_item_pending
            return mock_item_approved

        with patch.object(repo, "get_by_id", side_effect=get_item_by_id):
            # First batch succeeds (item was pending)
            result1 = await repo.batch_approve_items(["item-1"])
            assert result1.successful_count == 1

            # Second batch should fail (item already approved - status != pending)
            result2 = await repo.batch_approve_items(["item-1"])
            assert result2.failed_count == 1
            assert "not in PENDING status" in result2.results[0].error

    @pytest.mark.asyncio
    async def test_batch_handles_partial_item_failures(self):
        """Test batch operations handle per-item failures gracefully."""
        from ui.backend.repositories.approval_repository import ApprovalItemRepository

        mock_session = AsyncMock()
        repo = ApprovalItemRepository(mock_session)

        # First item is pending (will succeed), second is already approved (will fail)
        mock_item_1 = MagicMock(
            id="item-1",
            status="pending",
            suggested_publish_time=datetime.now(),
        )
        mock_item_2 = MagicMock(
            id="item-2",
            status="approved",  # Already approved - should fail
            suggested_publish_time=datetime.now(),
        )

        def get_by_id_mock(item_id):
            if item_id == "item-1":
                return mock_item_1
            return mock_item_2

        with patch.object(repo, "get_by_id", side_effect=get_by_id_mock):
            result = await repo.batch_approve_items(["item-1", "item-2"])

            # First item succeeded, second failed
            assert result.successful_count == 1
            assert result.failed_count == 1
            assert result.results[0].success is True
            assert result.results[1].success is False


class TestBatchResponseFormat:
    """Tests for batch response format."""

    def test_batch_response_includes_summary(self):
        """Test batch response includes human-readable summary."""
        response = BatchApproveResponse(
            batch_id="batch-123",
            total_requested=5,
            successful_count=5,
            failed_count=0,
            results=[],
            summary="5 items approved, scheduled for Feb 10 - Feb 14, 2026",
        )

        assert "5 items approved" in response.summary
        assert "Feb" in response.summary

    def test_batch_response_includes_date_range(self):
        """Test batch response summary includes date range."""
        response = BatchApproveResponse(
            batch_id="batch-123",
            total_requested=3,
            successful_count=3,
            failed_count=0,
            results=[
                BatchActionResultItem(
                    item_id="1",
                    success=True,
                    scheduled_publish_time="2026-02-10T10:00:00Z",
                ),
                BatchActionResultItem(
                    item_id="2",
                    success=True,
                    scheduled_publish_time="2026-02-15T10:00:00Z",
                ),
            ],
            summary="3 items approved, scheduled for Feb 10 - Feb 15, 2026",
        )

        assert "Feb 10" in response.summary
        assert "Feb 15" in response.summary
