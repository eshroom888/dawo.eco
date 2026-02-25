"""Evidence Collector Orchestrator (Story 6-8, Task 8).

Orchestrates batch evidence collection: fetch pending violations,
capture screenshots, store evidence, update statuses, emit events.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from core.regulatory.models import EvidenceCollectionStatus
from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.schemas import (
    CaptureResult,
    CollectionBatchResult,
    EvidenceCreateDTO,
)
from teams.dawo.scanners.evidence_collection.screenshot_service import (
    ScreenshotServiceProtocol,
    _build_instagram_embed_url,
)
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService

if TYPE_CHECKING:
    from core.regulatory.events import RegulatoryEventEmitter
    from core.regulatory.models import CompetitorViolation
    from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
    from teams.dawo.scanners.violation_detection.repository import ViolationRepository

logger = logging.getLogger(__name__)

# Instagram URL detection pattern
_INSTAGRAM_DOMAINS = ("instagram.com", "www.instagram.com")


class EvidenceCollector:
    """Batch evidence collection orchestrator.

    Processes pending violations: captures screenshots, stores evidence,
    updates violation statuses, and emits events.

    Args:
        violation_repository: Repository for pending violations (Story 6-7).
        evidence_repository: Repository for evidence records (this story).
        screenshot_service: Screenshot capture protocol implementation.
        storage_service: File storage with SHA-256 hashing.
        event_emitter: For EVIDENCE_COLLECTED events.
        config: Evidence collection configuration.
    """

    def __init__(
        self,
        violation_repository: ViolationRepository,
        evidence_repository: EvidenceRepository,
        screenshot_service: ScreenshotServiceProtocol,
        storage_service: EvidenceStorageService,
        event_emitter: RegulatoryEventEmitter,
        config: EvidenceCollectionConfig,
    ) -> None:
        self._violation_repository = violation_repository
        self._evidence_repository = evidence_repository
        self._screenshot_service = screenshot_service
        self._storage_service = storage_service
        self._event_emitter = event_emitter
        self._config = config

    async def execute(self) -> CollectionBatchResult:
        """Run batch evidence collection.

        Stage 1: Fetch pending violations (limited by batch_size).
        Stage 2: Filter already-collected (idempotent).
        Stage 3: Process each violation (capture, store, create, emit).
        Stage 4: Commit.

        Returns:
            CollectionBatchResult with statistics.
        """
        batch_result = CollectionBatchResult()

        # Stage 1: Fetch pending violations
        pending = await self._violation_repository.get_pending_evidence_collection()
        pending = list(pending)[: self._config.batch_size]
        batch_result.total_processed = len(pending)

        if not pending:
            logger.info("No pending violations for evidence collection")
            return batch_result

        logger.info("Stage 1: Found %d pending violations", len(pending))

        # Stage 2: Filter already-collected
        collected_ids = await self._evidence_repository.get_collected_violation_ids()
        to_process = []
        for v in pending:
            if v.id in collected_ids:
                batch_result.skipped_already_collected += 1
            else:
                to_process.append(v)

        logger.info(
            "Stage 2: %d to process, %d skipped (already collected)",
            len(to_process),
            batch_result.skipped_already_collected,
        )

        # Stage 3: Process each violation
        for violation in to_process:
            try:
                await self._process_violation(violation, batch_result)
            except Exception as e:
                error_msg = f"Failed for violation {violation.id} ({violation.source_url}): {e}"
                logger.error(error_msg)
                batch_result.failed += 1
                batch_result.errors.append(error_msg)

        # Stage 4: Commit
        await self._evidence_repository.commit()

        logger.info(
            "Stage 4: Batch complete — collected=%d, failed=%d, skipped=%d",
            batch_result.collected,
            batch_result.failed,
            batch_result.skipped_already_collected,
        )

        return batch_result

    async def _process_violation(
        self, violation: CompetitorViolation, batch_result: CollectionBatchResult
    ) -> None:
        """Process a single violation: capture, store, create evidence, emit event.

        Args:
            violation: CompetitorViolation ORM object.
            batch_result: Mutable result to update counters.
        """
        evidence_id = uuid4()
        source_url = violation.source_url
        source_type = self._determine_source_type(source_url)

        # Build capture URL (embed for Instagram)
        capture_url = source_url
        if source_type == "instagram_post":
            capture_url = _build_instagram_embed_url(
                source_url, self._config.instagram_embed_template
            )

        # Capture screenshot
        capture_result = await self._screenshot_service.capture(
            capture_url,
            full_page=self._config.full_page,
            viewport_width=self._config.viewport_width,
            viewport_height=self._config.viewport_height,
        )

        # Store to filesystem
        screenshot_path, screenshot_hash, screenshot_size = (
            await self._storage_service.store_screenshot(
                capture_result.screenshot_bytes, evidence_id
            )
        )

        # Extract claim data from violation's extracted_claim relationship
        claim = violation.extracted_claim
        claim_text = claim.claim_text
        claim_category = claim.claim_category
        confidence = claim.confidence_score / 100.0  # Normalize 0-100 to 0.0-1.0

        # Build evidence metadata
        metadata = self._build_evidence_metadata(capture_result)

        # Create evidence record
        dto = EvidenceCreateDTO(
            violation_id=violation.id,
            competitor_name=violation.competitor_name,
            source_url=source_url,
            source_type=source_type,
            claim_text=claim_text,
            claim_category=claim_category,
            violation_type=violation.violation_type,
            severity=violation.severity,
            regulation_violated=violation.regulation_article,
            detection_reasoning=violation.detection_reasoning,
            confidence=confidence,
            screenshot_path=screenshot_path,
            screenshot_hash=screenshot_hash,
            screenshot_size_bytes=screenshot_size,
            captured_at=capture_result.captured_at,
            evidence_metadata=metadata,
        )

        evidence = await self._evidence_repository.create(dto)

        # Update violation status
        violation.evidence_status = EvidenceCollectionStatus.COLLECTED.value

        # Emit event
        await self._event_emitter.emit(
            RegulatoryEvent(
                event_type=RegulatoryEventType.EVIDENCE_COLLECTED,
                claim_id=str(violation.extracted_claim_id),
                severity=violation.severity,
                data={
                    "violation_id": str(violation.id),
                    "evidence_id": str(evidence.id),
                    "competitor_name": violation.competitor_name,
                    "source_url": source_url,
                    "screenshot_hash": screenshot_hash,
                    "screenshot_path": screenshot_path,
                },
            )
        )

        batch_result.collected += 1
        logger.debug(
            "Collected evidence for violation %s (competitor=%s)",
            violation.id,
            violation.competitor_name,
        )

    @staticmethod
    def _determine_source_type(url: str) -> str:
        """Classify URL as instagram_post or website_page.

        Args:
            url: Source URL to classify.

        Returns:
            'instagram_post' or 'website_page'.
        """
        for domain in _INSTAGRAM_DOMAINS:
            if domain in url:
                return "instagram_post"
        return "website_page"

    def _build_evidence_metadata(
        self, capture_result: CaptureResult
    ) -> dict:
        """Build JSONB metadata dict for evidence record.

        Args:
            capture_result: CaptureResult from screenshot service.

        Returns:
            Metadata dict with page_title, capture_url, viewport.
        """
        return {
            "page_title": capture_result.page_title,
            "capture_url": capture_result.url,
            "viewport_width": self._config.viewport_width,
            "viewport_height": self._config.viewport_height,
        }


__all__ = [
    "EvidenceCollector",
]
