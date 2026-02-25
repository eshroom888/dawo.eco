"""Tests for LeadRepository pipeline query methods.

Story 5-5, Task 2/9.14-9.20: Tests pipeline-specific repository methods
with mocked AsyncSession.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from teams.dawo.leads.repository import LeadRepository
from core.leads.models import Lead, LeadActivity, LeadStatus, ActivityType


class TestGetPipelineSummary:
    """Tests for get_pipeline_summary()."""

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create LeadRepository with mock session."""
        return LeadRepository(session=mock_session)

    async def test_returns_counts_for_all_statuses(self, repository, mock_session):
        """get_pipeline_summary returns count for every LeadStatus value."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("new", 5),
            ("qualified", 3),
            ("contacted", 4),
            ("converted", 1),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        summary = await repository.get_pipeline_summary()

        # All statuses should be present, even those with 0 count
        for status in LeadStatus:
            assert status.value in summary
        assert summary["new"] == 5
        assert summary["qualified"] == 3
        assert summary["contacted"] == 4
        assert summary["converted"] == 1
        assert summary["lost"] == 0  # Not in DB results, should default to 0

    async def test_empty_database_returns_all_zeros(self, repository, mock_session):
        """get_pipeline_summary returns all zeros when no leads exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        summary = await repository.get_pipeline_summary()

        for status in LeadStatus:
            assert summary[status.value] == 0


class TestGetLeadsFiltered:
    """Tests for get_leads_filtered()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    @pytest.fixture
    def sample_leads(self):
        """Create sample lead mocks."""
        leads = []
        for i in range(3):
            lead = MagicMock(spec=Lead)
            lead.id = uuid4()
            lead.email = f"lead{i}@example.com"
            lead.status = "contacted"
            lead.score = 80.0 - i * 10
            leads.append(lead)
        return leads

    async def test_returns_leads_and_total_count(self, repository, mock_session, sample_leads):
        """get_leads_filtered returns tuple of (leads, total_count)."""
        # Mock for the count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 3

        # Mock for the leads query
        mock_leads_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_leads
        mock_leads_result.scalars.return_value = mock_scalars

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_leads_result]
        )

        leads, total = await repository.get_leads_filtered(
            limit=25, offset=0
        )

        assert len(leads) == 3
        assert total == 3

    async def test_pagination_with_limit_and_offset(self, repository, mock_session, sample_leads):
        """get_leads_filtered respects limit and offset."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10

        mock_leads_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_leads[:2]
        mock_leads_result.scalars.return_value = mock_scalars

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_leads_result]
        )

        leads, total = await repository.get_leads_filtered(
            limit=2, offset=5
        )

        assert len(leads) == 2
        assert total == 10

    async def test_filter_by_status(self, repository, mock_session, sample_leads):
        """get_leads_filtered accepts optional status filter."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        mock_leads_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_leads[:2]
        mock_leads_result.scalars.return_value = mock_scalars

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_leads_result]
        )

        leads, total = await repository.get_leads_filtered(
            status=LeadStatus.CONTACTED, limit=25, offset=0
        )

        assert total == 2

    async def test_search_filter(self, repository, mock_session, sample_leads):
        """get_leads_filtered accepts optional search term."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_leads_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_leads[0]]
        mock_leads_result.scalars.return_value = mock_scalars

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_leads_result]
        )

        leads, total = await repository.get_leads_filtered(
            search="example", limit=25, offset=0
        )

        assert total == 1


class TestGetLeadWithRelations:
    """Tests for get_lead_with_relations()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    async def test_returns_lead_with_eager_loaded_relations(self, repository, mock_session):
        """get_lead_with_relations returns lead with activities and emails."""
        lead_id = uuid4()
        mock_lead = MagicMock(spec=Lead)
        mock_lead.id = lead_id
        mock_lead.activities = []
        mock_lead.emails = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_lead
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_lead_with_relations(lead_id)

        assert result is not None
        assert result.id == lead_id

    async def test_returns_none_for_unknown_id(self, repository, mock_session):
        """get_lead_with_relations returns None for nonexistent lead."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_lead_with_relations(uuid4())
        assert result is None


