"""Tests for CompetitorDuplicateChecker.

Epic 6, Story 6-5, Task 6: Content deduplication via content_hash.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from teams.dawo.scanners.competitor.duplicate_checker import CompetitorDuplicateChecker
from teams.dawo.scanners.competitor.schemas import ParsedContent


def _make_content(hash_val: str, name: str = "CompA") -> ParsedContent:
    return ParsedContent(
        source_type="instagram",
        competitor_name=name,
        source_url=f"https://instagram.com/p/{hash_val}",
        content_text=f"Content {hash_val}",
        hashtags=[],
        account_or_domain="comp_a",
        published_at=datetime(2026, 2, 10, tzinfo=UTC),
        content_hash=hash_val,
        has_health_language=False,
        health_keywords_matched=[],
    )


class TestCompetitorDuplicateChecker:
    """Tests for batch duplicate checking."""

    @pytest.mark.asyncio
    async def test_returns_only_new_items(self, mock_session):
        """Existing items filtered out, new ones returned."""
        # Mock DB returning one existing hash
        mock_result = MagicMock()
        mock_result.all.return_value = [("hash_existing", "CompA")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        checker = CompetitorDuplicateChecker(session=mock_session)
        items = [_make_content("hash_existing"), _make_content("hash_new")]

        result = await checker.check_duplicates(items)

        assert len(result) == 1
        assert result[0].content_hash == "hash_new"

    @pytest.mark.asyncio
    async def test_returns_all_when_none_exist(self, mock_session):
        """All items returned when none exist in DB."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        checker = CompetitorDuplicateChecker(session=mock_session)
        items = [_make_content("hash_a"), _make_content("hash_b")]

        result = await checker.check_duplicates(items)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_duplicates(self, mock_session):
        """Empty list when all items are duplicates."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("hash_a", "CompA"), ("hash_b", "CompA"),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        checker = CompetitorDuplicateChecker(session=mock_session)
        items = [_make_content("hash_a"), _make_content("hash_b")]

        result = await checker.check_duplicates(items)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_single_db_call_batch_query(self, mock_session):
        """Verify single DB call (batch, no N+1)."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        checker = CompetitorDuplicateChecker(session=mock_session)
        items = [_make_content(f"hash_{i}") for i in range(5)]

        await checker.check_duplicates(items)
        assert mock_session.execute.call_count == 1
