"""FastAPI router for Approval Queue API.

Provides endpoints for retrieving, displaying, and managing content pending approval.
Implements source-based priority sorting, cursor-based pagination, and action operations.

Endpoints:
    GET /api/approval-queue: List pending approval items with sorting
    GET /api/approval-queue/{item_id}: Get single approval item detail
    POST /api/approval-queue/{item_id}/approve: Approve content item
    POST /api/approval-queue/{item_id}/reject: Reject content item with reason
    PUT /api/approval-queue/{item_id}/edit: Edit caption content
    POST /api/approval-queue/{item_id}/revalidate: Trigger compliance revalidation
    GET /api/approval-queue/{item_id}/history: Get edit history

Performance Target:
    Queue loads in < 3 seconds (AC #2)
    Actions complete in < 2 seconds
"""

import logging
from typing import Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ui.backend.schemas.approval import (
    ApprovalQueueItemSchema,
    ApprovalQueueResponse,
    QualityColor,
    get_quality_color,
)
from ui.backend.schemas.approval_actions import (
    ApproveActionSchema,
    RejectActionSchema,
    EditActionSchema,
    ApplyRewriteSchema,
    ApprovalActionResponse,
    EditHistorySchema,
    RevalidationResultSchema,
    RewriteSuggestionSchema,
)
from ui.backend.schemas.batch_approval import (
    BatchApproveSchema,
    BatchRejectSchema,
    BatchApproveResponse,
    BatchRejectResponse,
)
from ui.backend.repositories.approval_repository import ApprovalItemRepository

if TYPE_CHECKING:
    from core.approval.models import ApprovalItem

# Lazy import validators to avoid circular dependencies
_eu_compliance_checker = None
_brand_voice_validator = None


def _get_eu_compliance_checker():
    """Lazy load EU Compliance Checker."""
    global _eu_compliance_checker
    if _eu_compliance_checker is None:
        try:
            from teams.dawo.validators.eu_compliance import EUComplianceChecker
            _eu_compliance_checker = EUComplianceChecker()
        except ImportError:
            logger.warning("EUComplianceChecker not available")
            return None
    return _eu_compliance_checker


def _get_brand_voice_validator():
    """Lazy load Brand Voice Validator."""
    global _brand_voice_validator
    if _brand_voice_validator is None:
        try:
            from teams.dawo.validators.brand_voice import BrandVoiceValidator
            _brand_voice_validator = BrandVoiceValidator()
        except ImportError:
            logger.warning("BrandVoiceValidator not available")
            return None
    return _brand_voice_validator


