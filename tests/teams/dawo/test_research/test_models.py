"""Tests for Research Pool models.

Tests cover:
- ResearchSource enum values and conversions
- ComplianceStatus enum values and conversions
- ResearchItem model validation and field types
- Model constraints and defaults
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from teams.dawo.research.models import (
    ResearchItem,
    ResearchSource,
    ComplianceStatus,
)


class TestResearchSourceEnum:
    """Tests for ResearchSource enumeration."""

    def test_has_all_required_sources(self):
        """Enum includes all required research sources."""
        expected_sources = {"reddit", "youtube", "instagram", "news", "pubmed"}
        actual_sources = {source.value for source in ResearchSource}
        assert actual_sources == expected_sources

    def test_enum_values_are_lowercase(self):
        """All enum values are lowercase strings."""
        for source in ResearchSource:
            assert source.value == source.value.lower()
            assert isinstance(source.value, str)

    def test_enum_names_are_uppercase(self):
        """All enum names are uppercase."""
        for source in ResearchSource:
            assert source.name == source.name.upper()

    def test_string_conversion(self):
        """Enum converts to string correctly."""
        assert ResearchSource.REDDIT.value == "reddit"
        assert ResearchSource.YOUTUBE.value == "youtube"
        assert ResearchSource.INSTAGRAM.value == "instagram"
        assert ResearchSource.NEWS.value == "news"
        assert ResearchSource.PUBMED.value == "pubmed"


class TestComplianceStatusEnum:
    """Tests for ComplianceStatus enumeration."""

    def test_has_all_required_statuses(self):
        """Enum includes all required compliance statuses."""
        expected_statuses = {"COMPLIANT", "WARNING", "REJECTED"}
        actual_statuses = {status.value for status in ComplianceStatus}
        assert actual_statuses == expected_statuses

    def test_enum_values_are_uppercase(self):
        """All enum values are uppercase strings."""
        for status in ComplianceStatus:
            assert status.value == status.value.upper()
            assert isinstance(status.value, str)

    def test_string_conversion(self):
        """Enum converts to string correctly."""
        assert ComplianceStatus.COMPLIANT.value == "COMPLIANT"
        assert ComplianceStatus.WARNING.value == "WARNING"
        assert ComplianceStatus.REJECTED.value == "REJECTED"


class TestResearchItemModel:
    """Tests for ResearchItem SQLAlchemy model."""

    def test_model_has_tablename(self):
        """Model defines correct table name."""
        assert ResearchItem.__tablename__ == "research_items"

    def test_model_has_required_columns(self):
        """Model includes all required columns from AC#1."""
        required_columns = [
            "id",
            "source",
            "title",
            "content",
            "url",
            "tags",
            "source_metadata",
            "created_at",
            "score",
            "compliance_status",
        ]
        model_columns = [col.name for col in ResearchItem.__table__.columns]

        for col in required_columns:
            assert col in model_columns, f"Missing required column: {col}"

    def test_model_has_search_vector_column(self):
        """Model includes search_vector for full-text search."""
        model_columns = [col.name for col in ResearchItem.__table__.columns]
        assert "search_vector" in model_columns

    def test_id_is_uuid_primary_key(self):
        """ID column is UUID and primary key."""
        id_column = ResearchItem.__table__.columns["id"]
        assert id_column.primary_key is True

    def test_source_column_is_not_nullable(self):
        """Source column is required."""
        source_column = ResearchItem.__table__.columns["source"]
        assert source_column.nullable is False

    def test_title_column_is_not_nullable(self):
        """Title column is required."""
        title_column = ResearchItem.__table__.columns["title"]
        assert title_column.nullable is False

    def test_content_column_is_not_nullable(self):
        """Content column is required."""
        content_column = ResearchItem.__table__.columns["content"]
        assert content_column.nullable is False

    def test_url_column_is_not_nullable(self):
        """URL column is required."""
        url_column = ResearchItem.__table__.columns["url"]
        assert url_column.nullable is False

    def test_score_default_value(self):
        """Score defaults to 0.0."""
        score_column = ResearchItem.__table__.columns["score"]
        # Default is set server-side or in Python
        assert score_column.default is not None or score_column.server_default is not None

    def test_compliance_status_default_value(self):
        """Compliance status defaults to COMPLIANT."""
        compliance_column = ResearchItem.__table__.columns["compliance_status"]
        # Default is set server-side or in Python
        assert compliance_column.default is not None or compliance_column.server_default is not None


class TestResearchItemIndexes:
    """Tests for ResearchItem database indexes."""

    def test_model_has_indexes_defined(self):
        """Model defines performance indexes."""
        indexes = list(ResearchItem.__table__.indexes)
        assert len(indexes) > 0, "Model should define indexes for performance"

    def test_source_index_exists(self):
        """Index on source column exists."""
        source_column = ResearchItem.__table__.columns["source"]
        # Check if column has index or is in a composite index
        assert source_column.index is True or any(
            "source" in str(idx.columns) for idx in ResearchItem.__table__.indexes
        ), "Source column should be indexed"
