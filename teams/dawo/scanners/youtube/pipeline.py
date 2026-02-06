"""YouTube Research Pipeline - orchestrates full Harvester Framework pipeline.

Implements the complete pipeline orchestration:
    [Scanner] → [Harvester] → [Transformer] → [Validator] → [Scorer] → [Publisher] → [Research Pool]

UNIQUE to YouTube: Handles QuotaExhaustedError separately from other API errors.
When quota is exhausted, pipeline returns QUOTA_EXCEEDED status with retry_after
timestamp for next day reset.

The pipeline chains all stages together with:
    - Statistics tracking through each stage (including insights_generated)
    - Graceful degradation on API failures
    - Quota exhaustion handling (wait until next day)
    - Partial failure handling (continue on item failures)
    - Comprehensive logging

Usage:
    pipeline = YouTubeResearchPipeline(
        scanner, harvester, transformer, validator, scorer, publisher
    )
    result = await pipeline.execute()
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from teams.dawo.research import ResearchPublisher, TransformedResearch
from teams.dawo.research.scoring import ResearchItemScorer

from .agent import YouTubeScanner
from .harvester import YouTubeHarvester
from .transformer import YouTubeTransformer
from .validator import YouTubeValidator
from .schemas import (
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
    ValidatedResearch,
)
from .tools import YouTubeAPIError, QuotaExhaustedError


# Module logger
logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Exception raised for critical pipeline errors.

    Attributes:
        message: Error description
        statistics: Pipeline statistics at time of failure
    """

    def __init__(
        self,
        message: str,
        statistics: Optional[PipelineStatistics] = None,
    ):
        super().__init__(message)
        self.message = message
        self.statistics = statistics or PipelineStatistics()


