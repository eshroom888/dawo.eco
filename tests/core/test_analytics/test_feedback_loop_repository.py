"""Tests for FeedbackLoopRepository.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 2.2: Write repository tests (target: 15+ tests).

Uses AsyncMock(spec=AsyncSession) for unit tests following
the QualityScoringRepository pattern from Story 7-4.
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.analytics.feedback_loop_models import (
    FeedbackReport,
    WeightAdjustmentRecord,
)
from core.analytics.feedback_loop_repository import FeedbackLoopRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> FeedbackLoopRepository:
    """Create repository with mock session."""
    return FeedbackLoopRepository(mock_session)


class TestFeedbackLoopRepositorySaveReport:
    """Tests for save_report method."""

    async def test_save_report_merges_and_flushes(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        report = FeedbackReport(
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=150,
            status="complete",
        )
        mock_session.merge.return_value = report

        result = await repository.save_report(report)

        mock_session.merge.assert_awaited_once_with(report)
        mock_session.flush.assert_awaited_once()
        assert result is report

    async def test_save_report_returns_merged_instance(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        report = FeedbackReport(
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=150,
            status="complete",
        )
        merged = FeedbackReport(
            id=uuid4(),
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=150,
            status="complete",
        )
        mock_session.merge.return_value = merged

        result = await repository.save_report(report)
        assert result is merged


class TestFeedbackLoopRepositoryGetLatestReport:
    """Tests for get_latest_report method."""

    async def test_get_latest_report_returns_report(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        report = FeedbackReport(
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=150,
            status="complete",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = report
        mock_session.execute.return_value = result_mock

        result = await repository.get_latest_report()

        mock_session.execute.assert_awaited_once()
        assert result is report

    async def test_get_latest_report_returns_none_when_empty(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        result = await repository.get_latest_report()
        assert result is None


class TestFeedbackLoopRepositoryGetReportsByDateRange:
    """Tests for get_reports_by_date_range method."""

    async def test_get_reports_by_date_range_returns_list(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        reports = [
            FeedbackReport(
                report_date=date(2026, 2, 16),
                min_posts_threshold=100,
                total_posts_analyzed=120,
                status="complete",
            ),
            FeedbackReport(
                report_date=date(2026, 2, 23),
                min_posts_threshold=100,
                total_posts_analyzed=150,
                status="complete",
            ),
        ]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = reports
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repository.get_reports_by_date_range(
            start=date(2026, 2, 1), end=date(2026, 2, 28)
        )
        assert len(result) == 2
        assert result[0].report_date == date(2026, 2, 16)

    async def test_get_reports_by_date_range_empty(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repository.get_reports_by_date_range(
            start=date(2026, 1, 1), end=date(2026, 1, 31)
        )
        assert result == []


class TestFeedbackLoopRepositorySaveWeightAdjustment:
    """Tests for save_weight_adjustment method."""

    async def test_save_weight_adjustment(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        report_id = uuid4()
        record = WeightAdjustmentRecord(
            adjustment_type="quality_scoring",
            previous_weights={"engagement_vs_avg": 0.30},
            new_weights={"engagement_vs_avg": 0.35},
            feedback_report_id=report_id,
        )
        mock_session.merge.return_value = record

        result = await repository.save_weight_adjustment(record)

        mock_session.merge.assert_awaited_once_with(record)
        mock_session.flush.assert_awaited_once()
        assert result is record


class TestFeedbackLoopRepositoryGetWeightHistory:
    """Tests for get_weight_history method."""

    async def test_get_weight_history_returns_records(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        records = [
            WeightAdjustmentRecord(
                adjustment_type="quality_scoring",
                previous_weights={},
                new_weights={},
                feedback_report_id=uuid4(),
            ),
        ]
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = records
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repository.get_weight_history("quality_scoring", limit=10)
        assert len(result) == 1

    async def test_get_weight_history_filters_by_type(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        await repository.get_weight_history("source_scoring", limit=5)
        mock_session.execute.assert_awaited_once()


class TestFeedbackLoopRepositoryMarkAdjustmentApplied:
    """Tests for mark_adjustment_applied method."""

    async def test_mark_adjustment_applied(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        record_id = uuid4()
        record = WeightAdjustmentRecord(
            id=record_id,
            adjustment_type="quality_scoring",
            previous_weights={},
            new_weights={},
            feedback_report_id=uuid4(),
            applied=False,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = record
        mock_session.execute.return_value = result_mock

        await repository.mark_adjustment_applied(record_id)

        assert record.applied is True
        assert record.applied_at is not None
        mock_session.flush.assert_awaited_once()

    async def test_mark_adjustment_applied_not_found_raises(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        with pytest.raises(ValueError, match="not found"):
            await repository.mark_adjustment_applied(uuid4())

    async def test_mark_adjustment_applied_sets_timestamp(
        self, repository: FeedbackLoopRepository, mock_session: AsyncMock
    ) -> None:
        record_id = uuid4()
        record = WeightAdjustmentRecord(
            id=record_id,
            adjustment_type="quality_scoring",
            previous_weights={},
            new_weights={},
            feedback_report_id=uuid4(),
            applied=False,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = record
        mock_session.execute.return_value = result_mock

        before = datetime.now(UTC)
        await repository.mark_adjustment_applied(record_id)

        assert record.applied_at is not None
        assert record.applied_at >= before
