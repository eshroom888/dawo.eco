"""Research Pool module for DAWO research intelligence pipeline.

This module provides the foundation for Epic 2's Harvester Framework:
    [Scanners] -> [Harvesters] -> [Transformers] -> [Validators] -> [Publisher] -> [Research Pool]

Components:
    - ResearchItem: SQLAlchemy model for research data storage
    - ResearchSource: Enum for valid research sources (reddit, youtube, etc.)
    - ComplianceStatus: Enum for EU compliance check status
    - ResearchPoolRepository: Async repository for CRUD operations
    - ResearchQueryFilters: Dataclass for query filtering
    - ResearchPublisher: Service for publishing research items

Usage:
    from teams.dawo.research import (
        ResearchItem,
        ResearchSource,
        ComplianceStatus,
        ResearchPoolRepository,
        ResearchQueryFilters,
        ResearchPublisher,
    )

    # Create repository with injected session
    repository = ResearchPoolRepository(session)

    # Query research items
    filters = ResearchQueryFilters(source=ResearchSource.REDDIT, min_score=7.0)
    items = await repository.query(filters)
"""

from .models import ResearchItem, ResearchSource, ComplianceStatus
from .schemas import ResearchItemCreate, ResearchItemUpdate
from .exceptions import ResearchPoolError, ItemNotFoundError, DatabaseError, ValidationError
from .repository import ResearchPoolRepository, ResearchQueryFilters
from .publisher import ResearchPublisher, TransformedResearch

__all__ = [
    # Models
    "ResearchItem",
    "ResearchSource",
    "ComplianceStatus",
    # Schemas
    "ResearchItemCreate",
    "ResearchItemUpdate",
    "TransformedResearch",
    # Exceptions
    "ResearchPoolError",
    "ItemNotFoundError",
    "DatabaseError",
    "ValidationError",
    # Repository
    "ResearchPoolRepository",
    "ResearchQueryFilters",
    # Publisher
    "ResearchPublisher",
]
