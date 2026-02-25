"""Tests for Pipeline API Pydantic schemas.

Story 5-5, Task 1/9.22: Validates all pipeline request/response schemas
serialize correctly and enforce validation rules.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC


class TestPipelineLeadSchema:
    """Test PipelineLeadSchema serialization and validation."""

    def test_create_with_valid_data(self, sample_lead_data):
        """PipelineLeadSchema accepts valid lead data."""
        from ui.backend.schemas.pipeline import PipelineLeadSchema

        schema = PipelineLeadSchema(**sample_lead_data)
        assert schema.email == "jane@example.com"
        assert schema.company == "EcoCorp"
        assert schema.status == "contacted"
        assert schema.score == 85.5
        assert schema.needs_followup is False

    def test_serialization_round_trip(self, sample_lead_data):
        """PipelineLeadSchema serializes to dict and back."""
        from ui.backend.schemas.pipeline import PipelineLeadSchema

        schema = PipelineLeadSchema(**sample_lead_data)
        data = schema.model_dump()
        restored = PipelineLeadSchema(**data)
        assert restored.id == schema.id
        assert restored.email == schema.email

    def test_optional_fields_default_none(self, sample_lead_data):
        """Optional fields default to None when not provided."""
        from ui.backend.schemas.pipeline import PipelineLeadSchema

        minimal = {
            "id": sample_lead_data["id"],
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "company": "TestCo",
            "status": "new",
            "source": "linkedin",
            "score": 0.0,
            "needs_followup": False,
            "contact_count": 0,
            "created_at": sample_lead_data["created_at"],
        }
        schema = PipelineLeadSchema(**minimal)
        assert schema.last_contacted_at is None
        assert schema.days_since_contact is None
        assert schema.job_title is None

    def test_json_serialization(self, sample_lead_data):
        """PipelineLeadSchema serializes to JSON string."""
        from ui.backend.schemas.pipeline import PipelineLeadSchema

        schema = PipelineLeadSchema(**sample_lead_data)
        json_str = schema.model_dump_json()
        assert "jane@example.com" in json_str
        assert "EcoCorp" in json_str


class TestPipelineSummarySchema:
    """Test PipelineSummarySchema serialization."""

    def test_create_with_valid_data(self, sample_pipeline_summary_data):
        """PipelineSummarySchema accepts valid summary data."""
        from ui.backend.schemas.pipeline import PipelineSummarySchema

        schema = PipelineSummarySchema(**sample_pipeline_summary_data)
        assert schema.total_leads == 18
        assert schema.conversion_rate == 5.56
        assert schema.followup_count == 2
        assert schema.status_counts["new"] == 5

    def test_status_counts_includes_all_statuses(self, sample_pipeline_summary_data):
        """Status counts dict includes all pipeline statuses."""
        from ui.backend.schemas.pipeline import PipelineSummarySchema

        schema = PipelineSummarySchema(**sample_pipeline_summary_data)
        expected_statuses = {
            "new", "researching", "qualified", "outreach_pending",
            "contacted", "replied", "meeting_scheduled", "negotiating",
            "converted", "lost", "nurture",
        }
        assert set(schema.status_counts.keys()) == expected_statuses

    def test_serialization_round_trip(self, sample_pipeline_summary_data):
        """PipelineSummarySchema serializes to dict and back."""
        from ui.backend.schemas.pipeline import PipelineSummarySchema

        schema = PipelineSummarySchema(**sample_pipeline_summary_data)
        data = schema.model_dump()
        restored = PipelineSummarySchema(**data)
        assert restored.total_leads == schema.total_leads


class TestPipelineLeadListResponse:
    """Test PipelineLeadListResponse pagination schema."""

    def test_empty_list(self):
        """PipelineLeadListResponse handles empty leads list."""
        from ui.backend.schemas.pipeline import PipelineLeadListResponse

        schema = PipelineLeadListResponse(
            leads=[],
            total_count=0,
            has_more=False,
        )
        assert len(schema.leads) == 0
        assert schema.total_count == 0
        assert schema.has_more is False
        assert schema.next_cursor is None

    def test_with_leads_and_cursor(self, sample_lead_data):
        """PipelineLeadListResponse with leads and pagination cursor."""
        from ui.backend.schemas.pipeline import (
            PipelineLeadListResponse,
            PipelineLeadSchema,
        )

        lead = PipelineLeadSchema(**sample_lead_data)
        schema = PipelineLeadListResponse(
            leads=[lead],
            total_count=25,
            has_more=True,
            next_cursor="offset:1",
        )
        assert len(schema.leads) == 1
        assert schema.total_count == 25
        assert schema.has_more is True
        assert schema.next_cursor == "offset:1"


class TestLeadHistoryEntrySchema:
    """Test LeadHistoryEntrySchema serialization."""

    def test_create_with_valid_data(self, sample_history_entry_data):
        """LeadHistoryEntrySchema accepts valid entry data."""
        from ui.backend.schemas.pipeline import LeadHistoryEntrySchema

        schema = LeadHistoryEntrySchema(**sample_history_entry_data)
        assert schema.activity_type == "status_change"
        assert schema.actor == "system"
        assert schema.metadata["old_status"] == "new"

    def test_optional_metadata(self, sample_history_entry_data):
        """LeadHistoryEntrySchema works without metadata."""
        from ui.backend.schemas.pipeline import LeadHistoryEntrySchema

        data = dict(sample_history_entry_data)
        data["metadata"] = None
        schema = LeadHistoryEntrySchema(**data)
        assert schema.metadata is None

    def test_serialization_round_trip(self, sample_history_entry_data):
        """LeadHistoryEntrySchema serializes to dict and back."""
        from ui.backend.schemas.pipeline import LeadHistoryEntrySchema

        schema = LeadHistoryEntrySchema(**sample_history_entry_data)
        data = schema.model_dump()
        restored = LeadHistoryEntrySchema(**data)
        assert restored.activity_type == schema.activity_type


class TestLeadHistoryResponse:
    """Test LeadHistoryResponse schema."""

    def test_empty_entries(self):
        """LeadHistoryResponse handles empty entries."""
        from ui.backend.schemas.pipeline import LeadHistoryResponse

        schema = LeadHistoryResponse(entries=[])
        assert len(schema.entries) == 0

    def test_with_entries(self, sample_history_entry_data):
        """LeadHistoryResponse with entries."""
        from ui.backend.schemas.pipeline import (
            LeadHistoryResponse,
            LeadHistoryEntrySchema,
        )

        entry = LeadHistoryEntrySchema(**sample_history_entry_data)
        schema = LeadHistoryResponse(entries=[entry])
        assert len(schema.entries) == 1


class TestStatusUpdateRequest:
    """Test StatusUpdateRequest schema."""

    def test_create_with_status_only(self):
        """StatusUpdateRequest with just new_status."""
        from ui.backend.schemas.pipeline import StatusUpdateRequest

        schema = StatusUpdateRequest(new_status="replied")
        assert schema.new_status == "replied"
        assert schema.reason is None
        assert schema.note is None

    def test_create_with_all_fields(self):
        """StatusUpdateRequest with reason and note."""
        from ui.backend.schemas.pipeline import StatusUpdateRequest

        schema = StatusUpdateRequest(
            new_status="lost",
            reason="No budget",
            note="Revisit in Q3",
        )
        assert schema.new_status == "lost"
        assert schema.reason == "No budget"
        assert schema.note == "Revisit in Q3"


class TestStatusUpdateResponse:
    """Test StatusUpdateResponse schema."""

    def test_create_response(self, sample_lead_data):
        """StatusUpdateResponse wraps lead data with success flag."""
        from ui.backend.schemas.pipeline import (
            StatusUpdateResponse,
            PipelineLeadSchema,
        )

        lead = PipelineLeadSchema(**sample_lead_data)
        schema = StatusUpdateResponse(
            success=True,
            lead=lead,
            message="Status updated to contacted",
        )
        assert schema.success is True
        assert schema.lead.email == "jane@example.com"
        assert "contacted" in schema.message


class TestPipelineMetricsSchema:
    """Test PipelineMetricsSchema serialization."""

    def test_create_with_valid_data(self, sample_metrics_data):
        """PipelineMetricsSchema accepts valid metrics data."""
        from ui.backend.schemas.pipeline import PipelineMetricsSchema

        schema = PipelineMetricsSchema(**sample_metrics_data)
        assert schema.conversion_rate == 12.5
        assert schema.total_leads == 40
        assert schema.converted_count == 5
        assert len(schema.weekly_trend) == 3

    def test_avg_time_per_stage_dict(self, sample_metrics_data):
        """avg_time_per_stage is a dict of stage name to avg days."""
        from ui.backend.schemas.pipeline import PipelineMetricsSchema

        schema = PipelineMetricsSchema(**sample_metrics_data)
        assert schema.avg_time_per_stage["new"] == 2.5
        assert schema.avg_time_per_stage["contacted"] == 5.5

    def test_weekly_trend_entries(self, sample_metrics_data):
        """Weekly trend entries have week, new_leads, and converted."""
        from ui.backend.schemas.pipeline import PipelineMetricsSchema

        schema = PipelineMetricsSchema(**sample_metrics_data)
        entry = schema.weekly_trend[0]
        assert entry["week"] == "2026-W04"
        assert entry["new_leads"] == 5
        assert entry["converted"] == 1

    def test_serialization_round_trip(self, sample_metrics_data):
        """PipelineMetricsSchema serializes to dict and back."""
        from ui.backend.schemas.pipeline import PipelineMetricsSchema

        schema = PipelineMetricsSchema(**sample_metrics_data)
        data = schema.model_dump()
        restored = PipelineMetricsSchema(**data)
        assert restored.conversion_rate == schema.conversion_rate


class TestLeadDetailSchema:
    """Test LeadDetailSchema with full lead data."""

    def test_create_with_full_data(self, sample_lead_detail_data):
        """LeadDetailSchema accepts full lead detail data."""
        from ui.backend.schemas.pipeline import LeadDetailSchema

        schema = LeadDetailSchema(**sample_lead_detail_data)
        assert schema.linkedin_url == "https://linkedin.com/in/janedoe"
        assert schema.country == "Norway"
        assert schema.industry == "Health & Wellness"
        assert schema.enrichment_data == {"revenue": "1M-5M"}
        assert schema.tags == ["eco", "b2b"]

    def test_serialization_round_trip(self, sample_lead_detail_data):
        """LeadDetailSchema serializes to dict and back."""
        from ui.backend.schemas.pipeline import LeadDetailSchema

        schema = LeadDetailSchema(**sample_lead_detail_data)
        data = schema.model_dump()
        restored = LeadDetailSchema(**data)
        assert restored.company == schema.company
        assert restored.enrichment_data == schema.enrichment_data


class TestAddNoteRequest:
    """Test AddNoteRequest schema."""

    def test_create_with_note(self):
        """AddNoteRequest accepts note text."""
        from ui.backend.schemas.pipeline import AddNoteRequest

        schema = AddNoteRequest(note="Follow up next week")
        assert schema.note == "Follow up next week"

    def test_note_required(self):
        """AddNoteRequest requires note field."""
        from ui.backend.schemas.pipeline import AddNoteRequest

        with pytest.raises(Exception):
            AddNoteRequest()


class TestAllExports:
    """Test that __all__ exports are complete."""

    def test_all_schemas_exported(self):
        """All schema classes are in __all__."""
        from ui.backend.schemas import pipeline

        expected = {
            "PipelineLeadSchema",
            "PipelineSummarySchema",
            "PipelineLeadListResponse",
            "LeadHistoryEntrySchema",
            "LeadHistoryResponse",
            "StatusUpdateRequest",
            "StatusUpdateResponse",
            "PipelineMetricsSchema",
            "LeadDetailSchema",
            "AddNoteRequest",
        }
        assert expected.issubset(set(pipeline.__all__))
