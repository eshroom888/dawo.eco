"""Approval management module for DAWO.ECO.

Provides database models and utilities for content approval workflow.

Models:
    - ApprovalItem: Content item pending approval
    - ApprovalItemEdit: Audit trail for caption edits
    - ApprovalStatus: Approval workflow status
    - SourcePriority: Source-based priority ordering
    - RejectReasonType: Predefined rejection reasons

Exports:
    - ApprovalItem: SQLAlchemy model for approval items
    - ApprovalItemEdit: SQLAlchemy model for edit history
    - ApprovalStatus: Enum for approval workflow states
    - SourcePriority: Enum for source priority ordering
    - RejectReasonType: Enum for rejection reasons
"""

from .models import (
    ApprovalItem,
    ApprovalItemEdit,
    ApprovalStatus,
    SourcePriority,
    ComplianceStatus,
    RejectReasonType,
)

__all__ = [
    "ApprovalItem",
    "ApprovalItemEdit",
    "ApprovalStatus",
    "SourcePriority",
    "ComplianceStatus",
    "RejectReasonType",
]
