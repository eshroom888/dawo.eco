"""Tests for Approval database models.

Tests model configuration, enums, and table structure.
"""

import pytest

from core.approval.models import (
    ApprovalItem,
    ApprovalItemEdit,
    ApprovalStatus,
    SourcePriority,
    ComplianceStatus,
    RejectReasonType,
)


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_status_values(self):
        """Test approval status enum values."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        # Story 4-5 added: SCHEDULED, PUBLISHING, PUBLISHED, PUBLISH_FAILED
        statuses = list(ApprovalStatus)
        assert len(statuses) == 7


class TestSourcePriority:
    """Tests for SourcePriority enum."""

    def test_priority_values(self):
        """Test source priority enum values."""
        assert SourcePriority.TRENDING == 1
        assert SourcePriority.SCHEDULED == 2
        assert SourcePriority.EVERGREEN == 3
        assert SourcePriority.RESEARCH == 4

    def test_priority_ordering(self):
        """Test priority values are in correct order."""
        assert SourcePriority.TRENDING < SourcePriority.SCHEDULED
        assert SourcePriority.SCHEDULED < SourcePriority.EVERGREEN
        assert SourcePriority.EVERGREEN < SourcePriority.RESEARCH

    def test_can_sort_by_priority(self):
        """Test priorities can be sorted."""
        priorities = [
            SourcePriority.RESEARCH,
            SourcePriority.TRENDING,
            SourcePriority.EVERGREEN,
            SourcePriority.SCHEDULED,
        ]
        sorted_priorities = sorted(priorities)
        assert sorted_priorities == [
            SourcePriority.TRENDING,
            SourcePriority.SCHEDULED,
            SourcePriority.EVERGREEN,
            SourcePriority.RESEARCH,
        ]


class TestComplianceStatus:
    """Tests for ComplianceStatus enum."""

    def test_status_values(self):
        """Test compliance status enum values."""
        assert ComplianceStatus.COMPLIANT.value == "COMPLIANT"
        assert ComplianceStatus.WARNING.value == "WARNING"
        assert ComplianceStatus.REJECTED.value == "REJECTED"


class TestApprovalItemModel:
    """Tests for ApprovalItem model configuration."""

    def test_tablename(self):
        """Test table name is correct."""
        assert ApprovalItem.__tablename__ == "approval_items"

    def test_model_has_required_columns(self):
        """Test model has all required columns."""
        columns = ApprovalItem.__table__.columns.keys()

        required_columns = [
            "id",
            "thumbnail_url",
            "full_caption",
            "hashtags",
            "quality_score",
            "compliance_status",
            "compliance_details",
            "quality_breakdown",
            "would_auto_publish",
            "suggested_publish_time",
            "source_type",
            "source_priority",
            "status",
            "created_at",
            "updated_at",
        ]

        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_model_has_indexes(self):
        """Test model has performance indexes."""
        indexes = {idx.name for idx in ApprovalItem.__table__.indexes}

        # Check for queue composite index
        assert "idx_approval_items_queue" in indexes
        # Check for priority index
        assert "idx_approval_items_priority" in indexes

    def test_source_priority_default(self):
        """Test source_priority default is EVERGREEN (3)."""
        col = ApprovalItem.__table__.columns["source_priority"]
        assert col.default.arg == SourcePriority.EVERGREEN.value

    def test_status_default(self):
        """Test status default is PENDING."""
        col = ApprovalItem.__table__.columns["status"]
        assert col.default.arg == ApprovalStatus.PENDING.value

    def test_would_auto_publish_default(self):
        """Test would_auto_publish default is False."""
        col = ApprovalItem.__table__.columns["would_auto_publish"]
        assert col.default.arg is False

    def test_repr(self):
        """Test model repr string format."""
        item = ApprovalItem()
        item.id = "test-uuid"
        item.source_type = "instagram_post"
        item.status = "pending"
        item.source_priority = 1

        repr_str = repr(item)
        assert "ApprovalItem" in repr_str
        assert "instagram_post" in repr_str
        assert "pending" in repr_str

    def test_model_has_story_42_columns(self):
        """Test model has Story 4-2 action columns."""
        columns = ApprovalItem.__table__.columns.keys()

        story_42_columns = [
            "original_caption",
            "rewrite_suggestions",
            "rejection_reason",
            "rejection_text",
            "archived_at",
            "approved_at",
            "approved_by",
            "scheduled_publish_time",
        ]

        for col in story_42_columns:
            assert col in columns, f"Missing Story 4-2 column: {col}"

    def test_edits_relationship(self):
        """Test ApprovalItem has edits relationship."""
        assert hasattr(ApprovalItem, "edits")


class TestApprovalItemEditModel:
    """Tests for ApprovalItemEdit model (Story 4-2 edit history)."""

    def test_tablename(self):
        """Test table name is correct."""
        assert ApprovalItemEdit.__tablename__ == "approval_item_edits"

    def test_model_has_required_columns(self):
        """Test model has all required columns."""
        columns = ApprovalItemEdit.__table__.columns.keys()

        required_columns = [
            "id",
            "item_id",
            "previous_caption",
            "new_caption",
            "edited_at",
            "editor",
        ]

        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    def test_item_id_has_index(self):
        """Test item_id column is indexed for efficient lookups."""
        col = ApprovalItemEdit.__table__.columns["item_id"]
        assert col.index is True

    def test_editor_default(self):
        """Test editor default is 'operator'."""
        col = ApprovalItemEdit.__table__.columns["editor"]
        assert col.default.arg == "operator"

    def test_item_relationship(self):
        """Test ApprovalItemEdit has item relationship."""
        assert hasattr(ApprovalItemEdit, "item")

    def test_repr(self):
        """Test model repr string format."""
        edit = ApprovalItemEdit()
        edit.id = "edit-uuid"
        edit.item_id = "item-uuid"
        edit.editor = "operator"
        edit.edited_at = None

        repr_str = repr(edit)
        assert "ApprovalItemEdit" in repr_str
        assert "operator" in repr_str


class TestRejectReasonType:
    """Tests for RejectReasonType enum (Story 4-2)."""

    def test_reason_values(self):
        """Test rejection reason enum values."""
        assert RejectReasonType.COMPLIANCE_ISSUE.value == "compliance_issue"
        assert RejectReasonType.BRAND_VOICE_MISMATCH.value == "brand_voice_mismatch"
        assert RejectReasonType.LOW_QUALITY.value == "low_quality"
        assert RejectReasonType.IRRELEVANT_CONTENT.value == "irrelevant_content"
        assert RejectReasonType.DUPLICATE_CONTENT.value == "duplicate_content"
        assert RejectReasonType.OTHER.value == "other"

    def test_all_reasons_defined(self):
        """Test all expected reasons are defined."""
        reasons = list(RejectReasonType)
        assert len(reasons) == 6

    def test_reasons_are_strings(self):
        """Test all reasons are string enums."""
        for reason in RejectReasonType:
            assert isinstance(reason.value, str)
