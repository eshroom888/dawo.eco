"""Tests for CSVExporter.

Story 5-5, Task 4/9.10-9.13: Tests CSV export generation
with mocked LeadRepository.
"""

import csv
import io
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.leads.models import Lead, LeadActivity, LeadStatus, ActivityType


@pytest.fixture
def mock_repo():
    """Create mock LeadRepository."""
    return AsyncMock()


@pytest.fixture
def sample_lead():
    """Create a sample lead mock."""
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
    lead.country = "Norway"
    lead.industry = "Health & Wellness"
    lead.created_at = datetime(2026, 1, 15, tzinfo=UTC)
    lead.last_contacted_at = datetime(2026, 2, 5, tzinfo=UTC)
    lead.contact_count = 1
    lead.converted_at = None
    lead.lost_reason = None
    return lead


@pytest.fixture
def exporter(mock_repo):
    """Create CSVExporter with mock repository."""
    from teams.dawo.leads.pipeline.csv_export import CSVExporter
    return CSVExporter(mock_repo)


class TestCSVExporterExportLeads:
    """Tests for CSVExporter.export_leads()."""

    async def test_generates_valid_csv_with_headers(self, exporter, mock_repo, sample_lead):
        """export_leads generates CSV string with correct headers."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        csv_content = await exporter.export_leads()

        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        assert "id" in headers
        assert "email" in headers
        assert "company" in headers
        assert "status" in headers
        assert "score" in headers

    async def test_csv_contains_lead_data(self, exporter, mock_repo, sample_lead):
        """export_leads includes lead data in rows."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        csv_content = await exporter.export_leads()

        assert "jane@ecocorp.com" in csv_content
        assert "EcoCorp" in csv_content
        assert "contacted" in csv_content

    async def test_respects_status_filter(self, exporter, mock_repo, sample_lead):
        """export_leads passes status filter to repository."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        await exporter.export_leads(status_filter=LeadStatus.CONTACTED)

        call_args = mock_repo.get_leads_filtered.call_args
        assert call_args[1]["status"] == LeadStatus.CONTACTED

    async def test_respects_date_range_filter(self, exporter, mock_repo, sample_lead):
        """export_leads passes date range filter to repository."""
        date_from = datetime(2026, 1, 1, tzinfo=UTC)
        date_to = datetime(2026, 2, 1, tzinfo=UTC)
        mock_repo.get_leads_filtered = AsyncMock(return_value=([sample_lead], 1))

        csv_content = await exporter.export_leads(
            date_from=date_from, date_to=date_to
        )

        assert csv_content  # Should still produce output

    async def test_empty_leads_returns_headers_only(self, exporter, mock_repo):
        """export_leads returns headers even with no leads."""
        mock_repo.get_leads_filtered = AsyncMock(return_value=([], 0))

        csv_content = await exporter.export_leads()

        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        assert len(headers) > 0
        # No data rows
        rows = list(reader)
        assert len(rows) == 0


class TestCSVExporterExportLeadHistory:
    """Tests for CSVExporter.export_lead_history()."""

    async def test_includes_all_activities(self, exporter, mock_repo):
        """export_lead_history includes all activity entries."""
        lead_id = uuid4()
        activities = []
        for i in range(3):
            act = MagicMock(spec=LeadActivity)
            act.id = uuid4()
            act.activity_type = ActivityType.STATUS_CHANGE.value
            act.description = f"Activity {i}"
            act.created_at = datetime(2026, 2, 1 + i, tzinfo=UTC)
            act.created_by = "system"
            act.activity_metadata = {"old_status": "new", "new_status": "contacted"}
            activities.append(act)

        mock_repo.get_lead_activities = AsyncMock(return_value=activities)

        csv_content = await exporter.export_lead_history(lead_id)

        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        rows = list(reader)
        assert len(rows) == 3
        assert "activity_type" in headers

    async def test_empty_history_returns_headers(self, exporter, mock_repo):
        """export_lead_history returns headers even with no activities."""
        mock_repo.get_lead_activities = AsyncMock(return_value=[])

        csv_content = await exporter.export_lead_history(uuid4())

        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        assert "activity_type" in headers
        rows = list(reader)
        assert len(rows) == 0
