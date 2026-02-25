"""Tests for HealthClaimRepository.

Story 6-6, Task 7: Claim storage repository.
"""

from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from teams.dawo.scanners.claim_extraction.repository import HealthClaimRepository
from teams.dawo.scanners.claim_extraction.schemas import ClaimExtractionResult


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()  # session.add is sync in SQLAlchemy
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: MagicMock) -> HealthClaimRepository:
    return HealthClaimRepository(mock_session)


@pytest.fixture
def sample_claims() -> list[ClaimExtractionResult]:
    return [
        ClaimExtractionResult(
            claim_text="boosts immunity",
            surrounding_context="extract boosts immunity and energy",
            claim_category="enhancement",
            confidence_score=90,
            language_detected="en",
            extraction_method="hybrid",
            eu_article_reference="13.1",
            matched_pattern="boosts immunity",
            llm_reasoning="Enhancement claim",
        ),
        ClaimExtractionResult(
            claim_text="cures cancer",
            surrounding_context="product cures cancer naturally",
            claim_category="treatment",
            confidence_score=60,
            language_detected="en",
            extraction_method="regex",
            eu_article_reference="prohibited",
            matched_pattern="cures cancer",
        ),
    ]


class TestHealthClaimRepository:
    """Tests for HealthClaimRepository."""

    @pytest.mark.asyncio
    async def test_save_claims_inserts_all(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
        sample_claims: list[ClaimExtractionResult],
    ) -> None:
        content_id = uuid4()
        count = await repo.save_claims(content_id, sample_claims)
        assert count == 2
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_save_claims_empty_returns_zero(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        count = await repo.save_claims(uuid4(), [])
        assert count == 0
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_extraction_status(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        content_id = uuid4()
        await repo.update_extraction_status(content_id, "extracted")
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_high_confidence_claims(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        result = await repo.get_high_confidence_claims(min_confidence=70)
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_claims_for_content(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        content_id = uuid4()
        result = await repo.get_claims_for_content(content_id)
        assert result == []
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_claims_review_status_auto_approved(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        """High-confidence claim → review_status='auto_approved'."""
        claim = ClaimExtractionResult(
            claim_text="cures cancer",
            surrounding_context="product cures cancer",
            claim_category="treatment",
            confidence_score=90,
            language_detected="en",
            extraction_method="hybrid",
        )
        await repo.save_claims(uuid4(), [claim], confidence_threshold=70)
        record = mock_session.add.call_args[0][0]
        assert record.review_status == "auto_approved"

    @pytest.mark.asyncio
    async def test_save_claims_review_status_manual_review(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        """Low-confidence claim → review_status='manual_review'."""
        claim = ClaimExtractionResult(
            claim_text="boosts immunity",
            surrounding_context="product boosts immunity",
            claim_category="enhancement",
            confidence_score=55,
            language_detected="en",
            extraction_method="regex",
        )
        await repo.save_claims(uuid4(), [claim], confidence_threshold=70)
        record = mock_session.add.call_args[0][0]
        assert record.review_status == "manual_review"

    @pytest.mark.asyncio
    async def test_save_claims_review_status_at_threshold(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        """Claim exactly at threshold → review_status='auto_approved'."""
        claim = ClaimExtractionResult(
            claim_text="contains vitamin C",
            surrounding_context="product contains vitamin C",
            claim_category="general_wellness",
            confidence_score=70,
            language_detected="en",
            extraction_method="hybrid",
        )
        await repo.save_claims(uuid4(), [claim], confidence_threshold=70)
        record = mock_session.add.call_args[0][0]
        assert record.review_status == "auto_approved"

    @pytest.mark.asyncio
    async def test_commit(
        self,
        repo: HealthClaimRepository,
        mock_session: MagicMock,
    ) -> None:
        await repo.commit()
        mock_session.commit.assert_awaited_once()