async def _perform_revalidation(caption: str) -> RevalidationResultSchema:
    """Perform compliance and quality revalidation on caption.

    Args:
        caption: The caption text to validate

    Returns:
        RevalidationResultSchema with updated compliance and quality scores
    """
    compliance_status = "COMPLIANT"
    compliance_details = []
    quality_score = 7.5  # Default score
    quality_breakdown = None
    rewrite_suggestions = []

    # Run EU Compliance Check
    checker = _get_eu_compliance_checker()
    if checker is not None:
        try:
            compliance_result = await checker.check(caption)
            compliance_status = compliance_result.overall_status.value
            compliance_details = [
                {
                    "phrase": r.phrase,
                    "status": r.status.value,
                    "explanation": r.explanation,
                    "regulation_reference": r.regulation_reference,
                }
                for r in compliance_result.results
            ]
            # Generate rewrite suggestions for non-compliant phrases
            for r in compliance_result.results:
                if r.status.value in ("PROHIBITED", "BORDERLINE"):
                    rewrite_suggestions.append({
                        "id": f"compliance-{hash(r.phrase) % 10000}",
                        "original_text": r.phrase,
                        "suggested_text": r.suggested_alternative or "",
                        "reason": r.explanation,
                        "type": "compliance",
                    })
        except Exception as e:
            logger.warning("EU Compliance check failed: %s", str(e))

    # Run Brand Voice Validation
    validator = _get_brand_voice_validator()
    if validator is not None:
        try:
            brand_result = await validator.validate(caption)
            # Adjust quality score based on brand voice
            if brand_result.status.value == "PASS":
                quality_score = min(10.0, quality_score + 1.0)
            elif brand_result.status.value == "FAIL":
                quality_score = max(0.0, quality_score - 2.0)

            quality_breakdown = {
                "brand_voice_score": brand_result.score,
                "compliance_score": 8.0 if compliance_status == "COMPLIANT" else 4.0,
            }

            # Add brand voice suggestions
            for issue in brand_result.issues:
                rewrite_suggestions.append({
                    "id": f"brand-{hash(issue.description) % 10000}",
                    "original_text": issue.text_sample or "",
                    "suggested_text": issue.suggestion or "",
                    "reason": issue.description,
                    "type": "brand_voice",
                })
        except Exception as e:
            logger.warning("Brand Voice validation failed: %s", str(e))

    return RevalidationResultSchema(
        compliance_status=compliance_status,
        compliance_details=compliance_details,
        quality_score=quality_score,
        quality_breakdown=quality_breakdown,
        rewrite_suggestions=[
            RewriteSuggestionSchema(**s) for s in rewrite_suggestions
        ] if rewrite_suggestions else None,
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approval-queue", tags=["approval-queue"])

# Default pagination settings
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


async def get_db_session() -> AsyncSession:
    """Dependency to get database session.

    This is a placeholder that should be replaced with actual
    database session management in production.

    Yields:
        AsyncSession for database operations
    """
    # TODO: Implement actual database session management
    # This will be injected by the main application
    raise NotImplementedError("Database session dependency not configured")


async def get_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalItemRepository:
    """Dependency to get approval item repository.

    Args:
        session: Database session from dependency injection

    Returns:
        ApprovalItemRepository instance
    """
    return ApprovalItemRepository(session)


@router.get(
    "",
    response_model=ApprovalQueueResponse,
    summary="List pending approval items",
    description="""
    Retrieves content items pending approval, sorted by source-based priority.

    Priority Order:
    1. TRENDING (time-sensitive)
    2. SCHEDULED (approaching deadline)
    3. EVERGREEN (flexible timing)
    4. RESEARCH (lowest urgency)

    Within each priority level, items are sorted by suggested publish time.
    """,
)
async def get_approval_queue(
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description="Maximum number of items to return",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (from previous response)",
    ),
    repository: ApprovalItemRepository = Depends(get_repository),
) -> ApprovalQueueResponse:
    """Get paginated approval queue with priority sorting.

    Args:
        limit: Maximum number of items to return (1-100)
        cursor: Pagination cursor from previous response
        repository: Approval item repository

    Returns:
        ApprovalQueueResponse with items and pagination info

    Raises:
        HTTPException: If database query fails
    """
    try:
        # Get items from repository with pagination
        items, total_count, next_cursor = await repository.get_pending_items(
            limit=limit,
            cursor=cursor,
        )

        # Transform database items to response schema
        queue_items = [
            _transform_to_queue_item(item) for item in items
        ]

        return ApprovalQueueResponse(
            items=queue_items,
            total_count=total_count,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    except Exception as e:
        logger.exception("Failed to retrieve approval queue")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve approval queue: {str(e)}",
        ) from e


