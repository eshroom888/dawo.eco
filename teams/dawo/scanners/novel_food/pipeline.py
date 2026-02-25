"""Novel Food Catalogue Monitor pipeline.

Epic 6, Story 6-2, Task 8: Monitor pipeline.

Orchestrates the full monitoring flow:
    fetch → parse → load previous → detect changes → save → commit → emit events.
"""

import logging
import time
from typing import Sequence

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventEmitter,
    RegulatoryEventType,
)
from core.regulatory.models import NovelFoodEntry
from teams.dawo.scanners.novel_food.client import NovelFoodCatalogueClient
from teams.dawo.scanners.novel_food.change_detector import NovelFoodChangeDetector
from teams.dawo.scanners.novel_food.config import NovelFoodMonitorConfig
from teams.dawo.scanners.novel_food.parser import CatalogueParser, CatalogueParseError
from teams.dawo.scanners.novel_food.repository import NovelFoodRepository
from teams.dawo.scanners.novel_food.schemas import (
    CatalogueChangeRecord,
    MonitorResult,
    MonitorStatus,
    NovelFoodEntryRecord,
)

logger = logging.getLogger(__name__)

# Map change_type to event type
_CHANGE_EVENT_MAP = {
    "new": RegulatoryEventType.NOVEL_FOOD_NEW_ENTRY,
    "removed": RegulatoryEventType.NOVEL_FOOD_ENTRY_REMOVED,
    "status_changed": RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED,
    "modified": RegulatoryEventType.NOVEL_FOOD_CATALOGUE_UPDATED,
}


class NovelFoodMonitorPipeline:
    """Pipeline for monitoring the EU Novel Food Catalogue.

    Story 6-2, Task 8: Orchestrates fetch → parse → detect → save → events.

    Accepts all dependencies via constructor (DI).

    Pipeline stages:
        1. Fetch all species from catalogue (client)
        2. Parse responses to entry records (parser)
        3. Load previous snapshot from DB (repository)
        4. Detect changes vs previous (change_detector) — skipped on first run
        5. Save new snapshot + entries (repository)
        6. Save change records (repository)
        7. Commit transaction (repository)
        8. Publish events for high-severity changes (event_emitter)
    """

    def __init__(
        self,
        client: NovelFoodCatalogueClient,
        parser: CatalogueParser,
        change_detector: NovelFoodChangeDetector,
        repository: NovelFoodRepository,
        event_emitter: RegulatoryEventEmitter,
        config: NovelFoodMonitorConfig,
    ) -> None:
        self._client = client
        self._parser = parser
        self._change_detector = change_detector
        self._repository = repository
        self._event_emitter = event_emitter
        self._config = config

    async def execute(self) -> MonitorResult:
        """Execute the full monitoring pipeline.

        Returns:
            MonitorResult with execution summary and statistics
        """
        result = MonitorResult()
        start_time = time.monotonic()

        # Stage 1: Fetch all species
        species_list = list(self._config.species)
        fetched = await self._client.fetch_all_species(species_list)

        if not fetched:
            result.status = MonitorStatus.INCOMPLETE
            result.errors.append("All species fetches failed")
            return result

        has_fetch_failures = len(fetched) < len(species_list)

        # Stage 2: Parse each species response
        all_entries: list[NovelFoodEntryRecord] = []
        parse_errors: list[str] = []

        for species_latin, data in fetched.items():
            try:
                entries = self._parser.parse_response(data, species_latin)
                all_entries.extend(entries)
            except CatalogueParseError as e:
                parse_errors.append(f"Parse failed for {species_latin}: {e}")
                logger.warning("Parse failed for '%s': %s", species_latin, e)

        if not all_entries and parse_errors:
            result.status = MonitorStatus.INCOMPLETE
            result.errors.extend(parse_errors)
            return result

        if parse_errors:
            result.errors.extend(parse_errors)

        # Stage 3: Load previous snapshot
        previous_snapshot = await self._repository.get_latest_snapshot()

        # Stage 4: Change detection (skip on first run)
        changes: list[CatalogueChangeRecord] = []
        if previous_snapshot is not None:
            previous_db_entries = await self._repository.get_entries_by_snapshot(
                previous_snapshot.id
            )
            previous_records = _db_entries_to_records(previous_db_entries)
            changes = self._change_detector.detect(previous_records, all_entries)

        # Stage 5: Save new snapshot
        duration = time.monotonic() - start_time
        snapshot = await self._repository.save_snapshot(
            entries=all_entries,
            species_queried=len(species_list),
            search_duration=duration,
        )

        # Stage 6: Save changes
        if changes:
            await self._repository.save_changes(changes, snapshot.id)

        # Stage 7: Commit
        await self._repository.commit()

        # Stage 8: Emit events for high-severity changes
        for change in changes:
            if change.severity in ("critical", "high"):
                event_type = _CHANGE_EVENT_MAP.get(
                    change.change_type,
                    RegulatoryEventType.NOVEL_FOOD_STATUS_CHANGED,
                )
                await self._event_emitter.emit(RegulatoryEvent(
                    event_type=event_type,
                    claim_id=f"{change.species_latin}:{change.entry_name}",
                    substance=change.species_latin,
                    old_status=change.old_value or "",
                    new_status=change.new_value or "",
                    severity=change.severity,
                    data={
                        "change_type": change.change_type,
                        "field_changed": change.field_changed,
                        "entry_name": change.entry_name,
                    },
                ))

        # Determine final status
        if has_fetch_failures or parse_errors:
            result.status = MonitorStatus.PARTIAL
        else:
            result.status = MonitorStatus.COMPLETE

        result.claim_count = len(all_entries)  # total entries found
        result.changes_detected = len(changes)
        logger.info(
            "Pipeline complete: %d entries, %d changes, status=%s",
            len(all_entries),
            len(changes),
            result.status.value,
        )
        return result


def _db_entries_to_records(
    db_entries: Sequence[NovelFoodEntry],
) -> list[NovelFoodEntryRecord]:
    """Convert SQLAlchemy NovelFoodEntry models to DTOs.

    Args:
        db_entries: Database entry records

    Returns:
        List of NovelFoodEntryRecord DTOs
    """
    return [
        NovelFoodEntryRecord(
            species_latin=e.species_latin,
            species_common=e.species_common or "",
            entry_name=e.entry_name,
            novel_food_status=e.novel_food_status,
            authorization_status=e.authorization_status or "",
            history_of_consumption=e.history_of_consumption or "",
            member_state_comments=e.member_state_comments or "",
            commission_comments=e.commission_comments or "",
            conditions_of_use=e.conditions_of_use or "",
            regulation_reference=e.regulation_reference or "",
            union_list_entry=e.union_list_entry or "",
            source_url=e.source_url or "",
            raw_html_hash=e.raw_html_hash or "",
        )
        for e in db_entries
    ]


__all__ = [
    "NovelFoodMonitorPipeline",
]
