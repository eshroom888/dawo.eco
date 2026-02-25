"""Tests for WeasyPrintPDFGenerator (Story 6-10, Task 4 + Task 13).

Validates PDF generation with mocked WeasyPrint, repository, and storage.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
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


def _make_evidence(
    evidence_id: UUID | None = None,
    competitor_name: str = "TestCorp",
    severity: str = "high",
    claim_text: str = "Boosts immunity",
    screenshot_path: str = "evidence/screenshots/2026-02/test.png",
    screenshot_hash: str = "a" * 64,
) -> MagicMock:
    """Create a mock Evidence ORM object."""
    ev = MagicMock()
    ev.id = evidence_id or uuid4()
    ev.competitor_name = competitor_name
    ev.source_url = "https://example.com/product"
    ev.source_type = "website_page"
    ev.claim_text = claim_text
    ev.claim_category = "treatment"
    ev.violation_type = "unauthorized_treatment_claim"
    ev.severity = severity
    ev.regulation_violated = "EC 1924/2006 Art. 10"
    ev.detection_reasoning = "Treatment claim without authorization"
    ev.confidence = 0.95
    ev.screenshot_path = screenshot_path
    ev.screenshot_hash = screenshot_hash
    ev.screenshot_size_bytes = 5000
    ev.captured_at = datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)
    ev.violation = MagicMock()
    ev.audit_logs = []
    return ev


@pytest.fixture
def config() -> ViolationReportConfig:
    """Default report config."""
    return ViolationReportConfig()


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Mock EvidenceRepository."""
    repo = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Mock EvidenceStorageService."""
    storage = AsyncMock()
    storage.verify_integrity = AsyncMock(return_value=True)
    return storage


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock AsyncSession for audit logging."""
    session = MagicMock()
    session.add = MagicMock()
    return session


class TestWeasyPrintPDFGenerator:
    """Tests for WeasyPrintPDFGenerator."""

    @pytest.mark.asyncio
    async def test_generate_report_with_evidence_ids(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Generate report with specific evidence_ids returns ReportResult."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.get_by_id.return_value = evidence

        fake_pdf = b"%PDF-1.4 fake content"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest(evidence_ids=[evidence.id])

        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert isinstance(result, ReportResult)
        assert result.pdf_bytes == fake_pdf
        assert result.evidence_count == 1
        assert result.template_type == "standard"
        expected_hash = hashlib.sha256(fake_pdf).hexdigest()
        assert result.sha256_hash == expected_hash

    @pytest.mark.asyncio
    async def test_generate_report_with_competitor_filter(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Generate report with competitor_name uses repository.search()."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence(competitor_name="FilterCorp")
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-1.4 filtered"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest(competitor_name="FilterCorp")

        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert result.evidence_count == 1
        mock_repository.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_report_different_templates(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Each template_type selects a different Jinja2 template."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-template-test"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        for template in ["standard", "mattilsynet", "eu_authority", "legal"]:
            request = ViolationReportRequest(template_type=template)
            with patch(
                "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
                return_value=mock_html_cls,
            ):
                result = await generator.generate_report(request)
            assert result.template_type == template

    @pytest.mark.asyncio
    async def test_deterministic_report_id(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Same PDF bytes produce same report_id."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-deterministic-test"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
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

    @pytest.mark.asyncio
    async def test_sha256_hash_matches_pdf(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """SHA-256 hash in result matches actual PDF content."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"unique pdf content for hash test"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        expected = hashlib.sha256(fake_pdf).hexdigest()
        assert result.sha256_hash == expected

    @pytest.mark.asyncio
    async def test_screenshot_integrity_failure_skips_image(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Screenshot integrity failure logs warning but continues."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)
        mock_storage.verify_integrity.return_value = False

        fake_pdf = b"%PDF-skip-screenshot"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert result.evidence_count == 1  # still included, just no image

    @pytest.mark.asyncio
    async def test_empty_evidence_raises_error(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Empty evidence list raises ValueError."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        mock_repository.search.return_value = ([], 0)

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        with pytest.raises(ValueError, match="No evidence"):
            await generator.generate_report(request)

    @pytest.mark.asyncio
    async def test_max_evidence_limit_enforced(
        self, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """max_evidence_per_report config limit is enforced."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        config = ViolationReportConfig(max_evidence_per_report=2)
        evidence_list = [_make_evidence() for _ in range(5)]
        mock_repository.search.return_value = (evidence_list, 5)

        fake_pdf = b"%PDF-limited"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            result = await generator.generate_report(request)

        assert result.evidence_count == 2

    @pytest.mark.asyncio
    async def test_audit_log_entries_created(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Audit log entries created for each evidence record."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-audit"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        request = ViolationReportRequest()
        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            await generator.generate_report(request)

        # session.add called for audit log entries
        assert mock_session.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_date_range_filter(
        self, config: ViolationReportConfig, mock_repository: AsyncMock,
        mock_storage: AsyncMock, mock_session: AsyncMock,
    ) -> None:
        """Date range filters passed to repository.search()."""
        from teams.dawo.scanners.evidence_collection.report_generator import (
            WeasyPrintPDFGenerator,
        )

        evidence = _make_evidence()
        mock_repository.search.return_value = ([evidence], 1)

        fake_pdf = b"%PDF-date-filter"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = fake_pdf

        generator = WeasyPrintPDFGenerator(
            repository=mock_repository,
            storage_service=mock_storage,
            config=config,
            session=mock_session,
        )

        date_from = datetime(2026, 1, 1, tzinfo=UTC)
        date_to = datetime(2026, 2, 28, tzinfo=UTC)
        request = ViolationReportRequest(
            date_from=date_from, date_to=date_to
        )
        with patch(
            "teams.dawo.scanners.evidence_collection.report_generator._import_weasyprint_html",
            return_value=mock_html_cls,
        ):
            await generator.generate_report(request)

        call_kwargs = mock_repository.search.call_args[1]
        assert call_kwargs["date_from"] == date_from
        assert call_kwargs["date_to"] == date_to