class TestGetLeadActivities:
    """Tests for get_lead_activities()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    async def test_returns_activities_for_lead(self, repository, mock_session):
        """get_lead_activities returns activity records."""
        lead_id = uuid4()
        activities = [MagicMock(spec=LeadActivity) for _ in range(3)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_lead_activities(lead_id)
        assert len(result) == 3

    async def test_respects_limit_parameter(self, repository, mock_session):
        """get_lead_activities respects the limit parameter."""
        lead_id = uuid4()
        activities = [MagicMock(spec=LeadActivity) for _ in range(5)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_lead_activities(lead_id, limit=5)
        assert len(result) == 5


class TestGetFollowupCandidates:
    """Tests for get_followup_candidates()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    async def test_returns_overdue_leads(self, repository, mock_session):
        """get_followup_candidates returns leads past threshold."""
        lead = MagicMock(spec=Lead)
        lead.status = LeadStatus.CONTACTED.value
        lead.last_contacted_at = datetime.now(UTC) - timedelta(days=10)
        lead.last_replied_at = None

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [lead]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_followup_candidates(days_threshold=7)
        assert len(result) == 1

    async def test_empty_when_no_overdue_leads(self, repository, mock_session):
        """get_followup_candidates returns empty when no leads are overdue."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_followup_candidates()
        assert len(result) == 0


class TestGetConversionMetrics:
    """Tests for get_conversion_metrics()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    async def test_returns_conversion_data(self, repository, mock_session):
        """get_conversion_metrics returns total, per-status, and conversion rate."""
        # Mock total count
        mock_total_result = MagicMock()
        mock_total_result.scalar_one.return_value = 20

        # Mock converted count
        mock_converted_result = MagicMock()
        mock_converted_result.scalar_one.return_value = 3

        # Mock per-status counts
        mock_status_result = MagicMock()
        mock_status_result.all.return_value = [
            ("new", 5), ("qualified", 4), ("contacted", 6),
            ("converted", 3), ("lost", 2),
        ]

        mock_session.execute = AsyncMock(
            side_effect=[mock_total_result, mock_converted_result, mock_status_result]
        )

        metrics = await repository.get_conversion_metrics()

        assert metrics["total_leads"] == 20
        assert metrics["converted_count"] == 3
        assert metrics["conversion_rate"] == 15.0  # 3/20 * 100

    async def test_zero_leads_returns_zero_rate(self, repository, mock_session):
        """get_conversion_metrics returns 0% rate when no leads exist."""
        mock_total_result = MagicMock()
        mock_total_result.scalar_one.return_value = 0

        mock_converted_result = MagicMock()
        mock_converted_result.scalar_one.return_value = 0

        mock_status_result = MagicMock()
        mock_status_result.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[mock_total_result, mock_converted_result, mock_status_result]
        )

        metrics = await repository.get_conversion_metrics()
        assert metrics["conversion_rate"] == 0.0


class TestGetWeeklyTrend:
    """Tests for get_weekly_trend()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    async def test_returns_weekly_data(self, repository, mock_session):
        """get_weekly_trend returns weekly new and converted counts."""
        # Mock new leads query
        mock_new_result = MagicMock()
        mock_new_result.all.return_value = [
            ("2026-W04", 5),
            ("2026-W05", 8),
        ]

        # Mock converted leads query
        mock_converted_result = MagicMock()
        mock_converted_result.all.return_value = [
            ("2026-W04", 1),
            ("2026-W05", 2),
        ]

        mock_session.execute = AsyncMock(
            side_effect=[mock_new_result, mock_converted_result]
        )

        trend = await repository.get_weekly_trend(weeks=8)
        assert len(trend) >= 1
        assert "week" in trend[0]
        assert "new_leads" in trend[0]
        assert "converted" in trend[0]


class TestGetAvgTimePerStage:
    """Tests for get_avg_time_per_stage()."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return LeadRepository(session=mock_session)

    async def test_returns_avg_days_per_status(self, repository, mock_session):
        """get_avg_time_per_stage returns dict of status -> avg days."""
        now = datetime.now(UTC)
        # Mock activities: simulate status changes
        activities = [
            MagicMock(
                lead_id=uuid4(),
                activity_type=ActivityType.STATUS_CHANGE.value,
                activity_metadata={
                    "old_status": "new",
                    "new_status": "contacted",
                },
                created_at=now - timedelta(days=3),
            ),
            MagicMock(
                lead_id=uuid4(),
                activity_type=ActivityType.STATUS_CHANGE.value,
                activity_metadata={
                    "old_status": "new",
                    "new_status": "contacted",
                },
                created_at=now - timedelta(days=5),
            ),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = activities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_avg_time_per_stage()
        assert isinstance(result, dict)
