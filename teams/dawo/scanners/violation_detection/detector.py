"""Violation Detector Engine (Story 6-7, Task 7).

Orchestrates the violation detection pipeline:
1. Fetch high-confidence extracted claims
2. Filter already-evaluated claims (idempotency)
3. Load EU Health Claims Register
4. Classify each claim
5. Save all violations
6. Emit events
7. Commit
"""

import logging
from typing import Sequence

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventEmitter,
    RegulatoryEventType,
)
from core.regulatory.models import ExtractedHealthClaim, HealthClaim
from teams.dawo.scanners.claim_extraction.repository import HealthClaimRepository
from teams.dawo.scanners.health_claims.repository import HealthClaimsRepository
from teams.dawo.scanners.violation_detection.classifier import ViolationClassifier
from teams.dawo.scanners.violation_detection.config import ViolationDetectionConfig
from teams.dawo.scanners.violation_detection.repository import ViolationRepository
from teams.dawo.scanners.violation_detection.schemas import (
    DetectionBatchResult,
    ViolationResult,
)

logger = logging.getLogger(__name__)


class ViolationDetector:
    """Orchestrates EU violation detection pipeline.

    Accepts all dependencies via constructor.

    Args:
        claim_repository: HealthClaimRepository for fetching extracted claims.
        health_claims_repository: HealthClaimsRepository for EU register data.
        violation_repository: ViolationRepository for saving violations.
        classifier: ViolationClassifier for classification logic.
        event_emitter: RegulatoryEventEmitter for emitting events.
        config: ViolationDetectionConfig with detection settings.
    """

    def __init__(
        self,
        claim_repository: HealthClaimRepository,
        health_claims_repository: HealthClaimsRepository,
        violation_repository: ViolationRepository,
        classifier: ViolationClassifier,
        event_emitter: RegulatoryEventEmitter,
        config: ViolationDetectionConfig,
    ) -> None:
        self._claim_repo = claim_repository
        self._health_claims_repo = health_claims_repository
        self._violation_repo = violation_repository
        self._classifier = classifier
        self._event_emitter = event_emitter
        self._config = config

    async def execute(self) -> DetectionBatchResult:
        """Execute the violation detection pipeline.

        Returns:
            DetectionBatchResult with aggregate statistics.
        """
        batch = DetectionBatchResult()

        # Stage 1: Fetch high-confidence claims (with eager-loaded competitor_content)
        # Fetch batch_size * 3 to account for already-evaluated claims being filtered
        fetch_limit = self._config.batch_size * 3
        logger.info(
            "Stage 1: Fetching claims with confidence >= %d (limit %d)",
            self._config.min_confidence,
            fetch_limit,
        )
        claims = await self._claim_repo.get_high_confidence_claims(
            self._config.min_confidence, limit=fetch_limit
        )
        logger.info("Stage 1: Found %d high-confidence claims", len(claims))

        if not claims:
            logger.info("No high-confidence claims found. Exiting.")
            return batch

        # Stage 2: Filter already-evaluated (idempotency)
        logger.info("Stage 2: Checking for already-evaluated claims")
        evaluated_ids = await self._violation_repo.get_evaluated_claim_ids()

        new_claims = []
        for claim in claims:
            if claim.id in evaluated_ids:
                batch.skipped_already_evaluated += 1
            else:
                new_claims.append(claim)

        logger.info(
            "Stage 2: %d new claims, %d skipped (already evaluated)",
            len(new_claims),
            batch.skipped_already_evaluated,
        )

        if not new_claims:
            logger.info("All claims already evaluated. Exiting.")
            return batch

        # Limit to batch_size
        new_claims = new_claims[: self._config.batch_size]

        # Stage 3: Load EU register
        logger.info("Stage 3: Loading EU Health Claims Register")
        authorized_claims = await self._load_authorized_claims()
        logger.info(
            "Stage 3: Loaded %d authorized claims", len(authorized_claims)
        )

        # Stage 4: Classify each claim
        logger.info("Stage 4: Classifying %d claims", len(new_claims))
        results: list[ViolationResult] = []

        for claim in new_claims:
            try:
                competitor_name = claim.competitor_content.competitor_name
                source_url = claim.competitor_content.source_url

                result = self._classifier.classify(
                    claim=claim,
                    authorized_claims=authorized_claims,
                    competitor_name=competitor_name,
                    source_url=source_url,
                )
                results.append(result)
                batch.total_processed += 1

                if result.violation_status == "violation":
                    batch.violations_found += 1
                elif result.violation_status == "suspect":
                    batch.suspects_found += 1
                else:
                    batch.compliant_found += 1

            except Exception:
                logger.debug(
                    "Error classifying claim %s", claim.id, exc_info=True
                )
                batch.errors += 1

        logger.info(
            "Stage 4: Classified %d claims: %d violations, %d suspects, "
            "%d compliant, %d errors",
            batch.total_processed,
            batch.violations_found,
            batch.suspects_found,
            batch.compliant_found,
            batch.errors,
        )

        if not results:
            return batch

        # Stage 5: Save violations (ALL classifications for audit trail)
        logger.info("Stage 5: Saving %d violation records", len(results))
        await self._violation_repo.save_violations_batch(results)

        # Stage 6: Emit events
        logger.info("Stage 6: Emitting events")
        for result in results:
            if result.violation_status == "violation":
                await self._emit_violation_event(result)
            elif result.violation_status == "suspect":
                await self._emit_suspect_event(result)

        # Stage 7: Commit
        logger.info("Stage 7: Committing transaction")
        await self._violation_repo.commit()

        logger.info(
            "Pipeline complete: %d processed, %d violations, %d suspects",
            batch.total_processed,
            batch.violations_found,
            batch.suspects_found,
        )
        return batch

    async def _load_authorized_claims(self) -> Sequence[HealthClaim]:
        """Load authorized claims from EU Health Claims Register.

        Returns empty list if no register data available.
        """
        snapshot = await self._health_claims_repo.get_latest_snapshot()
        if snapshot is None:
            logger.warning(
                "No EU Health Claims Register snapshot available. "
                "Classifying with empty authorized claims list."
            )
            return []
        return await self._health_claims_repo.get_relevant_claims(snapshot.id)

    async def _emit_violation_event(self, result: ViolationResult) -> None:
        """Emit EU_VIOLATION_DETECTED event for a violation."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.EU_VIOLATION_DETECTED,
            claim_id=str(result.extracted_claim_id),
            substance="",
            severity=result.severity,
            data={
                "competitor_name": result.competitor_name,
                "source_url": result.source_url,
                "claim_text": result.claim_text,
                "claim_category": result.claim_category,
                "violation_type": result.violation_type,
                "regulation_article": result.regulation_article,
                "confidence_score": result.confidence_score,
                "evidence_status": result.evidence_status,
            },
        )
        await self._event_emitter.emit(event)

    async def _emit_suspect_event(self, result: ViolationResult) -> None:
        """Emit SUSPECT_CLAIM_FLAGGED event for a suspect claim."""
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.SUSPECT_CLAIM_FLAGGED,
            claim_id=str(result.extracted_claim_id),
            substance="",
            severity=result.severity,
            data={
                "competitor_name": result.competitor_name,
                "source_url": result.source_url,
                "claim_text": result.claim_text,
                "claim_category": result.claim_category,
                "violation_type": result.violation_type,
                "regulation_article": result.regulation_article,
                "confidence_score": result.confidence_score,
                "evidence_status": result.evidence_status,
            },
        )
        await self._event_emitter.emit(event)


__all__ = [
    "ViolationDetector",
]
