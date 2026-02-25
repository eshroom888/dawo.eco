"""API router tests for Reports endpoints (Story 6-10, Task 14).

Tests all 4 report API routes using FastAPI TestClient with
dependency overrides for generator, storage, and config.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from teams.dawo.scanners.evidence_collection.report_config import (
    ViolationReportConfig,
)
from teams.dawo.scanners.evidence_collection.report_schemas import (
    ReportMetadata,
    ReportResult,
)
from ui.backend.routers.reports import (
    get_generator,
    get_report_config,
    get_report_storage,
    router,
)


def _make_report_result(
    pdf_bytes: bytes = b"%PDF-1.4 test",
    template_type: str = "standard",
    evidence_count: int = 3,
) -> ReportResult:
    """Build a sample ReportResult."""
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    return ReportResult(
        pdf_bytes=pdf_bytes,
        report_id=uuid4(),
        filename=f"violation-report-2026-02-15-{template_type}.pdf",
        page_count=2,
        evidence_count=evidence_count,
        generated_at=datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC),
        sha256_hash=sha256,
        template_type=template_type,
    )


def _make_report_metadata(
    report_id=None,
    template_type: str = "standard",
    evidence_count: int = 5,
) -> ReportMetadata:
    """Build a sample ReportMetadata."""
    return ReportMetadata(
        report_id=report_id or uuid4(),
        filename="violation-report-2026-02-15-standard.pdf",
        evidence_count=evidence_count,
        competitor_name="TestCorp",
        template_type=template_type,
        generated_at=datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC),
        sha256_hash="a" * 64,
        page_count=3,
        file_size_bytes=12000,
    )


@pytest.fixture
def config() -> ViolationReportConfig:
    """Default report config."""
    return ViolationReportConfig()


@pytest.fixture
def mock_generator() -> AsyncMock:
    """Mock WeasyPrintPDFGenerator."""
    gen = AsyncMock()
    gen.generate_report = AsyncMock(return_value=_make_report_result())
    return gen


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Mock ReportStorageService."""
    storage = AsyncMock()
    storage.save_report = AsyncMock(return_value="reports/2026-02/test.pdf")
    storage.get_report = AsyncMock(return_value=None)
    storage.list_reports = AsyncMock(return_value=([], 0))
    return storage


@pytest.fixture
def client(config, mock_generator, mock_storage):
    """FastAPI TestClient with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_generator] = lambda: mock_generator
    app.dependency_overrides[get_report_storage] = lambda: mock_storage
    app.dependency_overrides[get_report_config] = lambda: config

    return TestClient(app)


class TestGenerateReport:
    """14.2-14.5: POST /api/reports/generate"""

    def test_generate_with_evidence_ids(self, client, mock_generator):
        """POST with evidence_ids returns report response."""
        eid = str(uuid4())
        response = client.post(
            "/api/reports/generate",
            json={"evidence_ids": [eid], "template_type": "standard"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert data["evidence_count"] >= 0
        assert data["sha256_hash"]
        assert data["download_url"].startswith("/api/reports/")
        mock_generator.generate_report.assert_awaited_once()

    def test_generate_with_competitor_filter(self, client, mock_generator):
        """POST with competitor_name generates competitor-scoped report."""
        response = client.post(
            "/api/reports/generate",
            json={"competitor_name": "TestCorp", "template_type": "standard"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data

    def test_generate_invalid_template_returns_422(self, client):
        """POST with invalid template_type returns 422."""
        response = client.post(
            "/api/reports/generate",
            json={"template_type": "invalid_template"},
        )
        assert response.status_code == 422
        assert "Invalid template_type" in response.json()["detail"]

    def test_generate_empty_evidence_returns_400(self, client, mock_generator):
        """POST when generator raises ValueError returns 400."""
        mock_generator.generate_report.side_effect = ValueError(
            "No evidence records found"
        )
        response = client.post(
            "/api/reports/generate",
            json={"template_type": "standard"},
        )
        assert response.status_code == 400
        assert "No evidence" in response.json()["detail"]


class TestListReports:
    """14.6: GET /api/reports"""

    def test_returns_paginated_list(self, client, mock_storage):
        """GET returns paginated report list."""
        meta = _make_report_metadata()
        mock_storage.list_reports.return_value = ([meta], 1)

        response = client.get("/api/reports?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["template_type"] == "standard"
        assert data["has_more"] is False


class TestDownloadReport:
    """14.7-14.8: GET /api/reports/{report_id}/download"""

    def test_download_returns_pdf(self, client, mock_storage):
        """GET returns PDF stream for existing report."""
        report_id = uuid4()
        mock_storage.get_report.return_value = b"%PDF-1.4 content"

        response = client.get(f"/api/reports/{report_id}/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"%PDF-1.4" in response.content

    def test_download_returns_404_for_missing(self, client, mock_storage):
        """GET returns 404 for non-existent report."""
        mock_storage.get_report.return_value = None

        response = client.get(f"/api/reports/{uuid4()}/download")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetTemplates:
    """14.9: GET /api/reports/templates"""

    def test_returns_template_list(self, client):
        """GET returns available templates from config."""
        response = client.get("/api/reports/templates")
        assert response.status_code == 200
        data = response.json()
        assert "standard" in data["templates"]
        assert "mattilsynet" in data["templates"]
        assert "eu_authority" in data["templates"]
        assert "legal" in data["templates"]
