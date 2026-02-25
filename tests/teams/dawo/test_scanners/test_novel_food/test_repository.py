"""Tests for NovelFoodRepository.

Story 6-2, Task 7: Create Novel Food repository.
Uses mocked AsyncSession to test repository logic without database.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from teams.dawo.scanners.novel_food.repository import NovelFoodRepository
from teams.dawo.scanners.novel_food.schemas import (
    NovelFoodEntryRecord,
    CatalogueChangeRecord,
)


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session):
    return NovelFoodRepository(session=mock_session)


class TestSaveSnapshot:
    """Test 11.19: save_snapshot creates snapshot + entries."""

    @pytest.mark.asyncio
    async def test_save_snapshot_returns_snapshot(self, repository, sample_entry_records):
        result = await repository.save_snapshot(
            entries=sample_entry_records,
            species_queried=2,
            search_duration=15.5,
        )
        assert result is not None
        assert result.total_entries == 2
        assert result.species_queried == 2
        assert result.search_duration_seconds == 15.5

    @pytest.mark.asyncio
    async def test_save_snapshot_computes_hash(self, repository, sample_entry_records):
        result = await repository.save_snapshot(
            entries=sample_entry_records,
            species_queried=2,
            search_duration=10.0,
        )
        assert result.snapshot_hash != ""
        assert len(result.snapshot_hash) == 64  # SHA-256

    @pytest.mark.asyncio
    async def test_save_snapshot_calls_flush(self, repository, mock_session, sample_entry_records):
        await repository.save_snapshot(
            entries=sample_entry_records,
            species_queried=1,
            search_duration=5.0,
        )
        mock_session.flush.assert_called()


class TestGetLatestSnapshot:
    """Test 11.20: get_latest_snapshot returns most recent."""

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_when_empty(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_snapshot()
        assert result is None


class TestSaveChanges:
    """Test 11.21: save_changes persists change records."""

    @pytest.mark.asyncio
    async def test_save_changes_returns_count(self, repository):
        changes = [
            CatalogueChangeRecord(
                species_latin="Hericium erinaceus",
                entry_name="Test",
                change_type="new",
                severity="high",
            ),
            CatalogueChangeRecord(
                species_latin="Inonotus obliquus",
                entry_name="Chaga",
                change_type="status_changed",
                field_changed="novel_food_status",
                old_value="novel",
                new_value="not_novel",
                severity="critical",
            ),
        ]
        count = await repository.save_changes(changes, uuid4())
        assert count == 2

    @pytest.mark.asyncio
    async def test_save_changes_empty_list(self, repository):
        count = await repository.save_changes([], uuid4())
        assert count == 0


class TestGetEntriesBySpecies:
    """Test 11.22: get_entries_by_species filters correctly."""

    @pytest.mark.asyncio
    async def test_returns_results(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repository.get_entries_by_species(uuid4(), "Hericium erinaceus")
        assert isinstance(result, list)


class TestCommit:
    """Test repository commit."""

    @pytest.mark.asyncio
    async def test_commit_calls_session_commit(self, repository, mock_session):
        await repository.commit()
        mock_session.commit.assert_called_once()
