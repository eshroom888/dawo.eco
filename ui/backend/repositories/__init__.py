"""Database repositories for UI Backend.

Provides database access layer for all UI backend operations.

Exports:
    - ApprovalItemRepository: Approval queue database operations
"""

from .approval_repository import ApprovalItemRepository

__all__ = [
    "ApprovalItemRepository",
]
