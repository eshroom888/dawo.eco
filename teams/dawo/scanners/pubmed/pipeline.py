"""PubMed Research Pipeline - Orchestrates full scanner pipeline.

Orchestrates all stages of the Harvester Framework:
    Scanner -> Harvester -> FindingSummarizer -> ClaimValidator -> Transformer -> Validator -> Scorer -> Publisher

The PubMedResearchPipeline:
    1. Executes scanner to find articles
    2. Harvests articles with metadata
    3. Summarizes findings with LLM
    4. Validates claim potential with LLM
    5. Transforms to Research Pool format
    6. Validates EU compliance
    7. Scores research relevance
    8. Publishes to Research Pool

Registration: team_spec.py as RegisteredService with capability="pubmed_research"

Usage:
    # Created by Team Builder with all injected components
    pipeline = PubMedResearchPipeline(
        scanner, harvester, summarizer, claim_validator,
        transformer, validator, scorer, publisher
    )

    # Execute full pipeline
    result = await pipeline.execute()
"""

import logging
from typing import Any, Optional, Protocol
from uuid import UUID

from .schemas import (
    PipelineResult,
    PipelineStatus,
    PipelineStatistics,
    ValidatedResearch,
    StudyType,
)
from .agent import PubMedScanner, PubMedScanError
from .harvester import PubMedHarvester
from .finding_summarizer import FindingSummarizer
from .claim_validator import ClaimValidator
from .transformer import PubMedTransformer
from .validator import PubMedValidator


# Module logger
logger = logging.getLogger(__name__)


class ResearchScorerProtocol(Protocol):
    """Protocol for research item scorer dependency injection."""

    def score(self, item: Any) -> Any:
        """Score a research item.

        Args:
            item: Research item to score

        Returns:
            Score result with final_score attribute
        """
        ...


class ResearchPublisherProtocol(Protocol):
    """Protocol for research publisher dependency injection."""

    async def publish_batch(self, items: list[Any]) -> list[Any]:
        """Publish batch of research items.

        Args:
            items: Items to publish

        Returns:
            List of published item results
        """
        ...


# Score boosts for study types (peer-reviewed content is premium)
STUDY_TYPE_BOOSTS = {
    StudyType.RCT: 2.0,
    StudyType.META_ANALYSIS: 2.5,
    StudyType.SYSTEMATIC_REVIEW: 2.0,
    StudyType.REVIEW: 1.0,
    StudyType.OTHER: 0.5,
}

# Recency boost for recent publications
RECENCY_BOOST = 0.5  # For publications in last 30 days


class PipelineError(Exception):
    """Exception raised for pipeline errors.

    Attributes:
        message: Error description
        stage: Pipeline stage that failed
    """

    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.stage = stage


