"""Tests for Pipeline FastAPI router.

Story 5-5, Task 10: Tests all pipeline API endpoints
using FastAPI TestClient with mocked dependencies.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.leads.models import Lead, LeadActivity, LeadStatus, ActivityType
from teams.dawo.leads.pipeline.schemas import (
    PipelineSummary,
    ConversionMetrics,
    FollowUpCandidate,
)
from ui.backend.routers.pipeline import router, get_db_session, get_repository, get_pipeline_service, get_csv_exporter


@pytest.fixture
def mock_repo():
    """Create mock LeadRepository."""
    return AsyncMock()


@pytest.fixture
def mock_service():
    """Create mock PipelineService."""
    return AsyncMock()


@pytest.fixture
def mock_exporter():
    """Create mock CSVExporter."""
    return AsyncMock()


@pytest.fixture
def sample_lead():
    """Create a sample Lead mock."""
    lead = MagicMock(spec=Lead)
    lead.id = uuid4()
    lead.email = "jane@ecocorp.com"
    lead.first_name = "Jane"
    lead.last_name = "Doe"
    lead.company = "EcoCorp"
    lead.job_title = "Marketing Director"
    lead.status = "contacted"
    lead.source = "linkedin"
    lead.score = 85.5
    lead.last_contacted_at = datetime(2026, 2, 5, tzinfo=UTC)
    lead.contact_count = 1
    lead.created_at = datetime(2026, 1, 15, tzinfo=UTC)
    lead.updated_at = datetime(2026, 2, 5, tzinfo=UTC)
    lead.linkedin_url = "https://linkedin.com/in/janedoe"
    lead.website_url = "https://ecocorp.com"
    lead.phone = None
    lead.country = "Norway"
    lead.industry = "Health & Wellness"
    lead.company_size = "11-50"
    lead.enrichment_data = None
    lead.outreach_data = None
    lead.tags = ["eco"]
    lead.notes = None
    lead.assigned_to = None
    lead.next_followup_at = None
    lead.converted_at = None
    lead.lost_reason = None
    lead.activities = []
    lead.emails = []
    return lead


@pytest.fixture
def app(mock_repo, mock_service, mock_exporter):
    """Create FastAPI test app with overridden dependencies."""
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_repository] = lambda: mock_repo
    app.dependency_overrides[get_pipeline_service] = lambda: mock_service
    app.dependency_overrides[get_csv_exporter] = lambda: mock_exporter

    return app


@pytest.fixture
def client(app):
    """Create TestClient."""
    return TestClient(app)


class TestGetSummary:
    """Tests for GET /api/pipeline/summary."""

    def test_returns_summary(self, client, mock_service):
        """GET /summary returns pipeline summary."""
        mock_service.get_dashboard_summary = AsyncMock(return_value=PipelineSummary(
            total_leads=18,
            status_counts={"new": 5, "contacted": 4, "converted": 1},
            conversion_rate=5.56,
            avg_days_in_pipeline=14.5,
            followup_count=2,
        ))

        response = client.get("/api/pipeline/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_leads"] == 18
        assert data["conversion_rate"] == 5.56
        assert data["followup_count"] == 2


class TestGetMetrics:
    """Tests for GET /api/pipeline/metrics."""

    def test_returns_metrics(self, client, mock_service):
        """GET /metrics returns conversion data."""
        mock_service.get_metrics = AsyncMock(return_value=ConversionMetrics(
            conversion_rate=12.5,
            total_leads=40,
            converted_count=5,
            avg_time_per_stage={"new": 2.5},
            weekly_trend=[{"week": "2026-W06", "new_leads": 3, "converted": 1}],
        ))

        response = client.get("/api/pipeline/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["conversion_rate"] == 12.5
        assert data["total_leads"] == 40


class TestGetLeads:
    """Tests for GET /api/pipeline/leads."""

    def test_pagination(self, client, mock_repo, sample_lead):
        """GET /leads returns paginated results."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        response = client.get("/api/pipeline/leads?limit=25&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["leads"]) == 1
        assert data["has_more"] is False

    def test_search_filter(self, client, mock_repo, sample_lead):
        """GET /leads supports search parameter."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        response = client.get("/api/pipeline/leads?search=EcoCorp")

        assert response.status_code == 200

    def test_status_filter(self, client, mock_repo, sample_lead):
        """GET /leads supports status filter."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        response = client.get("/api/pipeline/leads?status=contacted")

        assert response.status_code == 200