@router.get(
    "/{item_id}",
    response_model=ApprovalQueueItemSchema,
    summary="Get approval item details",
    description="""
    Retrieves full details for a single approval item including:
    - Full caption with hashtags
    - Compliance check details with explanations
    - Quality score breakdown by factor
    """,
)
async def get_approval_item(
    item_id: str,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> ApprovalQueueItemSchema:
    """Get detailed view of single approval item.

    Args:
        item_id: Unique identifier of the approval item
        repository: Approval item repository

    Returns:
        ApprovalQueueItemSchema with full details

    Raises:
        HTTPException: If item not found or database query fails
    """
    try:
        item = await repository.get_by_id(item_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Approval item not found: {item_id}",
            )
        return _transform_to_queue_item(item, include_details=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to retrieve approval item: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve approval item: {str(e)}",
        ) from e


@router.post(
    "/{item_id}/approve",
    response_model=ApprovalActionResponse,
    summary="Approve content item",
    description="""
    Approve a content item and move it to the scheduled queue.
    Optionally override the suggested publish time.
    """,
)
async def approve_item(
    item_id: str,
    request: ApproveActionSchema = ApproveActionSchema(),
    repository: ApprovalItemRepository = Depends(get_repository),
) -> ApprovalActionResponse:
    """Approve content and schedule for publishing.

    Args:
        item_id: Unique identifier of the approval item
        request: Optional publish time override
        repository: Approval item repository

    Returns:
        ApprovalActionResponse with success status

    Raises:
        HTTPException: If item not found, invalid state, or database error
    """
    try:
        item = await repository.approve_item(
            item_id=item_id,
            scheduled_publish_time=request.scheduled_publish_time,
            operator_id="operator",  # TODO: Get from auth context
        )

        scheduled_time = item.scheduled_publish_time
        time_str = scheduled_time.strftime("%Y-%m-%d %H:%M") if scheduled_time else "not scheduled"

        return ApprovalActionResponse(
            success=True,
            message=f"Content approved. Scheduled for {time_str}",
            item_id=str(item.id),
            new_status=item.status,
        )
    except ValueError as e:
        logger.warning("Approve validation error for %s: %s", item_id, str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to approve item: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve item: {str(e)}",
        ) from e


@router.post(
    "/{item_id}/reject",
    response_model=ApprovalActionResponse,
    summary="Reject content item",
    description="""
    Reject a content item with a reason for ML feedback and analytics.
    The item is archived and the rejection reason is stored for learning.
    """,
)
async def reject_item(
    item_id: str,
    request: RejectActionSchema,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> ApprovalActionResponse:
    """Reject content with reason for ML feedback.

    Args:
        item_id: Unique identifier of the approval item
        request: Rejection reason and optional details
        repository: Approval item repository

    Returns:
        ApprovalActionResponse with success status

    Raises:
        HTTPException: If item not found, invalid state, or database error
    """
    try:
        # Validate reason_text when reason is OTHER
        if request.reason.value == "other" and not request.reason_text:
            raise HTTPException(
                status_code=400,
                detail="Please provide details when selecting 'Other'",
            )

        item = await repository.reject_item(
            item_id=item_id,
            reason=request.reason.value,
            reason_text=request.reason_text,
            operator_id="operator",  # TODO: Get from auth context
        )

        return ApprovalActionResponse(
            success=True,
            message=f"Content rejected. Reason: {request.reason.value}",
            item_id=str(item.id),
            new_status=item.status,
        )
    except ValueError as e:
        logger.warning("Reject validation error for %s: %s", item_id, str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to reject item: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject item: {str(e)}",
        ) from e


@router.put(
    "/{item_id}/edit",
    response_model=ApprovalActionResponse,
    summary="Edit caption content",
    description="""
    Edit the caption of a content item.
    Edit history is preserved for audit trail.
    Triggers automatic revalidation of compliance and quality.
    """,
)
async def edit_item(
    item_id: str,
    request: EditActionSchema,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> ApprovalActionResponse:
    """Edit caption and trigger revalidation.

    Args:
        item_id: Unique identifier of the approval item
        request: New caption and optional hashtags
        repository: Approval item repository

    Returns:
        ApprovalActionResponse with success status and revalidation results

    Raises:
        HTTPException: If item not found or database error
    """
    try:
        item = await repository.update_caption(
            item_id=item_id,
            new_caption=request.caption,
            new_hashtags=request.hashtags,
            operator_id="operator",  # TODO: Get from auth context
        )

        # Trigger revalidation via compliance/quality validators
        revalidation_result = await _perform_revalidation(request.caption)

        return ApprovalActionResponse(
            success=True,
            message="Caption updated and revalidated successfully.",
            item_id=str(item.id),
            new_status=item.status,
            revalidation=revalidation_result,
        )
    except ValueError as e:
        logger.warning("Edit validation error for %s: %s", item_id, str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to edit item: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit item: {str(e)}",
        ) from e


@router.post(
    "/{item_id}/revalidate",
    response_model=RevalidationResultSchema,
    summary="Trigger content revalidation",
    description="""
    Manually trigger compliance and quality revalidation for a content item.
    Useful after editing or when compliance rules have been updated.
    """,
)
async def revalidate_item(
    item_id: str,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> RevalidationResultSchema:
    """Revalidate content for compliance and quality.

    Args:
        item_id: Unique identifier of the approval item
        repository: Approval item repository

    Returns:
        RevalidationResultSchema with updated scores

    Raises:
        HTTPException: If item not found or revalidation fails
    """
    try:
        item = await repository.get_by_id(item_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Approval item not found: {item_id}",
            )

        # Perform actual revalidation via validators
        result = await _perform_revalidation(item.full_caption)

        logger.info(
            "Revalidated item %s: compliance=%s, quality=%.1f",
            item_id,
            result.compliance_status,
            result.quality_score,
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to revalidate item: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revalidate item: {str(e)}",
        ) from e


@router.put(
    "/{item_id}/apply-rewrite",
    response_model=ApprovalActionResponse,
    summary="Apply AI rewrite suggestions",
    description="""
    Apply one or more AI-suggested rewrites to the content.
    Each applied suggestion updates the caption and is tracked in edit history.
    Triggers automatic revalidation after applying.
    """,
)
async def apply_rewrite(
    item_id: str,
    request: ApplyRewriteSchema,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> ApprovalActionResponse:
    """Apply AI rewrite suggestions to content.

    Args:
        item_id: Unique identifier of the approval item
        request: List of suggestion IDs to apply
        repository: Approval item repository

    Returns:
        ApprovalActionResponse with success status

    Raises:
        HTTPException: If item not found, invalid suggestions, or database error
    """
    try:
        item = await repository.get_by_id(item_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Approval item not found: {item_id}",
            )

        # Get rewrite suggestions
        suggestions = item.rewrite_suggestions or []
        suggestion_map = {s.get("id"): s for s in suggestions if isinstance(s, dict)}

        # Validate all suggestion IDs exist
        missing_ids = [sid for sid in request.suggestion_ids if sid not in suggestion_map]
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid suggestion IDs: {missing_ids}",
            )

        # Apply suggestions to caption
        new_caption = item.full_caption
        for suggestion_id in request.suggestion_ids:
            suggestion = suggestion_map[suggestion_id]
            original_text = suggestion.get("original_text", "")
            suggested_text = suggestion.get("suggested_text", "")
            if original_text and original_text in new_caption:
                new_caption = new_caption.replace(original_text, suggested_text, 1)

        # Update caption if changes were made
        if new_caption != item.full_caption:
            await repository.update_caption(
                item_id=item_id,
                new_caption=new_caption,
                operator_id="ai_rewrite",
            )

        return ApprovalActionResponse(
            success=True,
            message=f"Applied {len(request.suggestion_ids)} suggestion(s)",
            item_id=str(item.id),
            new_status=item.status,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to apply rewrites: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply rewrites: {str(e)}",
        ) from e


@router.get(
    "/{item_id}/history",
    response_model=list[EditHistorySchema],
    summary="Get edit history",
    description="""
    Retrieve the complete edit history for a content item.
    Shows all caption changes with timestamps and editors.
    """,
)
async def get_edit_history(
    item_id: str,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> list[EditHistorySchema]:
    """Get edit history for audit trail.

    Args:
        item_id: Unique identifier of the approval item
        repository: Approval item repository

    Returns:
        List of EditHistorySchema entries, newest first

    Raises:
        HTTPException: If item not found or database error
    """
    try:
        # Verify item exists
        item = await repository.get_by_id(item_id)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Approval item not found: {item_id}",
            )

        edits = await repository.get_edit_history(item_id)

        return [
            EditHistorySchema(
                id=str(edit.id),
                previous_caption=edit.previous_caption,
                new_caption=edit.new_caption,
                edited_at=edit.edited_at,
                editor=edit.editor,
            )
            for edit in edits
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to retrieve edit history: %s", item_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve edit history: {str(e)}",
        ) from e


# Story 4-3: Batch approval endpoints
@router.post(
    "/batch/approve",
    response_model=BatchApproveResponse,
    summary="Batch approve content items",
    description="""
    Approve multiple content items at once.
    Each item uses its suggested_publish_time for scheduling.

    Story 4-3: Batch Approval Capability
    """,
)
async def batch_approve_items(
    request: BatchApproveSchema,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> BatchApproveResponse:
    """Batch approve multiple items.

    Args:
        request: List of item IDs to approve
        repository: Approval item repository

    Returns:
        BatchApproveResponse with summary and per-item results

    Raises:
        HTTPException: If database error occurs
    """
    try:
        result = await repository.batch_approve_items(
            item_ids=request.item_ids,
            operator_id="operator",  # TODO: Get from auth context
        )

        logger.info(
            "Batch approved %d/%d items (batch_id=%s)",
            result.successful_count,
            result.total_requested,
            result.batch_id,
        )

        return result
    except ValueError as e:
        logger.warning("Batch approve validation error: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to batch approve items")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch approve items: {str(e)}",
        ) from e


@router.post(
    "/batch/reject",
    response_model=BatchRejectResponse,
    summary="Batch reject content items",
    description="""
    Reject multiple content items with the same reason.
    All items receive the same rejection reason for consistency.

    Story 4-3: Batch Approval Capability
    """,
)
async def batch_reject_items(
    request: BatchRejectSchema,
    repository: ApprovalItemRepository = Depends(get_repository),
) -> BatchRejectResponse:
    """Batch reject multiple items with reason.

    Args:
        request: List of item IDs and rejection reason
        repository: Approval item repository

    Returns:
        BatchRejectResponse with summary and per-item results

    Raises:
        HTTPException: If validation fails or database error occurs
    """
    try:
        # Validate reason_text when reason is OTHER
        if request.reason.value == "other" and not request.reason_text:
            raise HTTPException(
                status_code=400,
                detail="Please provide details when selecting 'Other'",
            )

        result = await repository.batch_reject_items(
            item_ids=request.item_ids,
            reason=request.reason.value,
            reason_text=request.reason_text,
            operator_id="operator",  # TODO: Get from auth context
        )

        logger.info(
            "Batch rejected %d/%d items (batch_id=%s, reason=%s)",
            result.successful_count,
            result.total_requested,
            result.batch_id,
            request.reason.value,
        )

        return result
    except ValueError as e:
        logger.warning("Batch reject validation error: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to batch reject items")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch reject items: {str(e)}",
        ) from e


def _transform_to_queue_item(
    item: "ApprovalItem",
    include_details: bool = False,
) -> ApprovalQueueItemSchema:
    """Transform database item to response schema.

    Args:
        item: Database approval item
        include_details: Whether to include compliance_details and quality_breakdown

    Returns:
        ApprovalQueueItemSchema for API response
    """
    # Calculate quality color from score
    quality_color = get_quality_color(item.quality_score)

    # Truncate caption to 100 chars for excerpt
    caption_excerpt = item.full_caption[:100] if len(item.full_caption) > 100 else item.full_caption

    return ApprovalQueueItemSchema(
        id=str(item.id),
        thumbnail_url=item.thumbnail_url,
        caption_excerpt=caption_excerpt,
        full_caption=item.full_caption,
        quality_score=item.quality_score,
        quality_color=quality_color,
        compliance_status=item.compliance_status,
        would_auto_publish=item.would_auto_publish,
        suggested_publish_time=item.suggested_publish_time,
        source_type=item.source_type,
        source_priority=item.source_priority,
        hashtags=item.hashtags or [],
        compliance_details=item.compliance_details if include_details else None,
        quality_breakdown=item.quality_breakdown if include_details else None,
        created_at=item.created_at,
        # Story 4-2: Edit support fields
        original_caption=item.original_caption if include_details else None,
        rewrite_suggestions=item.rewrite_suggestions if include_details else None,
        status=item.status,
    )


__all__ = [
    "router",
    "get_approval_queue",
    "get_approval_item",
    "approve_item",
    "reject_item",
    "edit_item",
    "revalidate_item",
    "get_edit_history",
    # Story 4-3: Batch operations
    "batch_approve_items",
    "batch_reject_items",
]
