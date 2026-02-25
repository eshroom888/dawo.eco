"""Tests for PipelineService.

Story 5-5, Task 3/9.2-9.9: Tests pipeline service business logic
with mocked LeadRepository.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.leads.models import Lead, LeadActivity, LeadStatus, ActivityType


class TestPipelineServiceGetDashboardSummary:
    """Tests for PipelineService.get_dashboard_summary()."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get_pipeline_summary = AsyncMock(return_value={
            "new": 5, "researching": 2, "qualified": 3,
            "outreach_pending": 2, "contacted": 4, "replied": 1,
            "meeting_scheduled": 0, "negotiating": 0,
            "converted": 1, "lost": 0, "nurture": 0,
        })
        repo.get_followup_candidates = AsyncMock(return_value=[
            MagicMock(spec=Lead), MagicMock(spec=Lead),
        ])
        repo.get_conversion_metrics = AsyncMock(return_value={
            "total_leads": 18, "converted_count": 1,
            "conversion_rate": 5.56, "status_counts": {},
        })
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        from teams.dawo.leads.pipeline.service import PipelineService
        return PipelineService(mock_repo)

    async def test_returns_summary_with_all_fields(self, service):
        """get_dashboard_summary returns complete summary data."""
        summary = await service.get_dashboard_summary()

        assert summary.total_leads == 18
        assert summary.followup_count == 2
        assert summary.conversion_rate == 5.56
        assert summary.status_counts["new"] == 5

    async def test_calls_repository_methods(self, service, mock_repo):
        """get_dashboard_summary calls all required repository methods."""
        await service.get_dashboard_summary()

        mock_repo.get_pipeline_summary.assert_called_once()
        mock_repo.get_followup_candidates.assert_called_once()
        mock_repo.get_conversion_metrics.assert_called_once()


class TestPipelineServiceGetMetrics:
    """Tests for PipelineService.get_metrics()."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get_conversion_metrics = AsyncMock(return_value={
            "total_leads": 40, "converted_count": 5,
            "conversion_rate": 12.5, "status_counts": {},
        })
        repo.get_avg_time_per_stage = AsyncMock(return_value={
            "new": 2.5, "contacted": 5.5,
        })
        repo.get_weekly_trend = AsyncMock(return_value=[
            {"week": "2026-W04", "new_leads": 5, "converted": 1},
        ])
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        from teams.dawo.leads.pipeline.service import PipelineService
        return PipelineService(mock_repo)

    async def test_returns_conversion_metrics(self, service):
        """get_metrics returns conversion rate data."""
        metrics = await service.get_metrics()

        assert metrics.conversion_rate == 12.5
        assert metrics.total_leads == 40
        assert metrics.converted_count == 5

    async def test_returns_avg_time_per_stage(self, service):
        """get_metrics includes avg time per stage."""
        metrics = await service.get_metrics()

        assert metrics.avg_time_per_stage["new"] == 2.5
        assert metrics.avg_time_per_stage["contacted"] == 5.5

    async def test_returns_weekly_trend(self, service):
        """get_metrics includes weekly trend data."""
        metrics = await service.get_metrics()

        assert len(metrics.weekly_trend) == 1
        assert metrics.weekly_trend[0]["week"] == "2026-W04"


class TestPipelineServiceUpdateLeadStatus:
    """Tests for PipelineService.update_lead_status()."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_lead(self):
        lead = MagicMock(spec=Lead)
        lead.id = uuid4()
        lead.email = "test@example.com"
        lead.status = LeadStatus.CONTACTED.value
        lead.last_contacted_at = datetime.now(UTC) - timedelta(days=3)
        lead.last_replied_at = None
        lead.converted_at = None
        lead.lost_reason = None
        lead.next_followup_at = None
        return lead

    @pytest.fixture
    def service(self, mock_repo):
        from teams.dawo.leads.pipeline.service import PipelineService
        return PipelineService(mock_repo)

    async def test_valid_transition_succeeds(self, service, mock_repo, mock_lead):
        """update_lead_status succeeds for valid transition."""
        mock_repo.get_lead_by_id = AsyncMock(return_value=mock_lead)
        mock_repo.add_activity = AsyncMock()

        result = await service.update_lead_status(
            mock_lead.id, LeadStatus.REPLIED, actor="operator@dawo.eco"
        )

        assert result is not None
        # Verify only ONE activity is logged (H1 fix)
        mock_repo.add_activity.assert_called_once()
        # Verify repo.update_lead_status is NOT called (service sets fields directly)
        mock_repo.update_lead_status.assert_not_called()

    async def test_invalid_transition_raises_error(self, service, mock_repo, mock_lead):
        """update_lead_status raises ValueError for invalid transition."""
        mock_lead.status = LeadStatus.CONVERTED.value
        mock_repo.get_lead_by_id = AsyncMock(return_value=mock_lead)

        with pytest.raises(ValueError, match="Invalid transition"):
            await service.update_lead_status(
                mock_lead.id, LeadStatus.NEW, actor="operator@dawo.eco"
            )

    async def test_sets_converted_at_on_conversion(self, service, mock_repo, mock_lead):
        """update_lead_status sets converted_at when transitioning to CONVERTED."""
        mock_lead.status = LeadStatus.REPLIED.value
        mock_repo.get_lead_by_id = AsyncMock(return_value=mock_lead)
        mock_repo.add_activity = AsyncMock()

        await service.update_lead_status(
            mock_lead.id, LeadStatus.CONVERTED, actor="operator@dawo.eco"
        )

        # Verify converted_at was set
        assert mock_lead.converted_at is not None

    async def test_sets_lost_reason_on_lost(self, service, mock_repo, mock_lead):
        """update_lead_status sets lost_reason when transitioning to LOST."""
        mock_repo.get_lead_by_id = AsyncMock(return_value=mock_lead)
        mock_repo.add_activity = AsyncMock()

        await service.update_lead_status(
            mock_lead.id, LeadStatus.LOST,
            reason="No budget", actor="operator@dawo.eco"
        )

        assert mock_lead.lost_reason == "No budget"

    async def test_sets_last_replied_at_on_replied(self, service, mock_repo, mock_lead):
        """update_lead_status sets last_replied_at on REPLIED."""
        mock_repo.get_lead_by_id = AsyncMock(return_value=mock_lead)
        mock_repo.add_activity = AsyncMock()

        await service.update_lead_status(
            mock_lead.id, LeadStatus.REPLIED, actor="operator@dawo.eco"
        )

        assert mock_lead.last_replied_at is not None

    async def test_lead_not_found_raises_error(self, service, mock_repo):
        """update_lead_status raises ValueError for unknown lead."""
        mock_repo.get_lead_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Lead not found"):
            await service.update_lead_status(
                uuid4(), LeadStatus.REPLIED, actor="operator@dawo.eco"
            )


