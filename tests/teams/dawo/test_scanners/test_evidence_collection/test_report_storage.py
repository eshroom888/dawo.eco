"""Tests for ReportStorageService (Story 6-10, Task 5 + Task 13).

Uses tmp_path fixture for filesystem tests.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
)
from teams.dawo.scanners.evidence_collection.report_schemas import ReportResult


@pytest.fixture
def config(tmp_path) -> ViolationReportConfig:
    """Config with storage_path pointing to tmp dir."""
    return ViolationReportConfig(storage_path=str(tmp_path / "reports"))


@pytest.fixture
def sample_result() -> ReportResult:
    """A sample ReportResult for testing."""
    pdf_bytes = b"%PDF-1.4 test report content"
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    return ReportResult(
        pdf_bytes=pdf_bytes,
        report_id=uuid4(),
        filename="test-report.pdf",
        page_count=3,
        evidence_count=5,
        generated_at=datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC),
        sha256_hash=sha256,
        template_type="standard",
    )


class TestReportStorageService:
    """Tests for ReportStorageService."""

    @pytest.mark.asyncio
    async def test_save_report_writes_to_correct_path(
        self, config: ViolationReportConfig, sample_result: ReportResult
    ) -> None:
        """save_report writes PDF to {storage_path}/{YYYY-MM}/{report_id}.pdf."""
        from teams.dawo.scanners.evidence_collection.report_storage import (
            ReportStorageService,
        )

        service = ReportStorageService(config=config)
        path = await service.save_report(sample_result)

        assert str(sample_result.report_id) in path
        assert path.endswith(".pdf")

    @pytest.mark.asyncio
    async def test_get_report_returns_bytes(
        self, config: ViolationReportConfig, sample_result: ReportResult
    ) -> None:
        """get_report returns bytes for saved report."""
        from teams.dawo.scanners.evidence_collection.report_storage import (
            ReportStorageService,
        )

        service = ReportStorageService(config=config)
        await service.save_report(sample_result)

        result = await service.get_report(sample_result.report_id)
        assert result == sample_result.pdf_bytes

    @pytest.mark.asyncio
    async def test_get_report_returns_none_for_missing(
        self, config: ViolationReportConfig
    ) -> None:
        """get_report returns None for non-existent report."""
        from teams.dawo.scanners.evidence_collection.report_storage import (
            ReportStorageService,
        )

        service = ReportStorageService(config=config)
        result = await service.get_report(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_reports_paginated(
        self, config: ViolationReportConfig
    ) -> None:
        """list_reports returns paginated metadata."""
        from teams.dawo.scanners.evidence_collection.report_storage import (
            ReportStorageService,
        )

        service = ReportStorageService(config=config)

        # Save 3 reports
        for i in range(3):
            pdf = f"%PDF-report-{i}".encode()
            sha = hashlib.sha256(pdf).hexdigest()
            result = ReportResult(
                pdf_bytes=pdf,
                report_id=uuid4(),
                filename=f"report-{i}.pdf",
                page_count=1,
                evidence_count=i + 1,
                generated_at=datetime(2026, 2, 15, 12, i, 0, tzinfo=UTC),
                sha256_hash=sha,
                template_type="standard",
            )
            await service.save_report(result)

        items, total = await service.list_reports(limit=2, offset=0)
        assert len(items) <= 2
        assert total == 3

    @pytest.mark.asyncio
    async def test_verify_report_integrity_valid(
        self, config: ViolationReportConfig, sample_result: ReportResult
    ) -> None:
        """verify_report_integrity returns True for valid hash."""
        from teams.dawo.scanners.evidence_collection.report_storage import (
            ReportStorageService,
        )

        service = ReportStorageService(config=config)
        await service.save_report(sample_result)

        is_valid = await service.verify_report_integrity(
            sample_result.report_id, sample_result.sha256_hash
        )
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_report_integrity_invalid(
        self, config: ViolationReportConfig, sample_result: ReportResult
    ) -> None:
        """verify_report_integrity returns False for wrong hash."""
        from teams.dawo.scanners.evidence_collection.report_storage import (
            ReportStorageService,
        )

        service = ReportStorageService(config=config)
        await service.save_report(sample_result)

        is_valid = await service.verify_report_integrity(
            sample_result.report_id, "wrong_hash"
        )
        assert is_valid is False
