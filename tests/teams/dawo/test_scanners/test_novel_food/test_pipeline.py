"""Tests for NovelFoodMonitorPipeline.

Story 6-2, Task 8: Create monitor pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from teams.dawo.scanners.novel_food.pipeline import NovelFoodMonitorPipeline
from teams.dawo.scanners.novel_food.schemas import (
    NovelFoodEntryRecord,
    CatalogueChangeRecord,
    MonitorStatus,
)
from teams.dawo.scanners.novel_food.client import NovelFoodClientError
from teams.dawo.scanners.novel_food.parser import CatalogueParseError


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.fetch_all_species = AsyncMock(return_value={
        "Hericium erinaceus": b'[{"name": "test"}]',
        "Inonotus obliquus": b'[{"name": "test2"}]',
    })
    return client


@pytest.fixture
def mock_parser():
    parser = MagicMock()
    parser.parse_response.return_value = [
        NovelFoodEntryRecord(
            species_latin="Hericium erinaceus",
            entry_name="Test entry",
            novel_food_status="novel",
        ),
    ]
    return parser


@pytest.fixture
def mock_change_detector():
    detector = MagicMock()
    detector.detect.return_value = []
    return detector


@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    repo.get_latest_snapshot.return_value = None
    repo.save_snapshot.return_value = MagicMock(id=uuid4())
    repo.save_changes.return_value = 0
    repo.get_entries_by_snapshot.return_value = []
    return repo


@pytest.fixture
def pipeline(
    mock_client,
    mock_parser,
    mock_change_detector,
    mock_repository,
    mock_event_emitter,
    novel_food_config,
):
    return NovelFoodMonitorPipeline(
        client=mock_client,
        parser=mock_parser,
        change_detector=mock_change_detector,
        repository=mock_repository,
        event_emitter=mock_event_emitter,
        config=novel_food_config,
    )


class TestPipelineHappyPath:
    """Test 11.23: full happy path."""

    @pytest.mark.asyncio
    async def test_execute_returns_complete(self, pipeline):
        result = await pipeline.execute()
        assert result.status == MonitorStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_execute_saves_snapshot(self, pipeline, mock_repository):
        await pipeline.execute()
        mock_repository.save_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_commits(self, pipeline, mock_repository):
        await pipeline.execute()
        mock_repository.commit.assert_called_once()


class TestPipelineFirstRun:
    """Test 11.24: first run (no previous snapshot)."""

    @pytest.mark.asyncio
    async def test_first_run_no_change_detection(
        self, pipeline, mock_repository, mock_change_detector
    ):
        mock_repository.get_latest_snapshot.return_value = None
        await pipeline.execute()
        # Change detector should not be called on first run
        mock_change_detector.detect.assert_not_called()


class TestPipelineFetchFailure:
    """Test 11.25: fetch failure -> INCOMPLETE."""

    @pytest.mark.asyncio
    async def test_fetch_failure_returns_incomplete(
        self, mock_parser, mock_change_detector, mock_repository,
        mock_event_emitter, novel_food_config,
    ):
        client = AsyncMock()
        client.fetch_all_species = AsyncMock(return_value={})  # All species failed

        pipeline = NovelFoodMonitorPipeline(
            client=client,
            parser=mock_parser,
            change_detector=mock_change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=novel_food_config,
        )
        result = await pipeline.execute()
        assert result.status == MonitorStatus.INCOMPLETE


class TestPipelineParseFailure:
    """Test 11.26: parse failure -> INCOMPLETE."""

    @pytest.mark.asyncio
    async def test_parse_failure_returns_incomplete(
        self, mock_client, mock_change_detector, mock_repository,
        mock_event_emitter, novel_food_config,
    ):
        parser = MagicMock()
        parser.parse_response.side_effect = CatalogueParseError("bad format")

        pipeline = NovelFoodMonitorPipeline(
            client=mock_client,
            parser=parser,
            change_detector=mock_change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=novel_food_config,
        )
        result = await pipeline.execute()
        assert result.status in (MonitorStatus.INCOMPLETE, MonitorStatus.PARTIAL)
        assert len(result.errors) > 0


class TestPipelinePartialFailure:
    """Test 11.27: partial failure (some species fail) -> PARTIAL."""

    @pytest.mark.asyncio
    async def test_partial_failure(
        self, mock_parser, mock_change_detector, mock_repository,
        mock_event_emitter, novel_food_config,
    ):
        # One species succeeds, one returns nothing (failed in client)
        client = AsyncMock()
        client.fetch_all_species = AsyncMock(return_value={
            "Hericium erinaceus": b'[{"name": "test"}]',
            # Inonotus obliquus missing — failed
        })

        pipeline = NovelFoodMonitorPipeline(
            client=client,
            parser=mock_parser,
            change_detector=mock_change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=novel_food_config,
        )
        result = await pipeline.execute()
        # With 2 species configured but only 1 returned, it should be PARTIAL
        assert result.status == MonitorStatus.PARTIAL


class TestPipelineEventEmission:
    """Test 11.28: publishes events for CRITICAL changes."""

    @pytest.mark.asyncio
    async def test_emits_event_for_critical_change(
        self, mock_client, mock_parser, mock_repository,
        mock_event_emitter, novel_food_config,
    ):
        # Set up previous snapshot to enable change detection
        prev_snapshot = MagicMock(id=uuid4())
        mock_repository.get_latest_snapshot.return_value = prev_snapshot
        mock_repository.get_entries_by_snapshot.return_value = []

        change_detector = MagicMock()
        change_detector.detect.return_value = [
            CatalogueChangeRecord(
                species_latin="Hericium erinaceus",
                entry_name="Test entry",
                change_type="status_changed",
                field_changed="novel_food_status",
                old_value="novel",
                new_value="not_novel",
                severity="critical",
            ),
        ]
        mock_repository.save_changes.return_value = 1

        pipeline = NovelFoodMonitorPipeline(
            client=mock_client,
            parser=mock_parser,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=novel_food_config,
        )
        await pipeline.execute()
        mock_event_emitter.emit.assert_called()