class TestPipelineServiceDetectFollowups:
    """Tests for PipelineService.detect_followups()."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        from teams.dawo.leads.pipeline.service import PipelineService
        return PipelineService(mock_repo)

    async def test_returns_followup_candidates(self, service, mock_repo):
        """detect_followups returns leads past threshold."""
        lead = MagicMock(spec=Lead)
        lead.id = uuid4()
        lead.last_contacted_at = datetime.now(UTC) - timedelta(days=10)
        mock_repo.get_followup_candidates = AsyncMock(return_value=[lead])

        result = await service.detect_followups()
        assert len(result) == 1

    async def test_excludes_replied_leads(self, service, mock_repo):
        """detect_followups delegates to repository which excludes replied leads."""
        mock_repo.get_followup_candidates = AsyncMock(return_value=[])

        result = await service.detect_followups()
        assert len(result) == 0
        mock_repo.get_followup_candidates.assert_called_once()


class TestPipelineServiceAddNote:
    """Tests for PipelineService.add_note()."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        from teams.dawo.leads.pipeline.service import PipelineService
        return PipelineService(mock_repo)

    async def test_creates_note_activity(self, service, mock_repo):
        """add_note creates a NOTE_ADDED activity."""
        lead_id = uuid4()
        activity = MagicMock(spec=LeadActivity)
        mock_repo.get_lead_by_id = AsyncMock(return_value=MagicMock(spec=Lead))
        mock_repo.add_activity = AsyncMock(return_value=activity)

        result = await service.add_note(
            lead_id, "Follow up next week", actor="operator@dawo.eco"
        )

        mock_repo.add_activity.assert_called_once()
        call_args = mock_repo.add_activity.call_args
        assert call_args[1]["activity_type"] == ActivityType.NOTE_ADDED

    async def test_lead_not_found_raises_error(self, service, mock_repo):
        """add_note raises ValueError for unknown lead."""
        mock_repo.get_lead_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Lead not found"):
            await service.add_note(uuid4(), "Note", actor="operator@dawo.eco")


class TestValidManualTransitions:
    """Tests for VALID_MANUAL_TRANSITIONS completeness."""

    def test_all_statuses_have_transition_entry(self):
        """Every LeadStatus has an entry in VALID_MANUAL_TRANSITIONS."""
        from teams.dawo.leads.pipeline.service import VALID_MANUAL_TRANSITIONS

        for status in LeadStatus:
            assert status.value in VALID_MANUAL_TRANSITIONS, (
                f"Missing transition entry for {status.value}"
            )

    def test_converted_has_no_outbound_transitions(self):
        """CONVERTED is terminal — no transitions out."""
        from teams.dawo.leads.pipeline.service import VALID_MANUAL_TRANSITIONS

        assert VALID_MANUAL_TRANSITIONS[LeadStatus.CONVERTED.value] == set()

    def test_lost_can_go_to_nurture(self):
        """LOST leads can be reactivated to NURTURE."""
        from teams.dawo.leads.pipeline.service import VALID_MANUAL_TRANSITIONS

        assert LeadStatus.NURTURE.value in VALID_MANUAL_TRANSITIONS[LeadStatus.LOST.value]