class YouTubeResearchPipeline:
    """YouTube Research Pipeline - orchestrates complete Harvester Framework.

    Chains all pipeline stages together:
        scan → harvest → transform → validate → score → publish

    UNIQUE to YouTube:
        - Transformer stage uses KeyInsightExtractor for LLM summarization
        - QuotaExhausted handled separately with retry_after timestamp
        - Statistics include insights_generated count

    Features:
        - Full stage orchestration
        - Statistics tracking per stage
        - Graceful degradation on YouTube API failure
        - Quota exhaustion handling (QUOTA_EXCEEDED status)
        - Partial failure handling (items can fail individually)
        - Retry scheduling on incomplete runs

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _scanner: YouTubeScanner for video discovery
        _harvester: YouTubeHarvester for detail/transcript enrichment
        _transformer: YouTubeTransformer for schema conversion (uses InsightExtractor)
        _validator: YouTubeValidator for compliance checking
        _scorer: ResearchItemScorer for relevance scoring
        _publisher: ResearchPublisher for database persistence
    """

    def __init__(
        self,
        scanner: YouTubeScanner,
        harvester: YouTubeHarvester,
        transformer: YouTubeTransformer,
        validator: YouTubeValidator,
        scorer: ResearchItemScorer,
        publisher: ResearchPublisher,
    ):
        """Initialize pipeline with injected stage components.

        Args:
            scanner: Video discovery stage
            harvester: Detail/transcript enrichment stage
            transformer: Schema conversion stage (includes LLM insight extraction)
            validator: Compliance checking stage
            scorer: Relevance scoring stage
            publisher: Database persistence stage
        """
        self._scanner = scanner
        self._harvester = harvester
        self._transformer = transformer
        self._validator = validator
        self._scorer = scorer
        self._publisher = publisher

    async def execute(self) -> PipelineResult:
        """Execute the complete pipeline.

        Runs all stages in sequence, tracking statistics and handling
        errors gracefully. Returns INCOMPLETE status on API failures
        and QUOTA_EXCEEDED on quota exhaustion (with retry_after).

        Returns:
            PipelineResult with status, statistics, and published IDs

        Note:
            - COMPLETE: All stages ran successfully
            - INCOMPLETE: YouTube API failure, retry scheduled
            - PARTIAL: Some items failed but pipeline completed
            - FAILED: Critical error, no retry
            - QUOTA_EXCEEDED: Daily quota exhausted, retry tomorrow
        """
        logger.info("Starting YouTube Research Pipeline execution")

        stats = PipelineStatistics()
        published_ids: list[UUID] = []

        try:
            # Stage 1: Scan - Discover videos
            logger.info("Stage 1/6: Scanning YouTube")
            scan_result = await self._scanner.scan()
            stats.total_found = len(scan_result.videos)
            stats.quota_used = scan_result.statistics.quota_used
            logger.info(f"Scan complete: {stats.total_found} videos found")

            if not scan_result.videos:
                logger.info("No videos found, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=stats,
                )

            # Stage 2: Harvest - Enrich with details and transcripts
            logger.info("Stage 2/6: Harvesting video details and transcripts")
            harvested = await self._harvester.harvest(scan_result.videos)
            stats.harvested = len(harvested)
            stats.transcripts_extracted = sum(
                1 for v in harvested if v.transcript_available
            )
            logger.info(
                f"Harvest complete: {stats.harvested} videos enriched, "
                f"{stats.transcripts_extracted} transcripts extracted"
            )

            if not harvested:
                logger.info("No videos harvested, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=stats,
                )

            # Stage 3: Transform - Convert to Research Pool schema (with LLM insights)
            logger.info("Stage 3/6: Transforming to Research Pool schema (with insights)")
            transformed = await self._transformer.transform(harvested)
            stats.transformed = len(transformed)
            # Count items that have insights (non-empty content with "Key Insights")
            stats.insights_generated = sum(
                1 for t in transformed if "Key Insights:" in t.content
            )
            logger.info(
                f"Transform complete: {stats.transformed} items created, "
                f"{stats.insights_generated} with insights"
            )

            # Stage 4: Validate - Check EU compliance
            logger.info("Stage 4/6: Validating EU compliance")
            validated = await self._validator.validate(transformed)
            stats.validated = len(validated)
            logger.info(f"Validation complete: {stats.validated} items validated")

            # Stage 5: Score - Calculate relevance scores
            logger.info("Stage 5/6: Scoring research items")
            scored = await self._score_items(validated)
            stats.scored = len(scored)
            logger.info(f"Scoring complete: {stats.scored} items scored")

            # Stage 6: Publish - Save to Research Pool
            logger.info("Stage 6/6: Publishing to Research Pool")
            publish_count, published_ids = await self._publish_items(scored)
            stats.published = publish_count
            stats.failed = stats.scored - stats.published
            logger.info(f"Publish complete: {stats.published} items published")

            # Determine final status
            status = self._determine_status(stats)

            logger.info(
                f"Pipeline complete: status={status.value}, "
                f"published={stats.published}/{stats.total_found}"
            )

            return PipelineResult(
                status=status,
                statistics=stats,
                published_ids=published_ids,
            )

        except QuotaExhaustedError as e:
            # Special handling for quota exhaustion - retry tomorrow
            logger.warning(f"YouTube quota exhausted: {e}")
            stats.failed = stats.total_found - stats.published

            # Calculate next day reset (YouTube resets at midnight PT)
            # For simplicity, we use UTC midnight + 8 hours
            now = datetime.now(timezone.utc)
            tomorrow = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now.hour >= 8:
                tomorrow += timedelta(days=1)

            return PipelineResult(
                status=PipelineStatus.QUOTA_EXCEEDED,
                statistics=stats,
                error=str(e),
                retry_scheduled=True,
                retry_after=tomorrow,
            )

        except YouTubeAPIError as e:
            # Graceful degradation - mark as incomplete for retry
            logger.error(f"YouTube API failure: {e}")
            stats.failed = stats.total_found - stats.published

            return PipelineResult(
                status=PipelineStatus.INCOMPLETE,
                statistics=stats,
                error=str(e),
                retry_scheduled=True,
            )

        except Exception as e:
            # Critical failure - no retry
            logger.error(f"Critical pipeline error: {e}")
            stats.failed = stats.total_found - stats.published

            raise PipelineError(
                f"Pipeline failed: {e}",
                statistics=stats,
            ) from e

    async def _score_items(
        self,
        validated: list[ValidatedResearch],
    ) -> list[TransformedResearch]:
        """Score validated items using the Research Item Scorer.

        Args:
            validated: Validated research items

        Returns:
            TransformedResearch items with scores set
        """
        scored: list[TransformedResearch] = []

        for item in validated:
            try:
                # Convert ValidatedResearch to format scorer expects
                scoring_input = {
                    "title": item.title,
                    "content": item.content,
                    "source": item.source,
                    "source_metadata": item.source_metadata,
                    "tags": item.tags,
                    "created_at": item.created_at,
                    "compliance_status": item.compliance_status,
                }

                # Score the item (calculate_score is synchronous)
                result = self._scorer.calculate_score(scoring_input)

                # Create TransformedResearch with score
                from teams.dawo.research import ResearchSource, ComplianceStatus as RC

                scored_item = TransformedResearch(
                    source=ResearchSource.YOUTUBE,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    tags=item.tags,
                    source_metadata=item.source_metadata,
                    created_at=item.created_at,
                    score=result.final_score,
                    compliance_status=RC(item.compliance_status),
                )
                scored.append(scored_item)

            except Exception as e:
                logger.error(f"Failed to score item '{item.title[:30]}': {e}")
                # Continue with remaining items

        return scored

    async def _publish_items(
        self,
        items: list[TransformedResearch],
    ) -> tuple[int, list[UUID]]:
        """Publish items to Research Pool.

        Args:
            items: Scored research items

        Returns:
            Tuple of (count_published, list_of_ids)
            Note: batch publish returns count but no IDs
        """
        published_ids: list[UUID] = []

        # Use batch publish if available
        try:
            count = await self._publisher.publish_batch(items)
            logger.info(f"Batch published {count} items")
            # Batch doesn't return individual IDs, but returns count
            return count, []
        except Exception as e:
            logger.warning(f"Batch publish failed, falling back to individual: {e}")

        # Fallback to individual publish
        for item in items:
            try:
                result = await self._publisher.publish(item)
                published_ids.append(result.id)
            except Exception as e:
                logger.error(f"Failed to publish item '{item.title[:30]}': {e}")
                # Continue with remaining items

        return len(published_ids), published_ids

    def _determine_status(self, stats: PipelineStatistics) -> PipelineStatus:
        """Determine pipeline completion status from statistics.

        Args:
            stats: Pipeline execution statistics

        Returns:
            Appropriate PipelineStatus
        """
        if stats.published == 0 and stats.total_found > 0:
            return PipelineStatus.FAILED

        if stats.failed > 0:
            return PipelineStatus.PARTIAL

        return PipelineStatus.COMPLETE
