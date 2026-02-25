"""Tests for report DTOs and Protocols (Story 6-10, Task 1).

Validates frozen dataclasses, field types, and protocol conformance.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from teams.dawo.scanners.evidence_collection.report_schemas import (
    PDFGeneratorProtocol,
    ReportMetadata,
    ReportResult,
    ReportStorageProtocol,
    ViolationReportRequest,
)


class TestViolationReportRequest:
    """Tests for ViolationReportRequest frozen dataclass."""

    def test_create_with_defaults(self) -> None:
        """ViolationReportRequest can be created with only defaults."""
        request = ViolationReportRequest()
        assert request.evidence_ids is None
        assert request.competitor_name is None
        assert request.date_from is None
        assert request.date_to is None
        assert request.template_type == "standard"
        assert request.report_title is None
        assert request.generated_by == "operator"

    def test_create_with_evidence_ids(self) -> None:
        """ViolationReportRequest accepts evidence_ids list."""
        ids = [uuid4(), uuid4()]
        request = ViolationReportRequest(evidence_ids=ids)
        assert request.evidence_ids == ids

    def test_create_with_all_fields(self) -> None:
        """ViolationReportRequest accepts all fields."""
        ids = [uuid4()]
        now = datetime.now(UTC)
        request = ViolationReportRequest(
            evidence_ids=ids,
            competitor_name="TestCorp",
            date_from=now,
            date_to=now,
            template_type="mattilsynet",
            report_title="Test Report",
            generated_by="admin",
        )
        assert request.evidence_ids == ids
        assert request.competitor_name == "TestCorp"
        assert request.date_from == now
        assert request.date_to == now
        assert request.template_type == "mattilsynet"
        assert request.report_title == "Test Report"
        assert request.generated_by == "admin"

    def test_is_frozen(self) -> None:
        """ViolationReportRequest is immutable."""
        request = ViolationReportRequest()
        with pytest.raises(AttributeError):
            request.template_type = "legal"  # type: ignore[misc]


class TestReportResult:
    """Tests for ReportResult frozen dataclass."""

    def test_create_with_all_fields(self) -> None:
        """ReportResult stores all report output data."""
        report_id = uuid4()
        now = datetime.now(UTC)
        result = ReportResult(
            pdf_bytes=b"%PDF-1.4",
            report_id=report_id,
            filename="violation-report-2026-02.pdf",
            page_count=5,
            evidence_count=10,
            generated_at=now,
            sha256_hash="abc123" * 10,
            template_type="standard",
        )
        assert result.pdf_bytes == b"%PDF-1.4"
        assert result.report_id == report_id
        assert result.filename == "violation-report-2026-02.pdf"
        assert result.page_count == 5
        assert result.evidence_count == 10
        assert result.generated_at == now
        assert result.sha256_hash == "abc123" * 10
        assert result.template_type == "standard"

    def test_is_frozen(self) -> None:
        """ReportResult is immutable."""
        result = ReportResult(
            pdf_bytes=b"",
            report_id=uuid4(),
            filename="test.pdf",
            page_count=1,
            evidence_count=0,
            generated_at=datetime.now(UTC),
            sha256_hash="a" * 64,
            template_type="standard",
        )
        with pytest.raises(AttributeError):
            result.page_count = 10  # type: ignore[misc]


class TestReportMetadata:
    """Tests for ReportMetadata frozen dataclass."""

    def test_create_with_all_fields(self) -> None:
        """ReportMetadata stores report listing data."""
        report_id = uuid4()
        now = datetime.now(UTC)
        meta = ReportMetadata(
            report_id=report_id,
            filename="report.pdf",
            evidence_count=5,
            competitor_name="TestCorp",
            template_type="legal",
            generated_at=now,
            sha256_hash="b" * 64,
            page_count=3,
            file_size_bytes=12345,
        )
        assert meta.report_id == report_id
        assert meta.filename == "report.pdf"
        assert meta.evidence_count == 5
        assert meta.competitor_name == "TestCorp"
        assert meta.template_type == "legal"
        assert meta.generated_at == now
        assert meta.sha256_hash == "b" * 64
        assert meta.page_count == 3
        assert meta.file_size_bytes == 12345

    def test_competitor_name_optional(self) -> None:
        """ReportMetadata allows None competitor_name."""
        meta = ReportMetadata(
            report_id=uuid4(),
            filename="report.pdf",
            evidence_count=5,
            competitor_name=None,
            template_type="standard",
            generated_at=datetime.now(UTC),
            sha256_hash="c" * 64,
            page_count=2,
            file_size_bytes=5000,
        )
        assert meta.competitor_name is None

    def test_is_frozen(self) -> None:
        """ReportMetadata is immutable."""
        meta = ReportMetadata(
            report_id=uuid4(),
            filename="r.pdf",
            evidence_count=1,
            competitor_name=None,
            template_type="standard",
            generated_at=datetime.now(UTC),
            sha256_hash="d" * 64,
            page_count=1,
            file_size_bytes=100,
        )
        with pytest.raises(AttributeError):
            meta.filename = "other.pdf"  # type: ignore[misc]


class TestPDFGeneratorProtocol:
    """Tests for PDFGeneratorProtocol."""

    def test_is_runtime_checkable(self) -> None:
        """PDFGeneratorProtocol is runtime_checkable."""
        from typing import runtime_checkable

        assert hasattr(PDFGeneratorProtocol, "__protocol_attrs__") or hasattr(
            PDFGeneratorProtocol, "__abstractmethods__"
        )

    def test_conformance(self) -> None:
        """A class with generate_report method satisfies PDFGeneratorProtocol."""

        class FakeGenerator:
            async def generate_report(
                self, request: ViolationReportRequest
            ) -> ReportResult:
                ...

        assert isinstance(FakeGenerator(), PDFGeneratorProtocol)


class TestReportStorageProtocol:
    """Tests for ReportStorageProtocol."""

    def test_conformance(self) -> None:
        """A class with required methods satisfies ReportStorageProtocol."""

        class FakeStorage:
            async def save_report(self, result: ReportResult) -> str:
                ...

            async def get_report(self, report_id: UUID) -> bytes | None:
                ...

            async def list_reports(
                self, limit: int, offset: int
            ) -> tuple[list[ReportMetadata], int]:
                ...

        assert isinstance(FakeStorage(), ReportStorageProtocol)

    def test_non_conformance(self) -> None:
        """A class missing methods does NOT satisfy ReportStorageProtocol."""

        class Incomplete:
            async def save_report(self, result: ReportResult) -> str:
                ...

        assert not isinstance(Incomplete(), ReportStorageProtocol)
