"""Health Claims Monitor pipeline.

Epic 6, Story 6-1, Task 9: Monitor pipeline.

Orchestrates the full monitoring flow: download → parse → filter → detect → save → publish events.
"""

import hashlib
import logging
from typing import Optional

import pandas as pd

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType, RegulatoryEventEmitter
from core.regulatory.models import ChangeType, ChangeSeverity
from teams.dawo.scanners.health_claims.client import HealthClaimsClient, HealthClaimsClientError
from teams.dawo.scanners.health_claims.parser import RegisterParser, ParseError
from teams.dawo.scanners.health_claims.relevance_filter import RelevanceFilter
from teams.dawo.scanners.health_claims.change_detector import ChangeDetector
from teams.dawo.scanners.health_claims.repository import HealthClaimsRepository
from teams.dawo.scanners.health_claims.schemas import MonitorResult, MonitorStatus

logger = logging.getLogger(__name__)


class HealthClaimsMonitorPipeline:
    """Pipeline for monitoring the EU Health Claims Register.

    Story 6-1, Task 9: Orchestrates download → parse → filter → detect → save → events.

    Accepts all dependencies via constructor (DI).

    Pipeline stages:
        1. Download register (client)
        2. Parse to DataFrame (parser)
        3. Load previous snapshot from DB (repository)
        4. Filter for relevant claims (filter)
        5. Detect changes vs previous (detector)
        6. Save new snapshot + claims (repository)
        7. Save change records (repository)
        8. Publish events for high-severity changes (event_emitter)
    """

    def __init__(
        self,
        client: HealthClaimsClient,
        parser: RegisterParser,
        relevance_filter: RelevanceFilter,
        change_detector: ChangeDetector,
        repository: HealthClaimsRepository,
        event_emitter: RegulatoryEventEmitter,
        source_url: str = "",
    ) -> None:
        """Initialize monitor pipeline.

        Args:
            client: HTTP client for downloading register
            parser: Parser for XLS/CSV data
            relevance_filter: Keyword-based relevance filter
            change_detector: Change detection between snapshots
            repository: Database persistence layer
            event_emitter: Event emitter for downstream consumers
            source_url: EU Open Data Portal URL for metadata
        """
        self._client = client
        self._parser = parser
        self._filter = relevance_filter
        self._detector = change_detector
        self._repository = repository
        self._event_emitter = event_emitter
        self._source_url = source_url

    async def execute(self) -> MonitorResult:
        """Execute the full monitoring pipeline.

        Returns:
            MonitorResult with execution summary and statistics
        """
        result = MonitorResult()

        # Stage 1: Download register
        try:
            raw_data = await self._client.download_register()
            logger.info("Stage 1: Downloaded %d bytes", len(raw_data))
        except HealthClaimsClientError as e:
            logger.error("Stage 1 failed: Download error: %s", e)
            result.status = MonitorStatus.INCOMPLETE
            result.errors.append(f"Download failed: {e}")
            return result

        # Stage 2: Parse to DataFrame
        try:
            df = self._parser.parse(raw_data)
            result.claim_count = len(df)
            logger.info("Stage 2: Parsed %d claims", len(df))
        except ParseError as e:
            logger.error("Stage 2 failed: Parse error: %s", e.detail)
            result.status = MonitorStatus.INCOMPLETE
            result.errors.append(f"Parse failed: {e.detail}")
            return result

        # Stage 3: Load previous snapshot
        previous_snapshot = await self._repository.get_latest_snapshot()
        previous_df = pd.DataFrame()
        if previous_snapshot:
            previous_claims = await self._repository.get_claims_by_snapshot(previous_snapshot.id)
            if previous_claims:
                previous_df = pd.DataFrame([
                    {
                        "claim_id": c.claim_id,
                        "claim_type": c.claim_type,
                        "substance": c.substance,
                        "health_relationship": c.health_relationship,
                        "claim_text": c.claim_text,
                        "conditions_of_use": c.conditions_of_use,
                        "food_category": c.food_category,
                        "status": c.status,
                        "efsa_opinion": c.efsa_opinion,
                        "commission_regulation": c.commission_regulation,
                        "restrictions": c.restrictions,
                    }
                    for c in previous_claims
                ])
            logger.info("Stage 3: Loaded previous snapshot with %d claims", len(previous_df))
        else:
            logger.info("Stage 3: No previous snapshot (first run)")

        # Stage 4: Annotate claims with relevance flags
        annotated_df, filter_stats = self._filter.filter(df)
        result.relevant_count = filter_stats.relevant_claims
        logger.info("Stage 4: %d relevant claims", filter_stats.relevant_claims)

        # Stage 5: Detect changes vs previous
        changes = self._detector.detect(previous_df, df)
        result.changes_detected = len(changes)
        result.new_claims = sum(1 for c in changes if c.change_type == ChangeType.NEW.value)
        result.removed_claims = sum(1 for c in changes if c.change_type == ChangeType.REMOVED.value)
        result.modified_claims = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED.value)
        result.status_changes = sum(1 for c in changes if c.change_type == ChangeType.STATUS_CHANGED.value)
        logger.info("Stage 5: %d changes detected", len(changes))

        # Stage 6: Save new snapshot + claims
        snapshot = await self._repository.save_snapshot(
            annotated_df,
            self._source_url,
            len(raw_data),
        )
        result.snapshot_hash = snapshot.snapshot_hash
        logger.info("Stage 6: Saved snapshot %s", snapshot.id)

        # Stage 7: Save change records
        if changes:
            await self._repository.save_changes(changes, snapshot.id)
            logger.info("Stage 7: Saved %d change records", len(changes))

        # Commit all saves atomically (snapshot + changes)
        await self._repository.commit()

        # Stage 8: Publish events for high-severity changes
        critical_changes = [c for c in changes if c.severity in (ChangeSeverity.HIGH.value, ChangeSeverity.CRITICAL.value)]
        for change in critical_changes:
            event_type = RegulatoryEventType.CLAIM_STATUS_CHANGED
            if change.change_type == ChangeType.NEW.value:
                event_type = RegulatoryEventType.NEW_CLAIM_APPROVED
            elif change.change_type == ChangeType.REMOVED.value:
                event_type = RegulatoryEventType.CLAIM_REMOVED

            await self._event_emitter.emit(RegulatoryEvent(
                event_type=event_type,
                claim_id=change.claim_id,
                substance=change.new_value or change.old_value or "",
                old_status=change.old_value or "",
                new_status=change.new_value or "",
                severity=change.severity,
                data={
                    "change_type": change.change_type,
                    "field_changed": change.field_changed,
                },
            ))

        if critical_changes:
            logger.info("Stage 8: Published %d events", len(critical_changes))

        result.status = MonitorStatus.COMPLETE
        logger.info(
            "Pipeline complete: %d claims, %d relevant, %d changes",
            result.claim_count,
            result.relevant_count,
            result.changes_detected,
        )
        return result


__all__ = [
    "HealthClaimsMonitorPipeline",
]
