"""Integration tests for Violation Reports pipeline (Story 6-10, Task 16).

Tests end-to-end flows: evidence -> report generation -> storage -> retrieval.
Uses mock WeasyPrint but real storage, config, and schemas.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
)
from teams.dawo.scanners.evidence_collection.report_schemas import (
    ReportResult,
    ViolationReportRequest,
)
from teams.dawo.scanners.evidence_collection.report_storage import (
    ReportStorageService,
)


def _make_evidence(
    evidence_id: UUID | None = None,
    competitor_name: str = "IntegTestCorp",
    severity: str = "high",
    captured_at: datetime | None = None,
) -> MagicMock:
    """Create a mock Evidence ORM object for integration tests."""
    ev = MagicMock()
    ev.id = evidence_id or uuid4()
    ev.competitor_name = competitor_name
    ev.source_url = "https://example.com/product"
    ev.source_type = "website_page"
    ev.claim_text = "Boosts immunity naturally"
    ev.claim_category = "treatment"
    ev.violation_type = "unauthorized_treatment_claim"
    ev.severity = severity
    ev.regulation_violated = "EC 1924/2006 Art. 10"
    ev.detection_reasoning = "Treatment claim without authorization"
    ev.confidence = 0.93
    ev.screenshot_path = "evidence/screenshots/2026-02/integ-test.png"
    ev.screenshot_hash = "c" * 64
    ev.screenshot_size_bytes = 4000
    ev.captured_at = captured_at or datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)
    ev.violation = MagicMock()
    ev.audit_logs = []
    return ev


@pytest.fixture
def config(tmp_path) -> ViolationReportConfig:
    """Config with tmp_path for storage."""
    return ViolationReportConfig(storage_path=str(tmp_path / "reports"))


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Mock EvidenceRepository."""
    repo = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_storage_svc() -> AsyncMock:
    """Mock EvidenceStorageService for screenshot integrity."""
    svc = AsyncMock()
    svc.verify_integrity = AsyncMock(return_value=True)
    return svc


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock AsyncSession."""
    session = MagicMock()
    session.add = MagicMock()
    return session


class TestViolationReportPipeline:
    """End-to-end report generation pipeline tests."""

    @pytest.mark.asyncio
    async def test_full_pipeline_generate_save_retrieve(
        self, config, mock_repository, mock_storage_svc, mock_session
    ) -> None:
        """Full pipeline: create evidence -> generate report -> save -> retrieve."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-1.4 integration test content"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage_svc,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest(template_type="standard")

        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        # Save to storage
        storage = ReportStorageService(config=config)
        path = await storage.save_report(result)
        assert path.endswith(".pdf")

        # Retrieve from storage
        retrieved = await storage.get_report(result.report_id)
        assert retrieved == result.pdf_bytes

    @pytest.mark.asyncio
    async def test_competitor_scoped_report(
        self, config, mock_repository, mock_storage_svc, mock_session
    ) -> None:
        """Competitor-scoped report only includes that competitor's evidence."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        target_evidence = _make_evidence(competitor_name="TargetCorp")
        mock_repository.search.return_value = ([target_evidence], 1)

        fake_pdf = b"%PDF-competitor-scoped"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage_svc,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest(competitor_name="TargetCorp")

        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert result.evidence_count == 1
        # Verify search was called with competitor filter
        call_kwargs = mock_repository.search.call_args[1]
        assert call_kwargs["competitor_name"] == "TargetCorp"

    @pytest.mark.asyncio
    async def test_date_range_filtering(
        self, config, mock_repository, mock_storage_svc, mock_session
    ) -> None:
        """Date range filtering produces correct evidence subset."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence(
            captured_at=datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)
        )
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-date-range"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage_svc,
            config=config,
            session=mock_session,
        )

        date_from = datetime(2026, 2, 1, tzinfo=UTC)
        date_to = datetime(2026, 2, 28, tzinfo=UTC)
        request = ViolationReportRequest(date_from=date_from, date_to=date_to)

        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert result.evidence_count == 1
        call_kwargs = mock_repository.search.call_args[1]
        assert call_kwargs["date_from"] == date_from
        assert call_kwargs["date_to"] == date_to

    @pytest.mark.asyncio
    async def test_storage_save_and_retrieval_roundtrip(
        self, config
    ) -> None:
        """Report storage save and retrieval roundtrip."""
        pdf_bytes = b"%PDF-1.4 roundtrip test"
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        report_result = ReportResult(
            pdf_bytes=pdf_bytes,
            report_id=uuid4(),
            filename="roundtrip-test.pdf",
            page_count=1,
            evidence_count=2,
            generated_at=datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC),
            sha256_hash=sha256,
            template_type="standard",
        )

        storage = ReportStorageService(config=config)

        # Save
        path = await storage.save_report(report_result)
        assert path.endswith(".pdf")
        assert str(report_result.report_id) in path

        # Retrieve
        retrieved = await storage.get_report(report_result.report_id)
        assert retrieved == pdf_bytes

        # Verify integrity
        is_valid = await storage.verify_report_integrity(
            report_result.report_id, sha256
        )
        assert is_valid is True

        # List
        items, total = await storage.list_reports()
        assert total == 1
        assert items[0].report_id == report_result.report_id

    @pytest.mark.asyncio
    async def test_deterministic_regeneration(
        self, config, mock_repository, mock_storage_svc, mock_session
    ) -> None:
        """Same inputs produce same hash (deterministic regeneration)."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        # Same PDF bytes = deterministic
        fake_pdf = b"%PDF-deterministic-integration"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage_svc,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        results = []
        for _ in range(2):
            with patch(
                "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
                return_value=mock_html_cls,
            ):
                results.append(await generator.generate_report(request))

        assert results[0].report_id == results[1].report_id
        assert results[0].sha256_hash == results[1].sha256_hash

    @pytest.mark.asyncio
    async def test_audit_log_entries_for_report(
        self, config, mock_repository, mock_storage_svc, mock_session
    ) -> None:
        """Audit log entries written for each evidence in report."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence_list = [_make_evidence() for _ in range(3)]
        mock_repository.search.return_value = (evidence_list, 3)

        fake_pdf = b"%PDF-audit-integration"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage_svc,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert result.evidence_count == 3
        # One audit log per evidence record
        assert mock_session.add.call_count == 3
