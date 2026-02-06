"""Research Scoring Service for Research Pool integration.

Provides a high-level service interface for scoring research items
and updating their scores in the database.

This service is registered in team_spec.py and injectable via Team Builder.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from ..repository import ResearchPoolRepository
from .scorer import ResearchItemScorer
from .schemas import ScoringResult
from ..exceptions import ItemNotFoundError

logger = logging.getLogger(__name__)


class ResearchScoringService:
    """Service for scoring research items and updating the Research Pool.

    Integrates ResearchItemScorer with ResearchPoolRepository to provide
    a single-call interface for scoring and persisting scores.

    Attributes:
        _repository: ResearchPoolRepository for database operations.
        _scorer: ResearchItemScorer for calculating scores.
    """

    def __init__(
        self,
        repository: ResearchPoolRepository,
        scorer: ResearchItemScorer,
    ) -> None:
        """Initialize with injected dependencies.

        Args:
            repository: ResearchPoolRepository for database access.
            scorer: ResearchItemScorer for score calculation.
        """
        self._repository = repository
        self._scorer = scorer

    async def score_and_update(self, item_id: UUID) -> ScoringResult:
        """Score a research item and update its score in the database.

        Loads the item from the database, calculates its score using
        the ResearchItemScorer, updates the score in the database,
        and returns the scoring result.

        Args:
            item_id: UUID of the item to score.

        Returns:
            ScoringResult with score breakdown and reasoning.

        Raises:
            ItemNotFoundError: If item does not exist.
        """
        # Load item from repository
        item = await self._repository.get_by_id(item_id)
        if item is None:
            logger.error(f"Item not found for scoring: {item_id}")
            raise ItemNotFoundError(item_id)

        # Convert ORM model to dictionary for scorer
        item_dict = self._model_to_dict(item)

        # Calculate score
        result = self._scorer.calculate_score(item_dict)

        # Update score in database
        await self._repository.update_score(item_id, result.final_score)

        logger.info(f"Scored and updated item {item_id}: {result.final_score}")

        return result

    async def score_item(self, item: Any) -> ScoringResult:
        """Score a research item without updating the database.

        Useful for preview scoring or batch scoring before committing.

        Args:
            item: Research item (ORM model or dictionary).

        Returns:
            ScoringResult with score breakdown and reasoning.
        """
        # Handle both ORM models and dictionaries
        if hasattr(item, "__dict__"):
            item_dict = self._model_to_dict(item)
        else:
            item_dict = item

        return self._scorer.calculate_score(item_dict)

    def _model_to_dict(self, item: Any) -> dict:
        """Convert ORM model to dictionary for scoring.

        Args:
            item: ResearchItem ORM model.

        Returns:
            Dictionary with item data.
        """
        return {
            "id": item.id,
            "source": item.source,
            "title": item.title,
            "content": item.content,
            "url": item.url,
            "tags": item.tags,
            "source_metadata": item.source_metadata,
            "created_at": item.created_at,
            "score": item.score,
            "compliance_status": item.compliance_status,
        }
