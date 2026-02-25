"""Integration Tests for Pipeline Status Tracking.

Epic 5: B2B Sales Pipeline
Story 5-5: Lead Pipeline Status Tracking
Task 11: Integration Tests

Tests the full pipeline flow with mocked repository but real interactions
between PipelineService, CSVExporter, and the FastAPI router.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.leads.models import Lead, LeadActivity, LeadStatus, ActivityType
from teams.dawo.leads.pipeline.service import PipelineService, VALID_MANUAL_TRANSITIONS
from teams.dawo.leads.pipeline.csv_export import CSVExporter
from teams.dawo.leads.pipeline.schemas import PipelineSummary, ConversionMetrics, FollowUpCandidate
from ui.backend.routers.pipeline import router, get_repository, get_pipeline_service, get_csv_exporter


# --- Helpers ---


def _make_lead(
    email: str = "lead@example.com",
    company: str = "TestCo",
    status: str = LeadStatus.NEW.value,
    score: float = 50.0,
    contact_count: int = 0,
    last_contacted_at=None,
    last_replied_at=None,
    created_at=None,
):
    """Create a mock Lead with realistic data."""
    lead = MagicMock(spec=Lead)
    lead.id = uuid4()
    lead.email = email
    lead.first_name = "Test"
    lead.last_name = "User"
    lead.company = company
    lead.job_title = "Manager"
    lead.status = status
    lead.source = "linkedin"
    lead.score = score
    lead.contact_count = contact_count
    lead.last_contacted_at = last_contacted_at
    lead.last_replied_at = last_replied_at
    lead.created_at = created_at or datetime(2026, 1, 15, tzinfo=UTC)
    lead.updated_at = datetime(2026, 2, 10, tzinfo=UTC)
    lead.linkedin_url = None
    lead.website_url = None
    lead.phone = None
    lead.country = "Norway"
    lead.industry = "Health & Wellness"
    lead.company_size = "11-50"
    lead.enrichment_data = None
    lead.outreach_data = None
    lead.tags = []
    lead.notes = None
    lead.assigned_to = None
    lead.next_followup_at = None
    lead.converted_at = None
    lead.lost_reason = None
    lead.activities = []
    lead.emails = []
    return lead


def _make_activity(
    lead_id=None,
    activity_type: str = "status_change",
    description: str = "Status changed",
    actor: str = "system",
    metadata=None,
):
    """Create a mock LeadActivity."""
    activity = MagicMock(spec=LeadActivity)
    activity.id = uuid4()
    activity.lead_id = lead_id or uuid4()
    activity.activity_type = activity_type
    activity.description = description
    activity.created_at = datetime.now(UTC)
    activity.created_by = actor
    activity.activity_metadata = metadata or {}
    return activity


# --- Fixtures ---


@pytest.fixture
def mock_repo():
    """Create mock repository with default behaviors."""
    repo = AsyncMock()
    repo.get_pipeline_summary = AsyncMock(return_value={
        "new": 5, "researching": 3, "qualified": 4, "outreach_pending": 2,
        "contacted": 6, "replied": 2, "meeting_scheduled": 1, "negotiating": 1,
        "converted": 3, "lost": 2, "nurture": 1,
    })
    repo.get_followup_candidates = AsyncMock(return_value=[])
    repo.get_conversion_metrics = AsyncMock(return_value={
        "total_leads": 30, "converted_count": 3, "conversion_rate": 10.0, "status_counts": {},
    })
    repo.get_weekly_trend = AsyncMock(return_value=[
        {"week": "2026-W06", "new_leads": 5, "converted": 1},
    ])
    repo.get_avg_time_per_stage = AsyncMock(return_value={"new": 3.0, "contacted": 5.0})
    return repo


@pytest.fixture
def service(mock_repo):
    """Create PipelineService with mock repo."""
    return PipelineService(mock_repo)


@pytest.fixture
def exporter(mock_repo):
    """Create CSVExporter with mock repo."""
    return CSVExporter(mock_repo)


@pytest.fixture
def app(mock_repo, service, exporter):
    """Create test FastAPI app with real service and exporter."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: mock_repo
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_csv_exporter] = lambda: exporter
    return app


@pytest.fixture
def client(app):
    """Create TestClient."""
    return TestClient(app)


# --- Test Classes ---


