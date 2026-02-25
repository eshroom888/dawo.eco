"""Tests for lead scanner schemas.

Epic 5: B2B Sales Pipeline
Story 5-1: B2B Lead Research Scanner
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from teams.dawo.leads.scanner.schemas import (
    RawLead,
    HarvestedLead,
    HarvestedContact,
    TransformedLead,
    ScanResult,
    PipelineResult,
    PipelineStatus,
    ScanStatistics,
)


class TestRawLead:
    """Tests for RawLead dataclass."""

    def test_raw_lead_creation(self) -> None:
        """Test basic raw lead creation."""
        lead = RawLead(
            domain="example.com",
            company_name="Example Inc",
            country="Norway",
            confidence=0.9,
        )

        assert lead.domain == "example.com"
        assert lead.company_name == "Example Inc"
        assert lead.country == "Norway"
        assert lead.confidence == 0.9
        assert lead.discovered_at is not None

    def test_domain_normalization_removes_protocol(self) -> None:
        """Test that domain normalization removes http/https."""
        lead = RawLead(domain="https://example.com")
        assert lead.domain == "example.com"

        lead = RawLead(domain="http://example.com")
        assert lead.domain == "example.com"

    def test_domain_normalization_removes_www(self) -> None:
        """Test that domain normalization removes www prefix."""
        lead = RawLead(domain="www.example.com")
        assert lead.domain == "example.com"

    def test_domain_normalization_removes_trailing_slash(self) -> None:
        """Test that domain normalization removes trailing slash."""
        lead = RawLead(domain="example.com/")
        assert lead.domain == "example.com"

    def test_domain_normalization_combined(self) -> None:
        """Test combined domain normalization."""
        lead = RawLead(domain="https://www.example.com/")
        assert lead.domain == "example.com"


class TestHarvestedContact:
    """Tests for HarvestedContact dataclass."""

    def test_contact_creation(self) -> None:
        """Test basic contact creation."""
        contact = HarvestedContact(
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            position="CEO",
            confidence=0.95,
        )

        assert contact.email == "john@example.com"
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.position == "CEO"
        assert contact.confidence == 0.95

    def test_contact_optional_fields(self) -> None:
        """Test contact with minimal fields."""
        contact = HarvestedContact(email="info@example.com")

        assert contact.email == "info@example.com"
        assert contact.first_name is None
        assert contact.last_name is None
        assert contact.confidence == 0.0


class TestHarvestedLead:
    """Tests for HarvestedLead dataclass."""

    def test_primary_contact_returns_highest_confidence(self) -> None:
        """Test that primary_contact returns highest confidence contact."""
        lead = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[
                HarvestedContact(email="low@example.com", confidence=0.5),
                HarvestedContact(email="high@example.com", confidence=0.95),
                HarvestedContact(email="mid@example.com", confidence=0.75),
            ],
        )

        primary = lead.primary_contact
        assert primary is not None
        assert primary.email == "high@example.com"
        assert primary.confidence == 0.95

    def test_primary_contact_returns_none_when_no_contacts(self) -> None:
        """Test that primary_contact returns None for empty contacts."""
        lead = HarvestedLead(
            domain="example.com",
            company_name="Example Inc",
            contacts=[],
        )

        assert lead.primary_contact is None


class TestTransformedLead:
    """Tests for TransformedLead dataclass."""

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        lead = TransformedLead(
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            company="Example Inc",
            job_title="CEO",
            country="Norway",
        )

        data = lead.to_dict()

        assert data["email"] == "john@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["company"] == "Example Inc"
        assert data["job_title"] == "CEO"
        assert data["country"] == "Norway"
        assert data["source"] == "cold_research"
        assert data["status"] == "new"


class TestScanStatistics:
    """Tests for ScanStatistics dataclass."""

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        stats = ScanStatistics(
            domains_searched=10,
            raw_leads_found=5,
            leads_harvested=4,
            leads_transformed=3,
            duplicates_found=1,
            leads_created=2,
            errors=1,
        )

        data = stats.to_dict()

        assert data["domains_searched"] == 10
        assert data["raw_leads_found"] == 5
        assert data["leads_created"] == 2
        assert data["errors"] == 1


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_duration_calculation(self) -> None:
        """Test duration_seconds calculation."""
        started = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 1, 10, 5, 30, tzinfo=UTC)

        result = PipelineResult(
            status=PipelineStatus.COMPLETE,
            started_at=started,
            completed_at=completed,
        )

        assert result.duration_seconds == 330.0  # 5 minutes 30 seconds

    def test_duration_none_when_not_completed(self) -> None:
        """Test duration is None when not completed."""
        result = PipelineResult(
            status=PipelineStatus.INCOMPLETE,
            completed_at=None,
        )

        # Need to manually set completed_at to None after creation
        result.completed_at = None
        assert result.duration_seconds is None

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        result = PipelineResult(
            status=PipelineStatus.COMPLETE,
            stats=ScanStatistics(leads_created=5),
            created_lead_ids=[uuid4(), uuid4()],
        )

        data = result.to_dict()

        assert data["status"] == "complete"
        assert data["stats"]["leads_created"] == 5
        assert len(data["created_lead_ids"]) == 2
        assert data["error"] is None


class TestPipelineStatus:
    """Tests for PipelineStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert PipelineStatus.COMPLETE.value == "complete"
        assert PipelineStatus.PARTIAL.value == "partial"
        assert PipelineStatus.INCOMPLETE.value == "incomplete"
        assert PipelineStatus.FAILED.value == "failed"
