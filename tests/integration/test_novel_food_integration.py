"""Integration tests for EU Novel Food Catalogue Monitor.

Story 6-2, Task 12: Integration tests.

Tests the full pipeline flow with real component interactions
(mocked HTTP only, real parsing/change detection).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.regulatory.events import RegulatoryEventEmitter
from teams.dawo.scanners.novel_food.config import SpeciesConfig, NovelFoodMonitorConfig
from teams.dawo.scanners.novel_food.parser import CatalogueParser
from teams.dawo.scanners.novel_food.change_detector import NovelFoodChangeDetector
from teams.dawo.scanners.novel_food.repository import NovelFoodRepository
from teams.dawo.scanners.novel_food.pipeline import NovelFoodMonitorPipeline
from teams.dawo.scanners.novel_food.schemas import MonitorStatus


# Shared test data
SPECIES = (
    SpeciesConfig(
        latin_name="Hericium erinaceus",
        common_names=("Lion's Mane",),
        is_dawo_product=True,
    ),
    SpeciesConfig(
        latin_name="Inonotus obliquus",
        common_names=("Chaga",),
        is_dawo_product=True,
    ),
)

CONFIG = NovelFoodMonitorConfig(
    search_url="https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search",
    portal_url="https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search",
    species=SPECIES,
    request_delay_seconds=0,  # No delay in tests
)

HERICIUM_JSON = json.dumps([
    {
        "name": "Hericium erinaceus (Lion's Mane) - fruiting body",
        "novelFoodStatus": "Yes",
        "authorisationStatus": None,
        "historyOfConsumption": "No history of significant consumption",
        "memberStateComments": "DE: Novel food",
        "commissionComments": "Classified as novel food",
        "conditionsOfUse": None,
        "regulationReference": None,
        "unionListEntry": "No",
    },
    {
        "name": "Hericium erinaceus - extract",
        "novelFoodStatus": "Yes",
        "authorisationStatus": None,
        "historyOfConsumption": "No history",
        "memberStateComments": "FR: Novel food",
        "commissionComments": None,
        "conditionsOfUse": None,
        "regulationReference": None,
        "unionListEntry": "No",
    },
]).encode("utf-8")

CHAGA_JSON = json.dumps([
    {
        "name": "Inonotus obliquus (Chaga) - fruiting body",
        "novelFoodStatus": "Yes",
        "authorisationStatus": None,
        "historyOfConsumption": "Limited consumption history",
        "memberStateComments": "FI: Novel food",
        "commissionComments": None,
        "conditionsOfUse": None,
        "regulationReference": None,
        "unionListEntry": "No",
    },
]).encode("utf-8")

# Modified data: Lion's Mane status changed, Chaga unchanged
HERICIUM_JSON_MODIFIED = json.dumps([
    {
        "name": "Hericium erinaceus (Lion's Mane) - fruiting body",
        "novelFoodStatus": "No",  # CHANGED: novel → not_novel
        "authorisationStatus": None,
        "historyOfConsumption": "Sufficient evidence of consumption before May 1997",
        "memberStateComments": "DE: Not novel food (reclassified 2026)",
        "commissionComments": "Reclassified based on new evidence",
        "conditionsOfUse": None,
        "regulationReference": "EU 2026/xxx",
        "unionListEntry": "No",
    },
    {
        "name": "Hericium erinaceus - extract",
        "novelFoodStatus": "Yes",  # UNCHANGED
        "authorisationStatus": None,
        "historyOfConsumption": "No history",
        "memberStateComments": "FR: Novel food",
        "commissionComments": None,
        "conditionsOfUse": None,
        "regulationReference": None,
        "unionListEntry": "No",
    },
    {
        "name": "Hericium erinaceus - mycelium",  # NEW entry
        "novelFoodStatus": "Yes",
        "authorisationStatus": None,
        "historyOfConsumption": "No history of consumption",
        "memberStateComments": None,
        "commissionComments": None,
        "conditionsOfUse": None,
        "regulationReference": None,
        "unionListEntry": "No",
    },
]).encode("utf-8")


@pytest.fixture
def parser():
    return CatalogueParser()


@pytest.fixture
def change_detector():
    return NovelFoodChangeDetector(species_config=SPECIES)


@pytest.fixture
def mock_repository():
    repo = AsyncMock(spec=NovelFoodRepository)
    repo.get_latest_snapshot.return_value = None
    mock_snapshot = MagicMock()
    mock_snapshot.id = uuid4()
    repo.save_snapshot.return_value = mock_snapshot
    repo.save_changes.return_value = 0
    repo.get_entries_by_snapshot.return_value = []
    return repo


@pytest.fixture
def mock_event_emitter():
    return AsyncMock(spec=RegulatoryEventEmitter)


class TestFullPipelineIntegration:
    """Test 12.1: Full pipeline — mock fetch → real parse → real detect → mock save → events."""

    @pytest.mark.asyncio
    async def test_first_run_parses_and_saves(
        self, parser, change_detector, mock_repository, mock_event_emitter
    ):
        """First run: fetch → parse → no change detection → save snapshot."""
        mock_client = AsyncMock()
        mock_client.fetch_all_species.return_value = {
            "Hericium erinaceus": HERICIUM_JSON,
            "Inonotus obliquus": CHAGA_JSON,
        }

        pipeline = NovelFoodMonitorPipeline(
            client=mock_client,
            parser=parser,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=CONFIG,
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.COMPLETE
        assert result.changes_detected == 0  # First run

        # Snapshot saved with 3 entries (2 Hericium + 1 Chaga)
        mock_repository.save_snapshot.assert_called_once()
        call_args = mock_repository.save_snapshot.call_args
        entries = call_args.kwargs.get("entries", call_args.args[0] if call_args.args else [])
        assert len(entries) == 3

        mock_repository.commit.assert_called_once()
        # No events on first run
        mock_event_emitter.emit.assert_not_called()


class TestChangeDetectionAcrossRuns:
    """Test 12.2: Change detection across two sequential runs."""

    @pytest.mark.asyncio
    async def test_detects_changes_between_runs(self, parser, change_detector):
        """Parse both runs and detect changes using real components."""
        # First run entries
        first_entries = (
            parser.parse_response(HERICIUM_JSON, "Hericium erinaceus")
            + parser.parse_response(CHAGA_JSON, "Inonotus obliquus")
        )
        assert len(first_entries) == 3

        # Second run entries (Hericium modified)
        second_entries = (
            parser.parse_response(HERICIUM_JSON_MODIFIED, "Hericium erinaceus")
            + parser.parse_response(CHAGA_JSON, "Inonotus obliquus")
        )
        assert len(second_entries) == 4  # 3 Hericium + 1 Chaga

        # Detect changes
        changes = change_detector.detect(first_entries, second_entries)

        # Should detect: status_changed (fruiting body), new_entry (mycelium),
        # plus field modifications
        assert len(changes) >= 2

        change_types = {c.change_type for c in changes}
        assert "status_changed" in change_types or "modified" in change_types
        assert "new" in change_types

        # Find the status change for fruiting body
        status_changes = [
            c for c in changes
            if c.entry_name == "Hericium erinaceus (Lion's Mane) - fruiting body"
            and c.change_type == "status_changed"
        ]
        assert len(status_changes) == 1
        assert status_changes[0].old_value == "novel"
        assert status_changes[0].new_value == "not_novel"


class TestStatusChangeEndToEnd:
    """Test 12.3: Status change detection end-to-end (novel → not_novel)."""

    @pytest.mark.asyncio
    async def test_novel_to_not_novel_full_pipeline(
        self, parser, change_detector, mock_repository, mock_event_emitter
    ):
        """Full pipeline: second run detects novel → not_novel status change."""
        # Set up previous snapshot
        prev_snapshot = MagicMock()
        prev_snapshot.id = uuid4()
        mock_repository.get_latest_snapshot.return_value = prev_snapshot

        # Reconstruct previous entries as DB-like objects
        first_entries = (
            parser.parse_response(HERICIUM_JSON, "Hericium erinaceus")
            + parser.parse_response(CHAGA_JSON, "Inonotus obliquus")
        )
        mock_db_entries = []
        for e in first_entries:
            db_entry = MagicMock()
            db_entry.species_latin = e.species_latin
            db_entry.species_common = e.species_common
            db_entry.entry_name = e.entry_name
            db_entry.novel_food_status = e.novel_food_status
            db_entry.authorization_status = e.authorization_status
            db_entry.history_of_consumption = e.history_of_consumption
            db_entry.member_state_comments = e.member_state_comments
            db_entry.commission_comments = e.commission_comments
            db_entry.conditions_of_use = e.conditions_of_use
            db_entry.regulation_reference = e.regulation_reference
            db_entry.union_list_entry = e.union_list_entry
            db_entry.source_url = e.source_url
            db_entry.raw_html_hash = e.raw_html_hash
            mock_db_entries.append(db_entry)
        mock_repository.get_entries_by_snapshot.return_value = mock_db_entries

        # Second run: modified data
        mock_client = AsyncMock()
        mock_client.fetch_all_species.return_value = {
            "Hericium erinaceus": HERICIUM_JSON_MODIFIED,
            "Inonotus obliquus": CHAGA_JSON,
        }

        new_snapshot = MagicMock()
        new_snapshot.id = uuid4()
        mock_repository.save_snapshot.return_value = new_snapshot

        pipeline = NovelFoodMonitorPipeline(
            client=mock_client,
            parser=parser,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=CONFIG,
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.COMPLETE
        assert result.changes_detected > 0
        mock_repository.save_changes.assert_called_once()


class TestCriticalEventEmission:
    """Test 12.4: Event emission for CRITICAL status change on DAWO product."""

    @pytest.mark.asyncio
    async def test_critical_change_emits_event(
        self, parser, change_detector, mock_repository, mock_event_emitter
    ):
        """DAWO product status change should emit event."""
        # Previous snapshot with first run data
        prev_snapshot = MagicMock()
        prev_snapshot.id = uuid4()
        mock_repository.get_latest_snapshot.return_value = prev_snapshot

        first_entries = (
            parser.parse_response(HERICIUM_JSON, "Hericium erinaceus")
            + parser.parse_response(CHAGA_JSON, "Inonotus obliquus")
        )
        mock_db_entries = []
        for e in first_entries:
            db_entry = MagicMock()
            for attr in (
                "species_latin", "species_common", "entry_name",
                "novel_food_status", "authorization_status",
                "history_of_consumption", "member_state_comments",
                "commission_comments", "conditions_of_use",
                "regulation_reference", "union_list_entry",
                "source_url", "raw_html_hash",
            ):
                setattr(db_entry, attr, getattr(e, attr))
            mock_db_entries.append(db_entry)
        mock_repository.get_entries_by_snapshot.return_value = mock_db_entries

        mock_client = AsyncMock()
        mock_client.fetch_all_species.return_value = {
            "Hericium erinaceus": HERICIUM_JSON_MODIFIED,
            "Inonotus obliquus": CHAGA_JSON,
        }

        new_snapshot = MagicMock()
        new_snapshot.id = uuid4()
        mock_repository.save_snapshot.return_value = new_snapshot

        received_events = []
        mock_event_emitter.emit.side_effect = lambda e: received_events.append(e)

        pipeline = NovelFoodMonitorPipeline(
            client=mock_client,
            parser=parser,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=CONFIG,
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.COMPLETE
        assert result.changes_detected > 0
        # Should emit events for critical/high severity changes
        assert mock_event_emitter.emit.call_count >= 1

        # Check that at least one event is for the Hericium status change
        hericium_events = [
            e for e in received_events
            if "Hericium erinaceus" in str(getattr(e, "substance", ""))
            or "Hericium erinaceus" in str(getattr(e, "claim_id", ""))
        ]
        assert len(hericium_events) >= 1


class TestGracefulDegradation:
    """Test 12.5: Graceful degradation on fetch failure."""

    @pytest.mark.asyncio
    async def test_fetch_failure_returns_incomplete(
        self, parser, change_detector, mock_repository, mock_event_emitter
    ):
        """All species fail to fetch → INCOMPLETE, no snapshot saved."""
        mock_client = AsyncMock()
        mock_client.fetch_all_species.return_value = {}  # All failed

        pipeline = NovelFoodMonitorPipeline(
            client=mock_client,
            parser=parser,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=CONFIG,
        )

        result = await pipeline.execute()

        assert result.status == MonitorStatus.INCOMPLETE
        assert len(result.errors) > 0
        # Repository save should NOT have been called
        mock_repository.save_snapshot.assert_not_called()
        mock_repository.commit.assert_not_called()
        mock_event_emitter.emit.assert_not_called()
