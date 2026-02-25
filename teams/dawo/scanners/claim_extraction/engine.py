"""Health Claim Extraction Engine.

Epic 6, Story 6-6, Task 8: HealthClaimExtractionEngine.

Orchestrates the full extraction pipeline: fetch pending content,
run regex pre-filter, optionally classify via LLM, save claims,
update statuses, and emit events.

Classes:
    HealthClaimExtractionEngine: Main extraction pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventType,
)
from teams.dawo.scanners.claim_extraction.config import HealthClaimExtractionConfig
from teams.dawo.scanners.claim_extraction.schemas import (
    ClaimExtractionResult,
    ExtractionBatchResult,
    PatternMatch,
)

if TYPE_CHECKING:
    from uuid import UUID

    from teams.dawo.scanners.claim_extraction.llm_classifier import ClaimLLMClassifier
    from teams.dawo.scanners.claim_extraction.pattern_matcher import ClaimPatternMatcher
    from teams.dawo.scanners.claim_extraction.repository import HealthClaimRepository
    from teams.dawo.scanners.competitor.repository import CompetitorRepository
    from core.regulatory.events import RegulatoryEventEmitter
    from core.regulatory.models import CompetitorContent

logger = logging.getLogger(__name__)

# Review status constants
REVIEW_AUTO_APPROVED = "auto_approved"
REVIEW_MANUAL_REVIEW = "manual_review"


class HealthClaimExtractionEngine:
    """Extraction pipeline for health claims from competitor content.

    Stages:
        1. Fetch pending content from CompetitorRepository
        2. Run regex pre-filter (ClaimPatternMatcher)
        3. Optionally classify via LLM (ClaimLLMClassifier)
        4. Save claims to HealthClaimRepository
        5. Update extraction_status
        6. Emit events for high-confidence claims

    Args:
        competitor_repository: Repository for reading competitor content.
        claim_repository: Repository for writing extracted claims.
        pattern_matcher: Regex pre-filter.
        llm_classifier: LLM classifier (None = regex-only mode).
        event_emitter: Event emitter for regulatory events.
        config: Extraction configuration.
    """

    def __init__(
        self,
        competitor_repository: CompetitorRepository,
        claim_repository: HealthClaimRepository,
        pattern_matcher: ClaimPatternMatcher,
        llm_classifier: ClaimLLMClassifier | None,
        event_emitter: RegulatoryEventEmitter,
        config: HealthClaimExtractionConfig,
    ) -> None:
        self._competitor_repo = competitor_repository
        self._claim_repo = claim_repository
        self._matcher = pattern_matcher
        self._llm = llm_classifier
        self._emitter = event_emitter
        self._config = config

    async def execute(self) -> ExtractionBatchResult:
        """Run the extraction pipeline.

        Returns:
            ExtractionBatchResult with statistics.
        """
        batch = ExtractionBatchResult()

        # Stage 1: Fetch pending content
        pending = await self._competitor_repo.get_pending_extraction()
        items = list(pending)[: self._config.batch_size]
        logger.info("Extraction engine: %d items to process", len(items))

        # Stage 2-6: Process each item
        for content in items:
            batch.total_processed += 1
            try:
                await self._process_item(content, batch)
            except Exception:
                logger.warning(
                    "Extraction error for content %s", content.id, exc_info=True
                )
                batch.items_error += 1
                await self._claim_repo.update_extraction_status(
                    content.id, "error"
                )

        await self._claim_repo.commit()

        logger.info(
            "Extraction complete: %d processed, %d claims, %d errors",
            batch.total_processed,
            batch.total_claims_extracted,
            batch.items_error,
        )
        return batch

    async def _process_item(self, content: CompetitorContent, batch: ExtractionBatchResult) -> None:
        """Process a single content item through the pipeline."""
        # Stage 2: Regex pre-filter
        matches: list[PatternMatch] = self._matcher.find_matches(content.content_text)

        if not matches:
            # No health claims detected
            batch.items_no_claims += 1
            await self._claim_repo.update_extraction_status(
                content.id, "no_claims"
            )
            return

        # Stage 3: Classify claims
        claims = await self._classify(content.content_text, matches)

        # Cap claims
        if len(claims) > self._config.max_claims_per_content:
            claims.sort(key=lambda c: c.confidence_score, reverse=True)
            claims = claims[: self._config.max_claims_per_content]

        if not claims:
            batch.items_no_claims += 1
            await self._claim_repo.update_extraction_status(
                content.id, "no_claims"
            )
            return

        # Stage 4: Save claims
        saved = await self._claim_repo.save_claims(
            content.id, claims, self._config.confidence_threshold
        )
        batch.total_claims_extracted += saved
        batch.items_with_claims += 1

        # Stage 5: Update extraction status
        await self._claim_repo.update_extraction_status(
            content.id, "extracted"
        )

        # Emit batch-level extraction event
        await self._emitter.emit(
            RegulatoryEvent(
                event_type=RegulatoryEventType.HEALTH_CLAIM_EXTRACTED,
                claim_id="",
                substance="",
                severity="low",
                data={
                    "competitor_content_id": str(content.id),
                    "claims_extracted": saved,
                },
            )
        )

        # Stage 6: Emit events and count review statuses
        for claim in claims:
            if claim.confidence_score >= self._config.confidence_threshold:
                batch.high_confidence_claims += 1
                await self._emit_high_confidence(content.id, claim)
            else:
                batch.manual_review_claims += 1

    async def _classify(
        self, content_text: str, matches: list[PatternMatch]
    ) -> list[ClaimExtractionResult]:
        """Classify matches using LLM or regex-only fallback."""
        if self._config.use_llm and self._llm is not None:
            language_hint = self._matcher.detect_language(content_text)
            return await self._llm.classify_claims(
                content_text, matches, language_hint
            )

        # Regex-only mode: convert PatternMatch to ClaimExtractionResult
        return [
            ClaimExtractionResult(
                claim_text=m.matched_text,
                surrounding_context=m.surrounding_context,
                claim_category=m.category,
                confidence_score=60,
                language_detected=m.language,
                extraction_method="regex",
                eu_article_reference=self._config.eu_article_mapping.get(m.category),
                matched_pattern=m.pattern,
            )
            for m in matches
        ]

    async def _emit_high_confidence(
        self, content_id: UUID, claim: ClaimExtractionResult
    ) -> None:
        """Emit event for a high-confidence claim."""
        severity = "high" if claim.claim_category == "treatment" else "medium"
        await self._emitter.emit(
            RegulatoryEvent(
                event_type=RegulatoryEventType.HIGH_CONFIDENCE_CLAIM_DETECTED,
                claim_id="",
                substance="",
                severity=severity,
                data={
                    "competitor_content_id": str(content_id),
                    "claim_text": claim.claim_text,
                    "claim_category": claim.claim_category,
                    "confidence_score": claim.confidence_score,
                    "language_detected": claim.language_detected,
                    "extraction_method": claim.extraction_method,
                },
            )
        )


__all__ = [
    "HealthClaimExtractionEngine",
]