class TestFullPipelineFlow:
    """Test 11.1: Full pipeline flow NEW → CONTACTED → REPLIED → CONVERTED."""

    @pytest.mark.asyncio
    async def test_status_transitions_through_pipeline(self, mock_repo, service):
        """Lead progresses through stages via actual service calls."""
        lead = _make_lead(status=LeadStatus.CONTACTED.value)
        mock_repo.get_lead_by_id = AsyncMock(return_value=lead)
        mock_repo.add_activity = AsyncMock()

        # CONTACTED → REPLIED
        await service.update_lead_status(lead.id, LeadStatus.REPLIED, actor="operator")
        assert lead.status == LeadStatus.REPLIED.value
        assert lead.last_replied_at is not None

        # REPLIED → MEETING_SCHEDULED
        await service.update_lead_status(lead.id, LeadStatus.MEETING_SCHEDULED, actor="operator")
        assert lead.status == LeadStatus.MEETING_SCHEDULED.value

        # MEETING_SCHEDULED → NEGOTIATING
        await service.update_lead_status(lead.id, LeadStatus.NEGOTIATING, actor="operator")
        assert lead.status == LeadStatus.NEGOTIATING.value

        # NEGOTIATING → CONVERTED
        await service.update_lead_status(lead.id, LeadStatus.CONVERTED, actor="operator")
        assert lead.status == LeadStatus.CONVERTED.value
        assert lead.converted_at is not None

        # CONVERTED is terminal — no transitions out
        assert len(VALID_MANUAL_TRANSITIONS[LeadStatus.CONVERTED]) == 0


class TestFollowUpDetection:
    """Test 11.2: Follow-up detection after simulated 7-day gap."""

    @pytest.mark.asyncio
    async def test_detects_overdue_followups(self, mock_repo, service):
        """Leads contacted > 7 days ago are flagged for follow-up."""
        old_date = datetime.now(UTC) - timedelta(days=10)
        lead = _make_lead(
            status=LeadStatus.CONTACTED.value,
            last_contacted_at=old_date,
        )
        lead.last_replied_at = None

        mock_repo.get_followup_candidates = AsyncMock(return_value=[lead])

        candidates = await service.detect_followups(days_threshold=7)

        assert len(candidates) == 1
        assert candidates[0].lead_id == lead.id
        assert candidates[0].days_since_contact >= 10
        mock_repo.get_followup_candidates.assert_called_once_with(7)


class TestManualStatusTransitionsWithLogging:
    """Test 11.3: Manual status transitions with activity logging."""

    @pytest.mark.asyncio
    async def test_status_change_creates_activity(self, mock_repo, service):
        """Manual status change creates exactly one activity log entry."""
        lead = _make_lead(status=LeadStatus.CONTACTED.value)

        mock_repo.get_lead_by_id = AsyncMock(return_value=lead)
        mock_repo.add_activity = AsyncMock()

        await service.update_lead_status(
            lead_id=lead.id,
            new_status=LeadStatus.REPLIED,
            reason="Customer replied via email",
            actor="operator",
        )

        # Service sets fields directly — repo.update_lead_status not called
        mock_repo.update_lead_status.assert_not_called()
        # Exactly one activity logged (no duplicates)
        mock_repo.add_activity.assert_called_once()
        call_kwargs = mock_repo.add_activity.call_args[1]
        assert call_kwargs["metadata"]["actor"] == "operator"
        assert call_kwargs["metadata"]["source"] == "pipeline_dashboard"


class TestCSVExportWithTransitions:
    """Test 11.4: CSV export includes correct data after status transitions."""

    @pytest.mark.asyncio
    async def test_csv_export_contains_leads(self, mock_repo, exporter):
        """CSV export includes all lead data."""
        lead = _make_lead(
            email="jane@eco.com",
            company="EcoCorp",
            status=LeadStatus.CONTACTED.value,
            score=85.0,
        )
        mock_repo.get_leads_filtered = AsyncMock(return_value=([lead], 1))

        csv = await exporter.export_leads()

        assert "email" in csv.lower()  # Has headers
        assert "jane@eco.com" in csv
        assert "EcoCorp" in csv


class TestPipelineSummaryAccuracy:
    """Test 11.5: Pipeline summary accuracy with mixed lead statuses."""

    def test_summary_endpoint_returns_all_metrics(self, client, mock_repo):
        """GET /summary includes all expected metrics from mixed statuses."""
        response = client.get("/api/pipeline/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "status_counts" in data
        assert "conversion_rate" in data
        assert "followup_count" in data
        assert data["total_leads"] == 30  # Sum from mock


class TestConversionMetricsEndToEnd:
    """Test 11.6: Conversion metrics calculation end-to-end."""

    def test_metrics_endpoint_returns_conversion_data(self, client):
        """GET /metrics returns conversion rate and funnel data."""
        response = client.get("/api/pipeline/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["conversion_rate"] == 10.0
        assert data["total_leads"] == 30
        assert data["converted_count"] == 3
        assert "avg_time_per_stage" in data
        assert "weekly_trend" in data


class TestWeeklyTrendAccuracy:
    """Test 11.7: Weekly trend data accuracy."""

    def test_metrics_include_weekly_trend(self, client):
        """GET /metrics includes weekly new vs converted data."""
        response = client.get("/api/pipeline/metrics")

        assert response.status_code == 200
        data = response.json()
        assert len(data["weekly_trend"]) >= 1
        week = data["weekly_trend"][0]
        assert "week" in week
        assert "new_leads" in week
        assert "converted" in week
        assert week["new_leads"] == 5
        assert week["converted"] == 1
