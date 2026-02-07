"""NewsResearchPipeline for orchestrating the full news research workflow.

Orchestrates the Harvester Framework pipeline stages:
    Scanner -> Harvester -> Categorizer -> PriorityScorer -> Transformer -> Validator -> Scorer -> Publisher

Handles partial failures and graceful degradation per AC #4.

Usage:
    pipeline = NewsResearchPipeline(
        scanner, harvester, transformer, validator, scorer, publisher
    )
    result = await pipeline.execute()
"""

import logging
from typing import Any, Optional, Protocol
from uuid import UUID

from .schemas import (
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
    ValidatedResearch,
)
from .agent import NewsScanner, NewsScanError
from .harvester import NewsHarvester
from .transformer import NewsTransformer
from .validator import NewsValidator

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when pipeline fails critically."""

    pass


class ResearchPublisherProtocol(Protocol):
    """Protocol for research publisher dependency injection."""

    async def publish(self, item: Any) -> Any:
        """Publish a single research item."""
        ...

    async def publish_batch(self, items: list[Any]) -> list[Any]:
        """Publish multiple research items."""
        ...


class ResearchItemScorerProtocol(Protocol):
    """Protocol for research item scorer dependency injection."""

    def calculate_score(self, item: Any) -> Any:
        """Calculate score for a research item."""
        ...


class NewsResearchPipeline:
    """Orchestrated pipeline for news research.

    Chains all stages and handles partial failures.
    Implements graceful degradation per AC #4.

    Attributes:
        _scanner: News scanner stage
        _harvester: News harvester stage
        _transformer: News transformer stage
        _validator: News validator stage
        _scorer: Research item scorer
        _publisher: Research publisher
    """

    def __init__(
        self,
        scanner: NewsScanner,
        harvester: NewsHarvester,
        transformer: NewsTransformer,
        validator: NewsValidator,
        scorer: ResearchItemScorerProtocol,
        publisher: ResearchPublisherProtocol,
    ) -> None:
        """Initialize pipeline.

        Args:
            scanner: News scanner
            harvester: News harvester
            transformer: News transformer
            validator: News validator
            scorer: Research item scorer
            publisher: Research publisher
        """
        self._scanner = scanner
        self._harvester = harvester
        self._transformer = transformer
        self._validator = validator
        self._scorer = scorer
        self._publisher = publisher

    async def execute(self) -> PipelineResult:
        """Execute the full pipeline.

        Returns:
            PipelineResult with status and statistics

        Raises:
            PipelineError: On critical failure
        """
        statistics = PipelineStatistics()
        published_ids: list[UUID] = []
        error_message: Optional[str] = None
        status = PipelineStatus.COMPLETE

        try:
            # Stage 1: Scan
            logger.info("Starting news scan...")
            try:
                scan_result = await self._scanner.scan()
                statistics.total_found = len(scan_result.articles)
                statistics.feeds_processed = scan_result.statistics.feeds_processed
                statistics.feeds_failed = scan_result.statistics.feeds_failed
            except NewsScanError as e:
                logger.error("Scan failed: %s", e)
                return PipelineResult(
                    status=PipelineStatus.INCOMPLETE,
                    statistics=statistics,
                    error=str(e),
                    retry_scheduled=True,
                )

            if not scan_result.articles:
                logger.info("No articles found, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=statistics,
                )

            # Stage 2: Harvest
            logger.info("Harvesting %d articles...", len(scan_result.articles))
            harvested = self._harvester.harvest(scan_result.articles)
            statistics.harvested = len(harvested)

            if not harvested:
                logger.info("No articles harvested, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=statistics,
                )

            # Stage 3-5: Transform (includes categorize + prioritize)
            logger.info("Transforming %d articles...", len(harvested))
            transformed = self._transformer.transform(harvested)
            statistics.transformed = len(transformed)
            statistics.categorized = len(transformed)

            # Count regulatory flagged
            statistics.regulatory_flagged = sum(
                1 for _, cat, _ in transformed if cat.is_regulatory
            )

            if not transformed:
                logger.info("No articles transformed, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=statistics,
                )

            # Stage 6: Validate
            logger.info("Validating %d articles...", len(transformed))
            validated = self._validator.validate(transformed)
            statistics.validated = len(validated)

            if not validated:
                logger.info("No articles validated, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=statistics,
                )

            # Stage 7: Score (adjust with Research Item Scorer)
            logger.info("Scoring %d articles...", len(validated))
            scored = self._apply_scoring(validated)
            statistics.scored = len(scored)

            # Stage 8: Publish
            logger.info("Publishing %d articles...", len(scored))
            published_ids = await self._publish_items(scored)
            statistics.published = len(published_ids)
            statistics.failed = statistics.validated - len(published_ids)

            # Determine final status
            if statistics.feeds_failed > 0:
                status = PipelineStatus.PARTIAL
                error_message = f"{statistics.feeds_failed} feeds failed"
            elif statistics.failed > 0:
                status = PipelineStatus.PARTIAL
                error_message = f"{statistics.failed} articles failed to publish"

            logger.info(
                "Pipeline complete: %d published, %d failed",
                statistics.published,
                statistics.failed,
            )

            return PipelineResult(
                status=status,
                statistics=statistics,
                error=error_message,
                published_ids=published_ids,
            )

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            return PipelineResult(
                status=PipelineStatus.FAILED,
                statistics=statistics,
                error=str(e),
            )

    def _apply_scoring(
        self,
        validated: list[ValidatedResearch],
    ) -> list[ValidatedResearch]:
        """Apply Research Item Scorer adjustments.

        Args:
            validated: Validated research items

        Returns:
            Items with adjusted scores
        """
        scored: list[ValidatedResearch] = []

        for item in validated:
            try:
                # Get scoring adjustment
                scoring_result = self._scorer.calculate_score(item)

                # Create new item with adjusted score if available
                if hasattr(scoring_result, "final_score"):
                    adjusted_score = scoring_result.final_score
                else:
                    adjusted_score = item.score

                scored.append(
                    ValidatedResearch(
                        source=item.source,
                        title=item.title,
                        content=item.content,
                        url=item.url,
                        tags=item.tags,
                        source_metadata=item.source_metadata,
                        created_at=item.created_at,
                        compliance_status=item.compliance_status,
                        score=adjusted_score,
                    )
                )
            except Exception as e:
                logger.warning("Scoring failed for %s: %s", item.url, e)
                scored.append(item)  # Keep original score

        return scored

    async def _publish_items(
        self,
        items: list[ValidatedResearch],
    ) -> list[UUID]:
        """Publish items to Research Pool.

        Args:
            items: Items to publish

        Returns:
            List of published item UUIDs
        """
        published_ids: list[UUID] = []

        try:
            # Try batch publish first
            results = await self._publisher.publish_batch(items)
            for result in results:
                if hasattr(result, "id"):
                    published_ids.append(result.id)
        except Exception as e:
            logger.warning("Batch publish failed, trying individual: %s", e)
            # Fall back to individual publishing
            for item in items:
                try:
                    result = await self._publisher.publish(item)
                    if hasattr(result, "id"):
                        published_ids.append(result.id)
                except Exception as e:
                    logger.warning("Failed to publish %s: %s", item.url, e)

        return published_ids
