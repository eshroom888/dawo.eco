"""Tests for CompetitorRepository.

Epic 6, Story 6-5, Task 7: Database persistence for competitor content.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from teams.dawo.scanners.competitor.repository import CompetitorRepository
from teams.dawo.scanners.competitor.schemas import ParsedContent


@pytest.fixture
def repo(mock_session):
    return CompetitorRepository(session=mock_session)


@pytest.fixture
def snapshot_id():
    return uuid4()


def _make_content(hash_val: str = "abc123") -> ParsedContent:
    return ParsedContent(
        source_type="instagram",
        competitor_name="CompA",
        source_url=f"https://instagram.com/p/{hash_val}",
        content_text=f"Content {hash_val}",
        hashtags=["#test"],
        account_or_domain="comp_a",
        published_at=datetime(2026, 2, 10, tzinfo=UTC),
        content_hash=hash_val,
        has_health_language=True,
        health_keywords_matched=["boost"],
    )


class TestCreateSnapshot:
    """Tests for create_snapshot()."""

    @pytest.mark.asyncio
    async def test_creates_record_with_in_progress_status(self, repo, mock_session):
        snapshot = await repo.create_snapshot("CompA", "instagram")
        assert snapshot.competitor_name == "CompA"
        assert snapshot.source_type == "instagram"
        assert snapshot.status == "in_progress"
        mock_session.add.assert_called_once()


class TestSaveContentBatch:
    """Tests for save_content_batch()."""

    @pytest.mark.asyncio
    async def test_saves_all_items_returns_count(self, repo, mock_session, snapshot_id):
        items = [_make_content("hash_a"), _make_content("hash_b")]
        count = await repo.save_content_batch(items, snapshot_id)
        assert count == 2
        mock_session.add_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_batch_returns_zero(self, repo, mock_session, snapshot_id):
        count = await repo.save_content_batch([], snapshot_id)
        assert count == 0


class TestUpdateSnapshotStats:
    """Tests for update_snapshot_stats()."""

    @pytest.mark.asyncio
    async def test_updates_total_and_status(self, repo, mock_session, snapshot_id):
        mock_snapshot = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_snapshot
        mock_session.execute = AsyncMock(return_value=mock_result)

        await repo.update_snapshot_stats(snapshot_id, total=10, health_count=3, status="completed")

        assert mock_snapshot.total_items_found == 10
        assert mock_snapshot.items_with_health_language == 3
        assert mock_snapshot.status == "completed"


class TestGetPendingExtraction:
    """Tests for get_pending_extraction()."""

    @pytest.mark.asyncio
    async def test_returns_only_pending_items(self, repo, mock_session):
        mock_items = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_items
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_pending_extraction()
        assert len(result) == 2


class TestCommit:
    """Tests for commit()."""

    @pytest.mark.asyncio
    async def test_calls_session_commit(self, repo, mock_session):
        await repo.commit()
        mock_session.commit.assert_awaited_once()