class PubMedResearchPipeline:
    """PubMed Research Pipeline - Orchestrates full scanner pipeline.

    Chains all pipeline stages:
        scan -> harvest -> summarize -> validate_claims -> transform -> validate -> score -> publish

    Features:
        - Full pipeline orchestration
        - Graceful degradation on failures
        - Partial success tracking
        - Statistics reporting
        - Study type score boosting

    All dependencies are injected via constructor.

    Attributes:
        _scanner: PubMed scanner for article discovery
        _harvester: Harvester for metadata extraction
        _summarizer: Finding summarizer (LLM)
        _claim_validator: Claim validator (LLM)
        _transformer: Transformer to Research Pool format
        _validator: EU compliance validator
        _scorer: Research item scorer
        _publisher: Research publisher
    """

    def __init__(
        self,
        scanner: PubMedScanner,
        harvester: PubMedHarvester,
        summarizer: FindingSummarizer,
        claim_validator: ClaimValidator,
        transformer: PubMedTransformer,
        validator: PubMedValidator,
        scorer: ResearchScorerProtocol,
        publisher: ResearchPublisherProtocol,
    ):
        """Initialize pipeline with all stage components.

        Args:
            scanner: PubMed scanner for article discovery
            harvester: Harvester for metadata extraction
            summarizer: Finding summarizer (LLM)
            claim_validator: Claim validator (LLM)
            transformer: Transformer to Research Pool format
            validator: EU compliance validator
            scorer: Research item scorer (Story 2.2)
            publisher: Research publisher (Story 2.1)
        """
        self._scanner = scanner
        self._harvester = harvester
        self._summarizer = summarizer
        self._claim_validator = claim_validator
        self._transformer = transformer
        self._validator = validator
        self._scorer = scorer
        self._publisher = publisher

    async def execute(self) -> PipelineResult:
        """Execute full pipeline.

        Returns:
            PipelineResult with status and statistics

        Note:
            Implements graceful degradation - continues on partial failures
        """
        stats = PipelineStatistics()
        published_ids: list[UUID] = []
        errors: list[str] = []

        try:
            # Stage 1: Scan
            logger.info("Starting PubMed research pipeline")
            scan_result = await self._execute_scan(stats, errors)
            if scan_result is None:
                return self._incomplete_result(stats, errors)

            # Stage 2: Harvest
            harvested = await self._execute_harvest(scan_result, stats, errors)
            if not harvested:
                return self._incomplete_result(stats, errors)

            # Stage 3: Summarize findings
            summaries = await self._execute_summarize(harvested, stats, errors)

            # Stage 4: Validate claims
            validations = await self._execute_validate_claims(summaries, stats, errors)

            # Stage 5: Transform
            transformed = await self._execute_transform(
                harvested, summaries, validations, stats, errors
            )
            if not transformed:
                return self._partial_result(stats, errors, published_ids)

            # Stage 6: Validate compliance
            validated = await self._execute_validate(transformed, stats, errors)

            # Stage 7: Score
            scored = await self._execute_score(validated, harvested, stats, errors)

            # Stage 8: Publish
            published_ids = await self._execute_publish(scored, stats, errors)

            # Determine final status
            if stats.failed > 0:
                status = PipelineStatus.PARTIAL
            else:
                status = PipelineStatus.COMPLETE

            logger.info(
                "Pipeline complete: %s - published %d items",
                status.value,
                len(published_ids),
            )

            return PipelineResult(
                status=status,
                statistics=stats,
                error="; ".join(errors) if errors else None,
                retry_scheduled=False,
                published_ids=published_ids,
            )

        except PubMedScanError as e:
            logger.error("Pipeline failed at scan stage: %s", e)
            return PipelineResult(
                status=PipelineStatus.INCOMPLETE,
                statistics=stats,
                error=f"Scan failed: {e.message}",
                retry_scheduled=True,
                published_ids=[],
            )
        except Exception as e:
            logger.error("Pipeline failed with unexpected error: %s", e)
            return PipelineResult(
                status=PipelineStatus.FAILED,
                statistics=stats,
                error=f"Unexpected error: {str(e)}",
                retry_scheduled=True,
                published_ids=published_ids,
            )

    async def _execute_scan(
        self,
        stats: PipelineStatistics,
        errors: list[str],
    ):
        """Execute scan stage."""
        logger.info("Executing scan stage")
        scan_result = await self._scanner.scan()

        stats.total_found = len(scan_result.articles)
        stats.queries_executed = scan_result.statistics.queries_executed
        stats.queries_failed = scan_result.statistics.queries_failed

        if scan_result.errors:
            errors.extend(scan_result.errors)

        if not scan_result.articles:
            errors.append("No articles found")
            return None

        return scan_result.articles

    async def _execute_harvest(
        self,
        raw_articles,
        stats: PipelineStatistics,
        errors: list[str],
    ):
        """Execute harvest stage."""
        logger.info("Executing harvest stage")
        harvested = await self._harvester.harvest(raw_articles)

        stats.harvested = len(harvested)

        if not harvested:
            errors.append("No articles harvested")

        return harvested

    async def _execute_summarize(
        self,
        harvested,
        stats: PipelineStatistics,
        errors: list[str],
    ):
        """Execute summarize stage."""
        logger.info("Executing summarize stage")
        summaries = await self._summarizer.summarize_batch(harvested)

        stats.summarized = len(summaries)

        return summaries

    async def _execute_validate_claims(
        self,
        summaries,
        stats: PipelineStatistics,
        errors: list[str],
    ):
        """Execute claim validation stage."""
        logger.info("Executing claim validation stage")
        validations = await self._claim_validator.validate_batch(summaries)

        stats.claim_validated = len(validations)

        return validations

    async def _execute_transform(
        self,
        harvested,
        summaries,
        validations,
        stats: PipelineStatistics,
        errors: list[str],
    ):
        """Execute transform stage."""
        logger.info("Executing transform stage")
        transformed = await self._transformer.transform(
            harvested, summaries, validations
        )

        stats.transformed = len(transformed)

        if not transformed:
            errors.append("No articles transformed")

        return transformed

    async def _execute_validate(
        self,
        transformed,
        stats: PipelineStatistics,
        errors: list[str],
    ):
        """Execute validation stage."""
        logger.info("Executing validation stage")
        validated = await self._validator.validate(transformed)

        stats.validated = len([v for v in validated if v.compliance_status != "REJECTED"])

        return validated

    async def _execute_score(
        self,
        validated: list[ValidatedResearch],
        harvested,
        stats: PipelineStatistics,
        errors: list[str],
    ) -> list[ValidatedResearch]:
        """Execute scoring stage with study type boosts."""
        logger.info("Executing score stage")
        scored: list[ValidatedResearch] = []

        # Build PMID to harvested article lookup
        harvested_lookup = {h.pmid: h for h in harvested}

        for item in validated:
            try:
                # Get base score from scorer
                score_result = self._scorer.score(item)
                base_score = score_result.final_score if score_result else 5.0

                # Apply study type boost
                harvested_article = harvested_lookup.get(item.source_id)
                if harvested_article:
                    boost = STUDY_TYPE_BOOSTS.get(harvested_article.study_type, 0.5)
                    base_score = min(10.0, base_score + boost)

                # Create scored copy
                scored_item = ValidatedResearch(
                    source=item.source,
                    source_id=item.source_id,
                    title=item.title,
                    content=item.content,
                    summary=item.summary,
                    url=item.url,
                    tags=item.tags,
                    source_metadata=item.source_metadata,
                    created_at=item.created_at,
                    compliance_status=item.compliance_status,
                    score=base_score,
                )
                scored.append(scored_item)

            except Exception as e:
                logger.warning("Failed to score %s: %s", item.source_id, e)
                scored.append(item)  # Keep original score
                stats.failed += 1

        stats.scored = len(scored)

        return scored

    async def _execute_publish(
        self,
        scored: list[ValidatedResearch],
        stats: PipelineStatistics,
        errors: list[str],
    ) -> list[UUID]:
        """Execute publish stage."""
        logger.info("Executing publish stage")
        published_ids: list[UUID] = []

        # Filter out rejected items
        publishable = [s for s in scored if s.compliance_status != "REJECTED"]

        try:
            # Publish batch
            results = await self._publisher.publish_batch(publishable)

            for result in results:
                if hasattr(result, "id"):
                    published_ids.append(result.id)

            stats.published = len(published_ids)

        except Exception as e:
            logger.error("Failed to publish batch: %s", e)
            errors.append(f"Publish failed: {str(e)}")
            stats.failed += len(publishable)

        return published_ids

    def _incomplete_result(
        self,
        stats: PipelineStatistics,
        errors: list[str],
    ) -> PipelineResult:
        """Create INCOMPLETE result for scan failures."""
        return PipelineResult(
            status=PipelineStatus.INCOMPLETE,
            statistics=stats,
            error="; ".join(errors) if errors else "No articles found",
            retry_scheduled=True,
            published_ids=[],
        )

    def _partial_result(
        self,
        stats: PipelineStatistics,
        errors: list[str],
        published_ids: list[UUID],
    ) -> PipelineResult:
        """Create PARTIAL result for partial failures."""
        return PipelineResult(
            status=PipelineStatus.PARTIAL,
            statistics=stats,
            error="; ".join(errors) if errors else None,
            retry_scheduled=False,
            published_ids=published_ids,
        )
