"""Tests for ViolationRepository (Story 6-7, Task 6)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from teams.dawo.scanners.violation_detection.repository import ViolationRepository
from teams.dawo.scanners.violation_detection.schemas import ViolationResult


def _make_result(**overrides) -> ViolationResult:
    """Create a ViolationResult with sensible defaults."""
    defaults = {
        "extracted_claim_id": uuid4(),
        "claim_text": "treats brain fog",
        "claim_category": "treatment",
        "confidence_score": 92,
        "violation_status": "violation",
        "severity": "high",
        "regulation_article": "EC 1924/2006 Art. 10",
        "violation_type": "unauthorized_treatment_claim",
        "detection_reasoning": "Treatment claim prohibited.",
        "authorized_claims_checked": 0,
        "nearest_authorized_claim": None,
        "competitor_name": "CompetitorA",
        "source_url": "https://example.com/post",
        "evidence_status": "pending_collection",
    }
    defaults.update(overrides)
    return ViolationResult(**defaults)


class TestViolationRepository:
    """Tests for ViolationRepository."""

    @pytest.mark.asyncio
    async def test_save_violation_inserts_and_returns(
        self, mock_session
    ) -> None:
        """save_violation inserts record and returns ORM object."""
        repo = ViolationRepository(session=mock_session)
        result = _make_result()

        violation = await repo.save_violation(result)

        assert mock_session.add.called
        assert violation.violation_status == "violation"
        assert violation.severity == "high"

    @pytest.mark.asyncio
    async def test_save_violations_batch_returns_count(
        self, mock_session
    ) -> None:
        """save_violations_batch inserts all and returns count."""
        repo = ViolationRepository(session=mock_session)
        results = [_make_result() for _ in range(3)]

        count = await repo.save_violations_batch(results)

        assert count == 3
        assert mock_session.add.call_count == 3

    @pytest.mark.asyncio
    async def test_save_violations_batch_empty_returns_zero(
        self, mock_session
    ) -> None:
        """save_violations_batch with empty list returns 0."""
        repo = ViolationRepository(session=mock_session)

        count = await repo.save_violations_batch([])

        assert count == 0
        assert mock_session.add.call_count == 0

    @pytest.mark.asyncio
    async def test_get_evaluated_claim_ids_returns_uuid_set(
        self, mock_session
    ) -> None:
        """get_evaluated_claim_ids returns correct UUID set."""
        id1 = uuid4()
        id2 = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [id1, id2]
        mock_session.execute.return_value = mock_result

        repo = ViolationRepository(session=mock_session)
        ids = await repo.get_evaluated_claim_ids()

        assert ids == {id1, id2}

    @pytest.mark.asyncio
    async def test_get_violations_by_status_filters(
        self, mock_session
    ) -> None:
        """get_violations_by_status filters by violation_status."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = ViolationRepository(session=mock_session)
        violations = await repo.get_violations_by_status("violation")

        assert mock_session.execute.called
        assert violations == []

    @pytest.mark.asyncio
    async def test_get_violations_by_competitor_filters(
        self, mock_session
    ) -> None:
        """get_violations_by_competitor filters by competitor_name."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = ViolationRepository(session=mock_session)
        violations = await repo.get_violations_by_competitor("CompetitorA")

        assert mock_session.execute.called
        assert violations == []

    @pytest.mark.asyncio
    async def test_get_pending_evidence_collection(
        self, mock_session
    ) -> None:
        """get_pending_evidence_collection returns pending_collection only."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = ViolationRepository(session=mock_session)
        violations = await repo.get_pending_evidence_collection()

        assert mock_session.execute.called
        assert violations == []

    @pytest.mark.asyncio
    async def test_commit_calls_session_commit(self, mock_session) -> None:
        """commit() calls session.commit()."""
        repo = ViolationRepository(session=mock_session)

        await repo.commit()

        mock_session.commit.assert_awaited_once()
