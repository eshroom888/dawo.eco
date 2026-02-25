"""Report DTOs and Protocols (Story 6-10, Task 1).

Data transfer objects for on-demand violation report generation.
Includes frozen dataclasses for request/result/metadata and
runtime-checkable protocols for PDF generation and report storage.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True)
class ViolationReportRequest:
    """Request parameters for generating a violation report.

    Attributes:
        evidence_ids: Specific evidence record IDs to include (optional).
        competitor_name: Filter by competitor (optional).
        date_from: Start of date range filter (optional).
        date_to: End of date range filter (optional).
        template_type: Report template variant.
        report_title: Custom report title (optional).
        generated_by: Identity of the requesting actor.
    """

    evidence_ids: list[UUID] | None = None
    competitor_name: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    template_type: str = "standard"
    report_title: str | None = None
    generated_by: str = "operator"


@dataclass(frozen=True)
class ReportResult:
    """Result from a PDF report generation operation.

    Attributes:
        pdf_bytes: Raw PDF file bytes.
        report_id: Deterministic UUID derived from PDF content hash.
        filename: Suggested filename for download.
        page_count: Total pages in the PDF.
        evidence_count: Number of evidence records included.
        generated_at: Timestamp of generation.
        sha256_hash: SHA-256 hex digest of pdf_bytes.
        template_type: Template variant used.
    """

    pdf_bytes: bytes
    report_id: UUID
    filename: str
    page_count: int
    evidence_count: int
    generated_at: datetime
    sha256_hash: str
    template_type: str


@dataclass(frozen=True)
class ReportMetadata:
    """Metadata for a stored report (used in listings).

    Attributes:
        report_id: Unique report identifier.
        filename: Report filename.
        evidence_count: Number of evidence records included.
        competitor_name: Competitor filter used (None if unfiltered).
        template_type: Template variant used.
        generated_at: When the report was generated.
        sha256_hash: SHA-256 hex digest for integrity verification.
        page_count: Total pages in the PDF.
        file_size_bytes: File size on disk.
    """

    report_id: UUID
    filename: str
    evidence_count: int
    competitor_name: str | None
    template_type: str
    generated_at: datetime
    sha256_hash: str
    page_count: int
    file_size_bytes: int


@runtime_checkable
class PDFGeneratorProtocol(Protocol):
    """Protocol for PDF report generators.

    Implementations generate violation report PDFs from evidence data.
    """

    async def generate_report(
        self, request: ViolationReportRequest
    ) -> ReportResult:
        """Generate a PDF violation report.

        Args:
            request: Report generation parameters.

        Returns:
            ReportResult with PDF bytes and metadata.
        """
        ...


@runtime_checkable
class ReportStorageProtocol(Protocol):
    """Protocol for report file storage.

    Implementations handle saving, retrieving, and listing generated reports.
    """

    async def save_report(self, result: ReportResult) -> str:
        """Save a generated report to storage.

        Args:
            result: Report generation result.

        Returns:
            Relative file path where report was saved.
        """
        ...

    async def get_report(self, report_id: UUID) -> bytes | None:
        """Retrieve a report's PDF bytes by ID.

        Args:
            report_id: Report identifier.

        Returns:
            PDF bytes or None if not found.
        """
        ...

    async def list_reports(
        self, limit: int, offset: int
    ) -> tuple[list[ReportMetadata], int]:
        """List stored reports with pagination.

        Args:
            limit: Maximum reports to return.
            offset: Number of reports to skip.

        Returns:
            Tuple of (report metadata list, total count).
        """
        ...


__all__ = [
    "PDFGeneratorProtocol",
    "ReportMetadata",
    "ReportResult",
    "ReportStorageProtocol",
    "ViolationReportRequest",
]
