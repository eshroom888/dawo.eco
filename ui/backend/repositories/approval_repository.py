"""Database repository for Approval Queue operations.

Provides async database access for approval items with
source-based priority sorting, cursor-based pagination,
and action operations (approve, reject, edit).

Performance Target:
    Queries complete in < 500ms for queues up to 10,000 items
    Actions complete in < 2 seconds
"""

import base64
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ui.backend.schemas.approval import SourcePriority
from ui.backend.schemas.batch_approval import (
    BatchApproveResponse,
    BatchRejectResponse,
    BatchActionResultItem,
)

logger = logging.getLogger(__name__)


class ApprovalItemRepository:
    """Repository for approval queue database operations.

    Provides methods for querying, retrieving, and modifying approval items
    with efficient pagination and sorting.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations
        """
        self._session = session

    async def get_pending_items(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> tuple[list, int, Optional[str]]:
        """Get pending approval items with priority sorting and pagination.

        Items are sorted by:
        1. source_priority ASC (TRENDING=1 first)
        2. suggested_publish_time ASC (earliest first within priority)

        Args:
            limit: Maximum number of items to return
            cursor: Base64-encoded pagination cursor from previous request

        Returns:
            Tuple of (items, total_count, next_cursor)
        """
        # Import here to avoid circular dependency
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            logger.warning("ApprovalItem model not yet available")
            return [], 0, None

        # Parse cursor if provided
        cursor_data = self._decode_cursor(cursor) if cursor else None

        # Build base query for pending items
        query = (
            select(ApprovalItem)
            .where(ApprovalItem.status == ApprovalStatus.PENDING)
            .order_by(
                ApprovalItem.source_priority.asc(),
                ApprovalItem.suggested_publish_time.asc(),
                ApprovalItem.id.asc(),  # Stable sort for pagination
            )
        )

        # Apply cursor filter if provided
        if cursor_data:
            query = query.where(
                (ApprovalItem.source_priority > cursor_data["priority"])
                | (
                    (ApprovalItem.source_priority == cursor_data["priority"])
                    & (ApprovalItem.suggested_publish_time > cursor_data["time"])
                )
                | (
                    (ApprovalItem.source_priority == cursor_data["priority"])
                    & (ApprovalItem.suggested_publish_time == cursor_data["time"])
                    & (ApprovalItem.id > UUID(cursor_data["id"]))
                )
            )

        # Add limit + 1 to check if more items exist
        query = query.limit(limit + 1)

        # Execute query
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        # Get total count
        count_query = (
            select(func.count())
            .select_from(ApprovalItem)
            .where(ApprovalItem.status == ApprovalStatus.PENDING)
        )
        count_result = await self._session.execute(count_query)
        total_count = count_result.scalar() or 0

        # Determine if there are more items
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]  # Remove extra item

        # Generate next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = self._encode_cursor(
                priority=last_item.source_priority,
                time=last_item.suggested_publish_time,
                item_id=str(last_item.id),
            )

        return items, total_count, next_cursor

    async def get_by_id(self, item_id: str) -> Optional[object]:
        """Get single approval item by ID.

        Args:
            item_id: Unique identifier of the approval item

        Returns:
            ApprovalItem if found, None otherwise
        """
        try:
            from core.approval.models import ApprovalItem
        except ImportError:
            logger.warning("ApprovalItem model not yet available")
            return None

        query = select(ApprovalItem).where(ApprovalItem.id == UUID(item_id))
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def approve_item(
        self,
        item_id: str,
        scheduled_publish_time: Optional[datetime] = None,
        operator_id: str = "operator",
    ) -> object:
        """Approve an item and move to scheduled queue.

        Args:
            item_id: Unique identifier of the approval item
            scheduled_publish_time: Override for publish time (uses suggested if None)
            operator_id: Who approved the item

        Returns:
            Updated ApprovalItem

        Raises:
            ValueError: If item not found or not in valid state
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            raise ValueError("ApprovalItem model not available")

        item = await self.get_by_id(item_id)
        if not item:
            raise ValueError(f"Approval item not found: {item_id}")

        # Validate state transition
        if item.status != ApprovalStatus.PENDING.value:
            raise ValueError(
                f"Cannot approve item in status '{item.status}'. "
                f"Only PENDING items can be approved."
            )

        # Update item
        item.status = ApprovalStatus.APPROVED.value
        item.approved_at = datetime.utcnow()
        item.approved_by = operator_id
        item.scheduled_publish_time = (
            scheduled_publish_time or item.suggested_publish_time
        )

        await self._session.flush()

        logger.info(
            "Approved item %s by %s, scheduled for %s",
            item_id,
            operator_id,
            item.scheduled_publish_time,
        )

        return item

    async def reject_item(
        self,
        item_id: str,
        reason: str,
        reason_text: Optional[str] = None,
        operator_id: str = "operator",
    ) -> object:
        """Reject an item with reason for ML feedback.

        Args:
            item_id: Unique identifier of the approval item
            reason: Rejection reason from RejectReasonType
            reason_text: Additional rejection details
            operator_id: Who rejected the item

        Returns:
            Updated ApprovalItem

        Raises:
            ValueError: If item not found or not in valid state
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            raise ValueError("ApprovalItem model not available")

        item = await self.get_by_id(item_id)
        if not item:
            raise ValueError(f"Approval item not found: {item_id}")

        # Validate state transition
        if item.status not in [ApprovalStatus.PENDING.value]:
            raise ValueError(
                f"Cannot reject item in status '{item.status}'. "
                f"Only PENDING items can be rejected."
            )

        # Validate reason_text for OTHER
        if reason == "other" and not reason_text:
            raise ValueError("reason_text is required when reason is 'other'")

        # Update item
        item.status = ApprovalStatus.REJECTED.value
        item.rejection_reason = reason
        item.rejection_text = reason_text
        item.archived_at = datetime.utcnow()

        await self._session.flush()

        logger.info(
            "Rejected item %s by %s, reason: %s",
            item_id,
            operator_id,
            reason,
        )

        return item

    async def update_caption(
        self,
        item_id: str,
        new_caption: str,
        new_hashtags: Optional[list[str]] = None,
        operator_id: str = "operator",
    ) -> object:
        """Update caption and preserve edit history.

        Args:
            item_id: Unique identifier of the approval item
            new_caption: Updated caption text
            new_hashtags: Updated hashtags (optional)
            operator_id: Who made the edit

        Returns:
            Updated ApprovalItem

        Raises:
            ValueError: If item not found
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalItemEdit
        except ImportError:
            raise ValueError("ApprovalItem model not available")

        item = await self.get_by_id(item_id)
        if not item:
            raise ValueError(f"Approval item not found: {item_id}")

        # Store original caption if first edit
        if item.original_caption is None:
            item.original_caption = item.full_caption

        # Create edit history entry
        edit = ApprovalItemEdit(
            item_id=item.id,
            previous_caption=item.full_caption,
            new_caption=new_caption,
            editor=operator_id,
        )
        self._session.add(edit)

        # Update caption
        item.full_caption = new_caption
        if new_hashtags is not None:
            item.hashtags = new_hashtags

        await self._session.flush()

        logger.info("Updated caption for item %s by %s", item_id, operator_id)

        return item

    async def get_edit_history(self, item_id: str) -> list:
        """Get all edits for an item.

        Args:
            item_id: Unique identifier of the approval item

        Returns:
            List of ApprovalItemEdit records, newest first
        """
        try:
            from core.approval.models import ApprovalItemEdit
        except ImportError:
            logger.warning("ApprovalItemEdit model not available")
            return []

        query = (
            select(ApprovalItemEdit)
            .where(ApprovalItemEdit.item_id == UUID(item_id))
            .order_by(ApprovalItemEdit.edited_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def revert_to_version(
        self,
        item_id: str,
        version_id: str,
        operator_id: str = "operator",
    ) -> object:
        """Revert caption to a previous version.

        Args:
            item_id: Unique identifier of the approval item
            version_id: ID of the edit to revert to
            operator_id: Who reverted

        Returns:
            Updated ApprovalItem

        Raises:
            ValueError: If item or version not found
        """
        try:
            from core.approval.models import ApprovalItemEdit
        except ImportError:
            raise ValueError("ApprovalItemEdit model not available")

        # Get the edit to revert to
        query = select(ApprovalItemEdit).where(
            ApprovalItemEdit.id == UUID(version_id)
        )
        result = await self._session.execute(query)
        edit = result.scalar_one_or_none()

        if not edit:
            raise ValueError(f"Edit version not found: {version_id}")

        if str(edit.item_id) != item_id:
            raise ValueError("Edit does not belong to this item")

        # Revert to previous caption (before this edit)
        return await self.update_caption(
            item_id=item_id,
            new_caption=edit.previous_caption,
            operator_id=f"{operator_id} (revert)",
        )

    async def revert_to_original(
        self,
        item_id: str,
        operator_id: str = "operator",
    ) -> object:
        """Revert caption to the original version.

        Args:
            item_id: Unique identifier of the approval item
            operator_id: Who reverted

        Returns:
            Updated ApprovalItem

        Raises:
            ValueError: If item not found or no original exists
        """
        item = await self.get_by_id(item_id)
        if not item:
            raise ValueError(f"Approval item not found: {item_id}")

        if item.original_caption is None:
            raise ValueError("No original caption stored - item has not been edited")

        return await self.update_caption(
            item_id=item_id,
            new_caption=item.original_caption,
            operator_id=f"{operator_id} (revert to original)",
        )

    # Story 4-3: Batch operations
    async def batch_approve_items(
        self,
        item_ids: list[str],
        operator_id: str = "operator",
    ) -> BatchApproveResponse:
        """Batch approve items and move to scheduled queue.

        Story 4-3, Task 3.4: Batch approve operation.

        Args:
            item_ids: List of item IDs to approve
            operator_id: Who approved the items

        Returns:
            BatchApproveResponse with summary and per-item results
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            raise ValueError("ApprovalItem model not available")

        batch_id = str(uuid4())
        results: list[BatchActionResultItem] = []
        successful = 0
        failed = 0
        earliest_time: Optional[datetime] = None
        latest_time: Optional[datetime] = None

        for item_id in item_ids:
            try:
                item = await self.get_by_id(item_id)
                if not item:
                    results.append(BatchActionResultItem(
                        item_id=item_id,
                        success=False,
                        error=f"Item not found: {item_id}",
                    ))
                    failed += 1
                    continue

                if item.status != ApprovalStatus.PENDING.value:
                    results.append(BatchActionResultItem(
                        item_id=item_id,
                        success=False,
                        error=f"Item not in PENDING status: {item.status}",
                    ))
                    failed += 1
                    continue

                # Update item
                item.status = ApprovalStatus.APPROVED.value
                item.approved_at = datetime.utcnow()
                item.approved_by = operator_id
                item.scheduled_publish_time = item.suggested_publish_time
                item.batch_id = batch_id

                # Track date range for summary
                publish_time = item.suggested_publish_time
                if publish_time:
                    if earliest_time is None or publish_time < earliest_time:
                        earliest_time = publish_time
                    if latest_time is None or publish_time > latest_time:
                        latest_time = publish_time

                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=True,
                    scheduled_publish_time=publish_time,
                ))
                successful += 1

            except Exception as e:
                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        await self._session.flush()

        # Generate summary
        if earliest_time and latest_time:
            if earliest_time.date() == latest_time.date():
                summary = f"{successful} items approved, scheduled for {earliest_time.strftime('%b %d')}"
            else:
                summary = f"{successful} items approved, scheduled for {earliest_time.strftime('%b %d')}-{latest_time.strftime('%b %d')}"
        else:
            summary = f"{successful} items approved"

        logger.info(
            "Batch approve completed: %d successful, %d failed (batch_id=%s)",
            successful,
            failed,
            batch_id,
        )

        return BatchApproveResponse(
            batch_id=batch_id,
            total_requested=len(item_ids),
            successful_count=successful,
            failed_count=failed,
            results=results,
            summary=summary,
        )

    async def batch_reject_items(
        self,
        item_ids: list[str],
        reason: str,
        reason_text: Optional[str] = None,
        operator_id: str = "operator",
    ) -> BatchRejectResponse:
        """Batch reject items with a single reason.

        Story 4-3, Task 4.4: Batch reject operation.

        Args:
            item_ids: List of item IDs to reject
            reason: Rejection reason (same for all items)
            reason_text: Optional additional details
            operator_id: Who rejected the items

        Returns:
            BatchRejectResponse with summary and per-item results
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            raise ValueError("ApprovalItem model not available")

        # Validate reason_text for OTHER
        if reason == "other" and not reason_text:
            raise ValueError("reason_text is required when reason is 'other'")

        batch_id = str(uuid4())
        results: list[BatchActionResultItem] = []
        successful = 0
        failed = 0

        for item_id in item_ids:
            try:
                item = await self.get_by_id(item_id)
                if not item:
                    results.append(BatchActionResultItem(
                        item_id=item_id,
                        success=False,
                        error=f"Item not found: {item_id}",
                    ))
                    failed += 1
                    continue

                if item.status != ApprovalStatus.PENDING.value:
                    results.append(BatchActionResultItem(
                        item_id=item_id,
                        success=False,
                        error=f"Item not in PENDING status: {item.status}",
                    ))
                    failed += 1
                    continue

                # Update item
                item.status = ApprovalStatus.REJECTED.value
                item.rejection_reason = reason
                item.rejection_text = reason_text
                item.archived_at = datetime.utcnow()
                item.batch_id = batch_id

                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=True,
                ))
                successful += 1

            except Exception as e:
                results.append(BatchActionResultItem(
                    item_id=item_id,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        await self._session.flush()

        # Generate summary
        reason_display = reason.replace("_", " ").title()
        summary = f"{successful} items rejected: {reason_display}"

        logger.info(
            "Batch reject completed: %d successful, %d failed (batch_id=%s, reason=%s)",
            successful,
            failed,
            batch_id,
            reason,
        )

        return BatchRejectResponse(
            batch_id=batch_id,
            total_requested=len(item_ids),
            successful_count=successful,
            failed_count=failed,
            results=results,
            summary=summary,
        )

    def _encode_cursor(
        self,
        priority: int,
        time,
        item_id: str,
    ) -> str:
        """Encode pagination cursor as base64 JSON.

        Args:
            priority: Source priority value
            time: Suggested publish time
            item_id: Item UUID as string

        Returns:
            Base64-encoded cursor string
        """
        cursor_data = {
            "priority": priority,
            "time": time.isoformat() if time else None,
            "id": item_id,
        }
        json_str = json.dumps(cursor_data)
        return base64.b64encode(json_str.encode()).decode()

    def _decode_cursor(self, cursor: str) -> Optional[dict]:
        """Decode pagination cursor from base64 JSON.

        Args:
            cursor: Base64-encoded cursor string

        Returns:
            Dictionary with cursor data, or None if invalid
        """
        try:
            json_str = base64.b64decode(cursor.encode()).decode()
            data = json.loads(json_str)

            # Parse datetime if present
            if data.get("time"):
                data["time"] = datetime.fromisoformat(data["time"])

            return data
        except Exception:
            logger.warning("Failed to decode pagination cursor")
            return None

    # Story 4-4: Scheduling operations

    async def get_scheduled_items(
        self,
        start_date: datetime,
        end_date: datetime,
        statuses: Optional[list[str]] = None,
    ) -> list:
        """Get items scheduled within date range.

        Story 4-4, Task 2.1: Calendar endpoint data source.

        Args:
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)
            statuses: Filter by status (optional)

        Returns:
            List of ApprovalItem with scheduled_publish_time in range
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            logger.warning("ApprovalItem model not available")
            return []

        # Default statuses for calendar view
        if statuses is None:
            statuses = [
                ApprovalStatus.APPROVED.value,
                ApprovalStatus.SCHEDULED.value,
            ]

        query = (
            select(ApprovalItem)
            .where(
                ApprovalItem.status.in_(statuses),
                ApprovalItem.scheduled_publish_time >= start_date,
                ApprovalItem.scheduled_publish_time <= end_date,
            )
            .order_by(ApprovalItem.scheduled_publish_time.asc())
        )

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def reschedule_item(
        self,
        item_id: str,
        new_publish_time: datetime,
        force: bool = False,
        operator_id: str = "operator",
    ) -> object:
        """Reschedule an approved/scheduled item.

        Story 4-4, Task 4.3: Reschedule endpoint.

        Args:
            item_id: Item to reschedule
            new_publish_time: New scheduled time
            force: Override imminent lock (< 30 min)
            operator_id: Who rescheduled

        Returns:
            Updated ApprovalItem

        Raises:
            ValueError: If item not found, invalid state, or locked
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            raise ValueError("ApprovalItem model not available")

        item = await self.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item not found: {item_id}")

        # Validate status
        valid_statuses = [
            ApprovalStatus.APPROVED.value,
            ApprovalStatus.SCHEDULED.value,
        ]
        if item.status not in valid_statuses:
            raise ValueError(
                f"Cannot reschedule item in status '{item.status}'. "
                f"Only APPROVED or SCHEDULED items can be rescheduled."
            )

        # Check imminent lock (30 min protection)
        if item.scheduled_publish_time:
            time_to_publish = item.scheduled_publish_time - datetime.utcnow()
            if time_to_publish.total_seconds() < 1800 and not force:
                raise ValueError(
                    "Cannot reschedule within 30 minutes of publish time. "
                    "Use force=true to override."
                )

        # Store old job ID for update
        old_arq_job_id = getattr(item, "arq_job_id", None)

        # Update time
        item.scheduled_publish_time = new_publish_time
        item.updated_at = datetime.utcnow()

        # Story 4-4, Task 8.4: Update ARQ job when publish time is rescheduled
        try:
            from core.scheduling.jobs import update_publish_job
            from core.database import get_redis_pool

            redis_pool = await get_redis_pool()
            if redis_pool:
                new_job_id = await update_publish_job(
                    redis_pool=redis_pool,
                    item_id=item_id,
                    old_job_id=old_arq_job_id,
                    new_publish_time=new_publish_time,
                )
                if new_job_id:
                    item.arq_job_id = new_job_id
                    logger.info(
                        "Updated ARQ job for item %s: %s -> %s",
                        item_id,
                        old_arq_job_id,
                        new_job_id,
                    )
        except ImportError:
            logger.debug("ARQ jobs module not available, skipping job update")
        except Exception as e:
            logger.warning("Failed to update ARQ job for item %s: %s", item_id, e)

        await self._session.flush()

        logger.info(
            "Rescheduled item %s to %s by %s",
            item_id,
            new_publish_time,
            operator_id,
        )

        return item

    async def get_items_at_hour(
        self,
        target_hour: datetime,
    ) -> list:
        """Get items scheduled for a specific hour.

        Story 4-4, Task 7.1: Conflict detection helper.

        Args:
            target_hour: The hour to check (minute/second ignored)

        Returns:
            List of items scheduled in that hour
        """
        try:
            from core.approval.models import ApprovalItem, ApprovalStatus
        except ImportError:
            return []

        # Calculate hour boundaries
        hour_start = target_hour.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start.replace(minute=59, second=59, microsecond=999999)

        query = (
            select(ApprovalItem)
            .where(
                ApprovalItem.status.in_([
                    ApprovalStatus.APPROVED.value,
                    ApprovalStatus.SCHEDULED.value,
                ]),
                ApprovalItem.scheduled_publish_time >= hour_start,
                ApprovalItem.scheduled_publish_time <= hour_end,
            )
            .order_by(ApprovalItem.scheduled_publish_time.asc())
        )

        result = await self._session.execute(query)
        return list(result.scalars().all())


__all__ = [
    "ApprovalItemRepository",
]
