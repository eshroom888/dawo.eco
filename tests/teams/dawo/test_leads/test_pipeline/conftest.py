"""Shared fixtures for pipeline tests.

Provides mock objects, sample data, and test helpers for
the lead pipeline status tracking test suite.
"""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest


@pytest.fixture
def sample_lead_id():
    """Generate a sample lead UUID."""
    return uuid4()


@pytest.fixture
def sample_datetime():
    """Generate a sample datetime."""
    return datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_pipeline_summary_data():
    """Sample data for PipelineSummarySchema."""
    return {
        "total_leads": 18,
        "status_counts": {
            "new": 5,
            "researching": 2,
            "qualified": 3,
            "outreach_pending": 2,
            "contacted": 4,
            "replied": 1,
            "meeting_scheduled": 0,
            "negotiating": 0,
            "converted": 1,
            "lost": 0,
            "nurture": 0,
        },
        "conversion_rate": 5.56,
        "avg_days_in_pipeline": 14.5,
        "followup_count": 2,
    }


@pytest.fixture
def sample_lead_data(sample_lead_id, sample_datetime):
    """Sample data for PipelineLeadSchema."""
    return {
        "id": str(sample_lead_id),
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "company": "EcoCorp",
        "job_title": "Marketing Director",
        "status": "contacted",
        "source": "linkedin",
        "score": 85.5,
        "last_contacted_at": sample_datetime.isoformat(),
        "days_since_contact": 3,
        "needs_followup": False,
        "contact_count": 1,
        "created_at": (sample_datetime - timedelta(days=10)).isoformat(),
    }


@pytest.fixture
def sample_history_entry_data(sample_lead_id, sample_datetime):
    """Sample data for LeadHistoryEntrySchema."""
    return {
        "id": str(uuid4()),
        "lead_id": str(sample_lead_id),
        "activity_type": "status_change",
        "description": "Status changed from new to contacted",
        "timestamp": sample_datetime.isoformat(),
        "actor": "system",
        "metadata": {"old_status": "new", "new_status": "contacted"},
    }


@pytest.fixture
def sample_metrics_data():
    """Sample data for PipelineMetricsSchema."""
    return {
        "conversion_rate": 12.5,
        "total_leads": 40,
        "converted_count": 5,
        "avg_time_per_stage": {
            "new": 2.5,
            "researching": 1.8,
            "qualified": 3.2,
            "outreach_pending": 1.0,
            "contacted": 5.5,
        },
        "weekly_trend": [
            {"week": "2026-W04", "new_leads": 5, "converted": 1},
            {"week": "2026-W05", "new_leads": 8, "converted": 2},
            {"week": "2026-W06", "new_leads": 3, "converted": 0},
        ],
    }


@pytest.fixture
def sample_lead_detail_data(sample_lead_data, sample_datetime):
    """Sample data for LeadDetailSchema."""
    data = dict(sample_lead_data)
    data.update({
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "website_url": "https://ecocorp.com",
        "phone": "+47 123 45 678",
        "country": "Norway",
        "industry": "Health & Wellness",
        "company_size": "11-50",
        "enrichment_data": {"revenue": "1M-5M"},
        "outreach_data": {"template": "intro_v2"},
        "tags": ["eco", "b2b"],
        "notes": "Met at conference",
        "assigned_to": "operator@dawo.eco",
        "next_followup_at": (sample_datetime + timedelta(days=7)).isoformat(),
        "converted_at": None,
        "lost_reason": None,
        "updated_at": sample_datetime.isoformat(),
        "activities": [],
        "emails": [],
    })
    return data
