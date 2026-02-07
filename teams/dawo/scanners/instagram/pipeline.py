"""Instagram Research Pipeline - orchestrates full Harvester Framework pipeline.

Implements the complete pipeline orchestration:
    [Scanner] → [Harvester] → [ThemeExtractor] → [ClaimDetector] → [Transformer] → [Validator] → [Scorer] → [Publisher] → [Research Pool]

UNIQUE to Instagram:
    - TWO LLM stages: ThemeExtractor AND HealthClaimDetector (both tier="generate")
    - CleanMarket flagging for Epic 6 integration
    - RateLimitError handled separately with retry_after timestamp
    - Statistics include themes_extracted, claims_detected, cleanmarket_flagged

The pipeline chains all stages together with:
    - Statistics tracking through each stage
    - Graceful degradation on API failures
    - Rate limit exhaustion handling (wait until hour reset)
    - Partial failure handling (continue on item failures)
    - Comprehensive logging

Usage:
    pipeline = InstagramResearchPipeline(
        scanner, harvester, theme_extractor, claim_detector,
        transformer, validator, scorer, publisher
    )
    result = await pipeline.execute()
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from teams.dawo.research import (
    ResearchPublisher,
    TransformedResearch,
    ResearchSource,
    ComplianceStatus,
)
from teams.dawo.research.scoring import ResearchItemScorer

from .agent import InstagramScanner
from .harvester import InstagramHarvester
from .theme_extractor import ThemeExtractor
from .claim_detector import HealthClaimDetector
from .transformer import InstagramTransformer
from .validator import InstagramValidator
from .schemas import (
    PipelineResult,
    PipelineStatistics,
    PipelineStatus,
    ValidatedResearch,
)
from .tools import InstagramAPIError, RateLimitError


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


class InstagramResearchPipeline:
    """Instagram Research Pipeline - orchestrates complete Harvester Framework.

    Chains all pipeline stages together:
        scan → harvest → extract_themes → detect_claims → transform → validate → score → publish

    UNIQUE to Instagram:
        - TWO LLM stages for theme extraction and claim detection
        - CleanMarket flagging for competitor health claims (Epic 6)
        - Rate limit handling with retry_after timestamp

    Features:
        - Full stage orchestration
        - Statistics tracking per stage
        - Graceful degradation on Instagram API failure
        - Rate limit exhaustion handling (RATE_LIMITED status)
        - Partial failure handling (items can fail individually)
        - Retry scheduling on incomplete runs

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _scanner: InstagramScanner for post discovery
        _harvester: InstagramHarvester for metadata enrichment
        _transformer: InstagramTransformer for schema conversion (includes LLM stages)
        _validator: InstagramValidator for compliance checking
        _scorer: ResearchItemScorer for relevance scoring
        _publisher: ResearchPublisher for database persistence
    """

    def __init__(
        self,
        scanner: InstagramScanner,
        harvester: InstagramHarvester,
        transformer: InstagramTransformer,
        validator: InstagramValidator,
        scorer: ResearchItemScorer,
        publisher: ResearchPublisher,
    ):
        """Initialize pipeline with injected stage components.

        Args:
            scanner: Post discovery stage
            harvester: Metadata enrichment stage
            transformer: Schema conversion stage (includes ThemeExtractor and ClaimDetector)
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
        and RATE_LIMITED on rate limit exhaustion (with retry_after).

        Returns:
            PipelineResult with status, statistics, and published IDs

        Note:
            - COMPLETE: All stages ran successfully
            - INCOMPLETE: Instagram API failure, retry scheduled
            - PARTIAL: Some items failed but pipeline completed
            - FAILED: Critical error, no retry
            - RATE_LIMITED: Hourly rate limit exhausted, retry in ~1 hour
        """
        logger.info("Starting Instagram Research Pipeline execution")

        stats = PipelineStatistics()
        published_ids: list[UUID] = []

        try:
            # Stage 1: Scan - Discover posts
            logger.info("Stage 1/6: Scanning Instagram")
            scan_result = await self._scanner.scan()
            stats.total_found = len(scan_result.posts)
            stats.api_calls_made = scan_result.statistics.api_calls_made
            logger.info("Scan complete: %d posts found", stats.total_found)

            if not scan_result.posts:
                logger.info("No posts found, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=stats,
                )

            # Stage 2: Harvest - Enrich with metadata
            logger.info("Stage 2/6: Harvesting post metadata")
            harvested = await self._harvester.harvest(scan_result.posts)
            stats.harvested = len(harvested)
            logger.info("Harvest complete: %d posts enriched", stats.harvested)

            if not harvested:
                logger.info("No posts harvested, pipeline complete")
                return PipelineResult(
                    status=PipelineStatus.COMPLETE,
                    statistics=stats,
                )

            # Stage 3: Transform - Convert to Research Pool schema (includes LLM stages)
            logger.info("Stage 3/6: Transforming to Research Pool schema (with theme + claim extraction)")
            transformed = await self._transformer.transform(harvested)
            stats.transformed = len(transformed)

            # Count themes and claims from metadata
            stats.themes_extracted = sum(
                1 for t in transformed if t.source_metadata.get("theme")
            )
            stats.claims_detected = sum(
                1 for t in transformed if t.source_metadata.get("detected_claims")
            )
            stats.cleanmarket_flagged = sum(
                1 for t in transformed
                if t.source_metadata.get("overall_risk_level", "none") != "none"
            )
            logger.info(
                "Transform complete: %d items, %d with themes, %d with claims",
                stats.transformed,
                stats.themes_extracted,
                stats.claims_detected,
            )

            # Stage 4: Validate - Check EU compliance
            logger.info("Stage 4/6: Validating EU compliance")
            validated = await self._validator.validate(transformed)
            stats.validated = len(validated)
            logger.info("Validation complete: %d items validated", stats.validated)

            # Stage 5: Score - Calculate relevance scores
            logger.info("Stage 5/6: Scoring research items")
            scored = await self._score_items(validated)
            stats.scored = len(scored)
            logger.info("Scoring complete: %d items scored", stats.scored)

            # Stage 6: Publish - Save to Research Pool
            logger.info("Stage 6/6: Publishing to Research Pool")
            publish_count, published_ids = await self._publish_items(scored)
            stats.published = publish_count
            stats.failed = stats.scored - stats.published
            logger.info("Publish complete: %d items published", stats.published)

            # Determine final status
            status = self._determine_status(stats)

            logger.info(
                "Pipeline complete: status=%s, published=%d/%d",
                status.value,
                stats.published,
                stats.total_found,
            )

            return PipelineResult(
                status=status,
                statistics=stats,
                published_ids=published_ids,
            )

        except RateLimitError as e:
            # Special handling for rate limit - retry in ~1 hour
            logger.warning("Instagram rate limit exceeded: %s", e)
            stats.failed = stats.total_found - stats.published

            # Calculate retry time as 1 hour from now (Instagram resets hourly)
            retry_after = datetime.now(timezone.utc) + timedelta(hours=1)

            return PipelineResult(
                status=PipelineStatus.RATE_LIMITED,
                statistics=stats,
                error=str(e),
                retry_scheduled=True,
                retry_after=retry_after,
            )

        except InstagramAPIError as e:
            # Graceful degradation - mark as incomplete for retry
            logger.error("Instagram API failure: %s", e)
            stats.failed = stats.total_found - stats.published

            return PipelineResult(
                status=PipelineStatus.INCOMPLETE,
                statistics=stats,
                error=str(e),
                retry_scheduled=True,
            )

        except Exception as e:
            # Critical failure - no retry
            logger.error("Critical pipeline error: %s", e)
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

                # Boost score for high engagement
                engagement_boost = self._calculate_engagement_boost(item.source_metadata)
                final_score = min(10.0, result.final_score + engagement_boost)

                # Create TransformedResearch with score
                scored_item = TransformedResearch(
                    source=ResearchSource.INSTAGRAM,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    tags=item.tags,
                    source_metadata=item.source_metadata,
                    created_at=item.created_at,
                    score=final_score,
                    compliance_status=ComplianceStatus(item.compliance_status),
                )
                scored.append(scored_item)

            except Exception as e:
                logger.error("Failed to score item '%s': %s", item.title[:30], e)
                # Continue with remaining items

        return scored

    def _calculate_engagement_boost(self, metadata: dict) -> float:
        """Calculate score boost based on engagement metrics.

        Args:
            metadata: Source metadata with likes/comments

        Returns:
            Score boost (0.0 to 2.0)
        """
        likes = metadata.get("likes", 0)
        comments = metadata.get("comments", 0)

        # Boost based on engagement tiers
        engagement = likes + (comments * 5)  # Comments weighted higher

        if engagement >= 10000:
            return 2.0
        elif engagement >= 5000:
            return 1.5
        elif engagement >= 1000:
            return 1.0
        elif engagement >= 500:
            return 0.5
        return 0.0

    async def _publish_items(
        self,
        items: list[TransformedResearch],
    ) -> tuple[int, list[UUID]]:
        """Publish items to Research Pool.

        Args:
            items: Scored research items

        Returns:
            Tuple of (count_published, list_of_ids)
        """
        published_ids: list[UUID] = []

        # Use batch publish if available
        try:
            count = await self._publisher.publish_batch(items)
            logger.info("Batch published %d items", count)
            return count, []
        except Exception as e:
            logger.warning("Batch publish failed, falling back to individual: %s", e)

        # Fallback to individual publish
        for item in items:
            try:
                result = await self._publisher.publish(item)
                published_ids.append(result.id)
            except Exception as e:
                logger.error("Failed to publish item '%s': %s", item.title[:30], e)
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