class TestGetLeadDetail:
    """Tests for GET /api/pipeline/leads/{lead_id}."""

    def test_returns_full_detail(self, client, mock_repo, sample_lead):
        """GET /leads/{id} returns full lead detail."""
        mock_repo.get_lead_with_relations = AsyncMock(return_value=sample_lead)

        response = client.get(f"/api/pipeline/leads/{sample_lead.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "jane@ecocorp.com"
        assert data["company"] == "EcoCorp"

    def test_404_for_unknown_lead(self, client, mock_repo):
        """GET /leads/{id} returns 404 for unknown lead."""
        mock_repo.get_lead_with_relations = AsyncMock(return_value=None)

        response = client.get(f"/api/pipeline/leads/{uuid4()}")

        assert response.status_code == 404


class TestGetLeadHistory:
    """Tests for GET /api/pipeline/leads/{lead_id}/history."""

    def test_returns_activities(self, client, mock_repo):
        """GET /leads/{id}/history returns activity log."""
        activity = MagicMock(spec=LeadActivity)
        activity.id = uuid4()
        activity.lead_id = uuid4()
        activity.activity_type = "status_change"
        activity.description = "Status changed"
        activity.created_at = datetime(2026, 2, 5, tzinfo=UTC)
        activity.created_by = "system"
        activity.activity_metadata = {"old_status": "new"}

        mock_repo.get_lead_activities = AsyncMock(return_value=[activity])

        response = client.get(f"/api/pipeline/leads/{activity.lead_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1


class TestUpdateLeadStatus:
    """Tests for POST /api/pipeline/leads/{lead_id}/status."""

    def test_valid_transition(self, client, mock_service, sample_lead):
        """POST /leads/{id}/status succeeds for valid transition."""
        mock_service.update_lead_status = AsyncMock(return_value=sample_lead)

        response = client.post(
            f"/api/pipeline/leads/{sample_lead.id}/status",
            json={"new_status": "replied"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_invalid_transition_returns_422(self, client, mock_service, sample_lead):
        """POST /leads/{id}/status returns 422 for invalid transition."""
        mock_service.update_lead_status = AsyncMock(
            side_effect=ValueError("Invalid transition from converted to new")
        )

        response = client.post(
            f"/api/pipeline/leads/{sample_lead.id}/status",
            json={"new_status": "new"},
        )

        assert response.status_code == 422


class TestAddNote:
    """Tests for POST /api/pipeline/leads/{lead_id}/note."""

    def test_creates_activity(self, client, mock_service):
        """POST /leads/{id}/note creates note activity."""
        activity = MagicMock(spec=LeadActivity)
        activity.id = uuid4()
        activity.lead_id = uuid4()
        activity.activity_type = ActivityType.NOTE_ADDED.value
        activity.description = "Follow up next week"
        activity.created_at = datetime.now(UTC)
        activity.created_by = "operator"
        activity.activity_metadata = {}

        mock_service.add_note = AsyncMock(return_value=activity)

        response = client.post(
            f"/api/pipeline/leads/{activity.lead_id}/note",
            json={"note": "Follow up next week"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["activity_type"] == "note_added"


class TestGetFollowups:
    """Tests for GET /api/pipeline/followups."""

    def test_returns_flagged_leads(self, client, mock_service, mock_repo, sample_lead):
        """GET /followups returns leads needing follow-up."""
        mock_service.detect_followups = AsyncMock(return_value=[
            FollowUpCandidate(
                lead_id=sample_lead.id,
                email="jane@ecocorp.com",
                company="EcoCorp",
                days_since_contact=10,
                last_contacted_at=datetime(2026, 2, 1, tzinfo=UTC),
            ),
        ])
        mock_repo.get_leads_by_ids = AsyncMock(return_value=[sample_lead])

        response = client.get("/api/pipeline/followups")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["needs_followup"] is True


class TestExportCSV:
    """Tests for GET /api/pipeline/export."""

    def test_returns_csv_content_type(self, client, mock_exporter):
        """GET /export returns CSV with correct Content-Type."""
        mock_exporter.export_leads = AsyncMock(
            return_value="id,email,company\n1,test@test.com,TestCo\n"
        )

        response = client.get("/api/pipeline/export")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers

    def test_with_status_filter(self, client, mock_exporter):
        """GET /export respects status filter."""
        mock_exporter.export_leads = AsyncMock(return_value="id,email\n")

        response = client.get("/api/pipeline/export?status=contacted")

        assert response.status_code == 200
        mock_exporter.export_leads.assert_called_once()
