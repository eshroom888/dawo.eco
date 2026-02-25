"""Tests for HealthClaimsRepository.

Story 6-1, Task 12.16-12.18: Repository tests.

Note: These are unit tests using mocked AsyncSession.
Integration tests with real DB are in tests/integration/.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd

from core.regulatory.models import HealthClaim, ClaimSnapshot, ClaimChange
from teams.dawo.scanners.health_claims.repository import HealthClaimsRepository
from teams.dawo.scanners.health_claims.schemas import ClaimChangeRecord


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session):
    return HealthClaimsRepository(session=mock_session)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "claim_id": ["ID-001", "ID-002"],
        "substance": ["Beta-glucans", "Vitamin C"],
        "status": ["Authorised", "Authorised"],
        "is_relevant": [True, False],
        "relevance_category": ["mushroom", None],
        "claim_type": [None, None],
        "health_relationship": [None, None],
        "claim_text": [None, None],
        "conditions_of_use": [None, None],
        "food_category": [None, None],
        "efsa_opinion": [None, None],
        "commission_regulation": [None, None],
        "date_of_entry": [None, None],
        "last_update": [None, None],
        "restrictions": [None, None],
    })


class TestSaveSnapshot:
    """Test 12.16: save_snapshot creates snapshot + claims."""

    @pytest.mark.asyncio
    async def test_saves_snapshot(self, repository, mock_session, sample_df):
        await repository.save_snapshot(
            claims_df=sample_df,
            source_url="https://example.com/data.xls",
            file_size_bytes=1024,
        )
        # Snapshot was added to session
        mock_session.add.assert_called_once()
        snapshot = mock_session.add.call_args[0][0]
        assert isinstance(snapshot, ClaimSnapshot)
        assert snapshot.claim_count == 2
        assert snapshot.relevant_claim_count == 1
        assert snapshot.source_url == "https://example.com/data.xls"

    @pytest.mark.asyncio
    async def test_saves_claims_batch(self, repository, mock_session, sample_df):
        await repository.save_snapshot(
            claims_df=sample_df,
            source_url="https://example.com/data.xls",
            file_size_bytes=1024,
        )
        # Flush called (for snapshot ID + after claims insert)
        assert mock_session.flush.call_count == 2
        # Execute called for batch insert
        mock_session.execute.assert_called_once()
        # No commit — caller owns the transaction boundary
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_snapshot_hash_computed(self, repository, mock_session, sample_df):
        await repository.save_snapshot(
            claims_df=sample_df,
            source_url="https://example.com/data.xls",
            file_size_bytes=1024,
        )
        snapshot = mock_session.add.call_args[0][0]
        assert len(snapshot.snapshot_hash) == 64  # SHA-256 hex digest


class TestGetLatestSnapshot:
    """Test 12.17: get_latest_snapshot returns most recent."""

    @pytest.mark.asyncio
    async def test_returns_snapshot(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ClaimSnapshot(
            snapshot_hash="abc123" * 10 + "abcd",
            claim_count=100,
            relevant_claim_count=5,
            source_url="https://example.com",
            downloaded_at=datetime.now(UTC),
        )
        mock_session.execute.return_value = mock_result

        snapshot = await repository.get_latest_snapshot()
        assert snapshot is not None
        assert snapshot.claim_count == 100

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        snapshot = await repository.get_latest_snapshot()
        assert snapshot is None


class TestSaveChanges:
    """Test 12.18: save_changes persists change records."""

    @pytest.mark.asyncio
    async def test_saves_changes(self, repository, mock_session):
        snapshot_id = uuid4()
        changes = [
            ClaimChangeRecord(
                claim_id="ID-001",
                change_type="new",
                new_value="Beta-glucans",
                is_relevant=True,
                severity="high",
            ),
            ClaimChangeRecord(
                claim_id="ID-002",
                change_type="removed",
                old_value="Vitamin C",
                is_relevant=False,
                severity="low",
            ),
        ]

        result = await repository.save_changes(changes, snapshot_id)
        assert result == 2
        # Execute called once for batch insert
        mock_session.execute.assert_called_once()
        # No commit — caller owns the transaction boundary
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_changes_no_db_call(self, repository, mock_session):
        result = await repository.save_changes([], uuid4())
        assert result == 0
        mock_session.execute.assert_not_called()
