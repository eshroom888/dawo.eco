"""Tests for QualityScoringRepository.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 2.10: Write repository tests (15+ tests).

Uses AsyncMock for session to test repository logic without database.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.analytics.quality_scoring_models import PostPublishScoreRecord
from core.analytics.quality_scoring_repository import QualityScoringRepository


def _make_record(
    post_id: str = "post-001",
    media_id: str = "media-001",
    pre_publish_score: Decimal | None = Decimal("7.0"),
    post_publish_score: Decimal = Decimal("6.5"),
    variance: Decimal = Decimal("-0.5"),
    flagged_for_review: bool = False,
    calculated_at: datetime | None = None,
) -> PostPublishScoreRecord:
    """Factory for creating test records."""
    return PostPublishScoreRecord(
        post_id=post_id,
        media_id=media_id,
        pre_publish_score=pre_publish_score,
        post_publish_score=post_publish_score,
        variance=variance,
        component_scores={"engagement_vs_avg": {"raw_score": 6.5, "weight": 0.3}},
        metrics_snapshot={"engagement_rate": 0.04},
        flagged_for_review=flagged_for_review,
        snapshot_label="7d",
        calculated_at=calculated_at or datetime.now(UTC),
    )


class TestQualityScoringRepositoryInit:
    """Test repository initialization."""

    def test_constructor_accepts_session(self) -> None:
        session = AsyncMock()
        repo = QualityScoringRepository(session)
        assert repo._session is session


class TestSaveScore:
    """Tests for save_score method (Task 2.2)."""

    @pytest.mark.asyncio
    async def test_save_score_calls_merge(self) -> None:
        session = AsyncMock()
        record = _make_record()
        session.merge.return_value = record

        repo = QualityScoringRepository(session)
        result = await repo.save_score(record)

        session.merge.assert_called_once_with(record)
        session.flush.assert_called_once()
        assert result is record

    @pytest.mark.asyncio
    async def test_save_score_returns_merged_record(self) -> None:
        session = AsyncMock()
        record = _make_record(post_id="post-new")
        merged = _make_record(post_id="post-new")
        session.merge.return_value = merged

        repo = QualityScoringRepository(session)
        result = await repo.save_score(record)

        assert result is merged


class TestGetByPostId:
    """Tests for get_by_post_id method (Task 2.3)."""

    @pytest.mark.asyncio
    async def test_returns_record_when_found(self) -> None:
        session = AsyncMock()
        record = _make_record(post_id="post-found")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = record
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_by_post_id("post-found")

        assert result is record
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_by_post_id("post-missing")

        assert result is None


class TestGetByPostIds:
    """Tests for get_by_post_ids method (Task 2.4)."""

    @pytest.mark.asyncio
    async def test_returns_dict_of_records(self) -> None:
        session = AsyncMock()
        r1 = _make_record(post_id="post-a")
        r2 = _make_record(post_id="post-b")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1, r2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_by_post_ids(["post-a", "post-b"])

        assert result["post-a"] is r1
        assert result["post-b"] is r2
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_dict_for_empty_input(self) -> None:
        session = AsyncMock()
        repo = QualityScoringRepository(session)
        result = await repo.get_by_post_ids([])

        assert result == {}
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_ids_not_in_result(self) -> None:
        session = AsyncMock()
        r1 = _make_record(post_id="post-a")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_by_post_ids(["post-a", "post-missing"])

        assert "post-a" in result
        assert "post-missing" not in result


class TestGetFlaggedForReview:
    """Tests for get_flagged_for_review method (Task 2.5)."""

    @pytest.mark.asyncio
    async def test_returns_flagged_records(self) -> None:
        session = AsyncMock()
        r1 = _make_record(flagged_for_review=True, variance=Decimal("-4.0"))

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_flagged_for_review(limit=50)

        assert len(result) == 1
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_flagged(self) -> None:
        session = AsyncMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_flagged_for_review()

        assert result == []


class TestGetAllScored:
    """Tests for get_all_scored method (Task 2.6)."""

    @pytest.mark.asyncio
    async def test_returns_records_with_both_scores(self) -> None:
        session = AsyncMock()
        r1 = _make_record(pre_publish_score=Decimal("8.0"))

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_all_scored(limit=500)

        assert len(result) == 1
        session.execute.assert_called_once()


class TestGetScoredCount:
    """Tests for get_scored_count method (Task 2.7)."""

    @pytest.mark.asyncio
    async def test_returns_count_of_scored_posts(self) -> None:
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 55
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_scored_count()

        assert result == 55

    @pytest.mark.asyncio
    async def test_returns_zero_when_none_scored(self) -> None:
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_scored_count()

        assert result == 0


class TestGetAveragePostPublishScore:
    """Tests for get_average_post_publish_score method (Task 2.8)."""

    @pytest.mark.asyncio
    async def test_returns_average_score(self) -> None:
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Decimal("6.8")
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_average_post_publish_score(days_back=30)

        assert result == Decimal("6.8")

    @pytest.mark.asyncio
    async def test_returns_none_when_no_records(self) -> None:
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_average_post_publish_score()

        assert result is None


class TestGetComponentAverages:
    """Tests for get_component_averages method (Task 2.9)."""

    @pytest.mark.asyncio
    async def test_returns_component_averages(self) -> None:
        session = AsyncMock()

        # Simulate raw records with component_scores JSONB
        r1 = _make_record(post_id="p1")
        r1.component_scores = {
            "engagement_vs_avg": {"weighted_score": 2.4},
            "reach_vs_avg": {"weighted_score": 1.2},
        }
        r2 = _make_record(post_id="p2")
        r2.component_scores = {
            "engagement_vs_avg": {"weighted_score": 1.8},
            "reach_vs_avg": {"weighted_score": 1.6},
        }

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [r1, r2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_component_averages(days_back=30)

        assert "engagement_vs_avg" in result
        assert "reach_vs_avg" in result
        # Average of 2.4 and 1.8 = 2.1
        assert abs(result["engagement_vs_avg"] - 2.1) < 0.01
        # Average of 1.2 and 1.6 = 1.4
        assert abs(result["reach_vs_avg"] - 1.4) < 0.01

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_records(self) -> None:
        session = AsyncMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute.return_value = mock_result

        repo = QualityScoringRepository(session)
        result = await repo.get_component_averages()

        assert result == {}
