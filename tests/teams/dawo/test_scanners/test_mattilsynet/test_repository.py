"""Tests for Mattilsynet repository.

Epic 6, Story 6-3: Tasks 13.23-13.28.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.regulatory.models import (
    MattilsynetSnapshot,
    MattilsynetPageHash,
    MattilsynetUpdate,
)
from teams.dawo.scanners.mattilsynet.repository import MattilsynetRepository
from teams.dawo.scanners.mattilsynet.schemas import RegulatoryUpdateRecord


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session) -> MattilsynetRepository:
    return MattilsynetRepository(mock_session)


class TestSaveSnapshot:
    """Test save_snapshot method."""

    @pytest.mark.asyncio
    async def test_creates_snapshot(self, repo, mock_session) -> None:
        snapshot = await repo.save_snapshot(
            total_updates=10,
            relevant_updates=3,
            feeds_checked=2,
            pages_checked=4,
            scan_duration=45.5,
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert isinstance(snapshot, MattilsynetSnapshot)
        assert snapshot.total_updates == 10
        assert snapshot.relevant_updates == 3

    @pytest.mark.asyncio
    async def test_snapshot_has_hash(self, repo) -> None:
        snapshot = await repo.save_snapshot(5, 2, 1, 3, 30.0)
        assert len(snapshot.snapshot_hash) == 64


class TestGetLatestSnapshot:
    """Test get_latest_snapshot method."""

    @pytest.mark.asyncio
    async def test_returns_snapshot(self, repo, mock_session) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(spec=MattilsynetSnapshot)
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_snapshot()
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, repo, mock_session) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_latest_snapshot()
        assert result is None


class TestSaveUpdates:
    """Test save_updates method."""

    @pytest.mark.asyncio
    async def test_persists_updates(self, repo, mock_session) -> None:
        updates = [
            RegulatoryUpdateRecord(
                title="Test Update",
                url="https://example.com/update",
                source_type="rss_news",
                severity="high",
                is_relevant=True,
            )
        ]
        count = await repo.save_updates(updates, uuid4())
        assert count == 1
        mock_session.execute.assert_awaited_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty(self, repo) -> None:
        count = await repo.save_updates([], uuid4())
        assert count == 0


class TestGetKnownUrls:
    """Test get_known_urls method."""

    @pytest.mark.asyncio
    async def test_returns_url_set(self, repo, mock_session) -> None:
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("https://example.com/1",),
            ("https://example.com/2",),
        ]
        mock_session.execute.return_value = mock_result

        urls = await repo.get_known_urls(datetime.now(UTC))
        assert len(urls) == 2
        assert "https://example.com/1" in urls


class TestPageHashOperations:
    """Test page hash CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_page_hash(self, repo, mock_session) -> None:
        page_hash = await repo.save_page_hash(
            url="https://example.com",
            page_name="Test",
            content_hash="abc123",
        )
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert isinstance(page_hash, MattilsynetPageHash)

    @pytest.mark.asyncio
    async def test_update_page_hash_changed(self, repo, mock_session) -> None:
        existing = MagicMock(spec=MattilsynetPageHash)
        existing.content_hash = "old_hash"
        existing.last_checked = None
        existing.last_changed = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        await repo.update_page_hash("https://example.com", "new_hash", changed=True)
        assert existing.content_hash == "new_hash"
        assert existing.last_changed is not None

    @pytest.mark.asyncio
    async def test_update_page_hash_not_changed(self, repo, mock_session) -> None:
        existing = MagicMock(spec=MattilsynetPageHash)
        existing.content_hash = "same"
        existing.last_checked = None
        existing.last_changed = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        await repo.update_page_hash("https://example.com", "same", changed=False)
        # last_changed should NOT be updated
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_page_hash(self, repo, mock_session) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(spec=MattilsynetPageHash)
        mock_session.execute.return_value = mock_result

        result = await repo.get_page_hash("https://example.com")
        assert result is not None


class TestCommit:
    """Test commit method."""

    @pytest.mark.asyncio
    async def test_commits_session(self, repo, mock_session) -> None:
        await repo.commit()
        mock_session.commit.assert_awaited_once()
