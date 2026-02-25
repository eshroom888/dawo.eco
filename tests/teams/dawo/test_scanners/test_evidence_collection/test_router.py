"""API router tests for Evidence endpoints (Story 6-9, Task 12).

Tests all 7 evidence API routes using FastAPI TestClient with
dependency overrides for EvidenceRepository and EvidenceDownloadService.
"""

import io
import json
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routers.evidence import get_download_service, get_repository, router


def _make_evidence_mock(**overrides):
    """Create a mock evidence record with sensible defaults."""
    e = MagicMock()
    e.id = overrides.get("id", uuid4())
    e.competitor_name = overrides.get("competitor_name", "CompetitorA")
    e.violation_type = overrides.get("violation_type", "unauthorized_treatment_claim")
    e.severity = overrides.get("severity", "high")
    e.claim_text = overrides.get("claim_text", "treats brain fog")
    e.claim_category = overrides.get("claim_category", "treatment")
    e.source_type = overrides.get("source_type", "instagram_post")
    e.source_url = overrides.get("source_url", "https://instagram.com/p/ABC123/")
    e.captured_at = overrides.get("captured_at", datetime.now(UTC))
    e.screenshot_path = overrides.get("screenshot_path", "/tmp/evidence/test.png")
    e.screenshot_hash = overrides.get("screenshot_hash", "a" * 64)
    e.screenshot_size_bytes = overrides.get("screenshot_size_bytes", 1024)
    e.regulation_violated = overrides.get("regulation_violated", "EC 1924/2006 Art. 10")
    e.detection_reasoning = overrides.get("detection_reasoning", "Treatment claim")
    e.confidence = overrides.get("confidence", 0.92)
    e.evidence_metadata = overrides.get("evidence_metadata", {})
    e.created_at = overrides.get("created_at", datetime.now(UTC))
    e.audit_logs = overrides.get("audit_logs", [])
    return e


def _build_sample_zip() -> bytes:
    """Build a minimal valid ZIP with expected evidence package files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("screenshot.png", b"fake-png-data")
        zf.writestr("metadata.json", json.dumps({"evidence_id": "test"}))
        zf.writestr("integrity.txt", "SHA-256: abc\n")
    return buf.getvalue()


@pytest.fixture
def mock_repo():
    """Mock EvidenceRepository."""
    repo = AsyncMock()
    repo.search = AsyncMock(return_value=([], 0))
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_id_lightweight = AsyncMock(return_value=None)
    repo.get_summary_stats = AsyncMock(return_value={
        "total_evidence": 10,
        "by_severity": {"high": 3, "medium": 5, "low": 2},
        "by_competitor": {"CompetitorA": 6, "CompetitorB": 4},
        "by_violation_type": {"unauthorized_treatment_claim": 7, "unauthorized_prevention_claim": 3},
    })
    repo.get_distinct_competitors = AsyncMock(return_value=["CompetitorA", "CompetitorB"])
    repo.get_competitor_timeline = AsyncMock(return_value=[
        {"month": "2026-01", "count": 3},
        {"month": "2026-02", "count": 5},
    ])
    repo.log_download = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_dl_service():
    """Mock EvidenceDownloadService."""
    service = AsyncMock()
    service.create_evidence_package = AsyncMock(return_value=_build_sample_zip())
    return service


@pytest.fixture
def client(mock_repo, mock_dl_service):
    """FastAPI TestClient with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_repository] = lambda: mock_repo
    app.dependency_overrides[get_download_service] = lambda: mock_dl_service

    return TestClient(app)


class TestGetSummary:
    """12.2: GET /api/evidence/summary"""

    def test_returns_summary_stats(self, client, mock_repo):
        response = client.get("/api/evidence/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_evidence"] == 10
        assert data["by_severity"]["high"] == 3
        assert data["by_competitor"]["CompetitorA"] == 6
        mock_repo.get_summary_stats.assert_awaited_once()


class TestListEvidence:
    """12.3-12.4, 12.10-12.11: GET /api/evidence"""

    def test_returns_paginated_list(self, client, mock_repo):
        evidence = _make_evidence_mock()
        mock_repo.search.return_value = ([evidence], 1)

        response = client.get("/api/evidence")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["competitor_name"] == "CompetitorA"
        assert data["has_more"] is False

    def test_with_filter_query_params(self, client, mock_repo):
        mock_repo.search.return_value = ([], 0)

        response = client.get("/api/evidence?competitor=CompetitorA&severity=high&keywords=brain")
        assert response.status_code == 200

        call_kwargs = mock_repo.search.call_args.kwargs
        assert call_kwargs["competitor_name"] == "CompetitorA"
        assert call_kwargs["severity"] == "high"
        assert call_kwargs["claim_keywords"] == "brain"

    def test_pagination_defaults(self, client, mock_repo):
        mock_repo.search.return_value = ([], 0)

        response = client.get("/api/evidence")
        assert response.status_code == 200

        call_kwargs = mock_repo.search.call_args.kwargs
        assert call_kwargs["limit"] == 25
        assert call_kwargs["offset"] == 0

    def test_pagination_max_limit(self, client, mock_repo):
        response = client.get("/api/evidence?limit=200")
        assert response.status_code == 422  # Validation error: le=100

    def test_has_more_true_when_more_results(self, client, mock_repo):
        evidence = _make_evidence_mock()
        mock_repo.search.return_value = ([evidence], 50)

        response = client.get("/api/evidence?limit=25&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True


class TestGetEvidenceDetail:
    """12.5-12.6: GET /api/evidence/{evidence_id}"""

    def test_returns_detail(self, client, mock_repo):
        evidence_id = uuid4()
        audit_log = MagicMock()
        audit_log.id = uuid4()
        audit_log.action = "collected"
        audit_log.actor = "system"
        audit_log.details = None
        audit_log.hash_verified = True
        audit_log.created_at = datetime.now(UTC)

        evidence = _make_evidence_mock(id=evidence_id, audit_logs=[audit_log])
        mock_repo.get_by_id.return_value = evidence

        response = client.get(f"/api/evidence/{evidence_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(evidence_id)
        assert data["competitor_name"] == "CompetitorA"
        assert len(data["audit_logs"]) == 1
        assert data["audit_logs"][0]["action"] == "collected"

    def test_returns_404_for_missing(self, client, mock_repo):
        mock_repo.get_by_id.return_value = None

        response = client.get(f"/api/evidence/{uuid4()}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDownloadEvidence:
    """12.7: GET /api/evidence/{evidence_id}/download"""

    def test_returns_zip(self, client, mock_repo, mock_dl_service):
        evidence_id = uuid4()
        evidence = _make_evidence_mock(id=evidence_id)
        mock_repo.get_by_id_lightweight.return_value = evidence

        response = client.get(f"/api/evidence/{evidence_id}/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

        # Verify it's a valid ZIP with expected files
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer) as zf:
            names = zf.namelist()
            assert "screenshot.png" in names
            assert "metadata.json" in names
            assert "integrity.txt" in names

        mock_dl_service.create_evidence_package.assert_awaited_once_with(evidence)

    def test_returns_404_for_missing(self, client, mock_repo):
        mock_repo.get_by_id_lightweight.return_value = None

        response = client.get(f"/api/evidence/{uuid4()}/download")
        assert response.status_code == 404

    def test_returns_404_for_missing_screenshot(self, client, mock_repo, mock_dl_service):
        evidence = _make_evidence_mock()
        mock_repo.get_by_id_lightweight.return_value = evidence
        mock_dl_service.create_evidence_package.side_effect = FileNotFoundError("gone")

        response = client.get(f"/api/evidence/{evidence.id}/download")
        assert response.status_code == 404
        assert "screenshot" in response.json()["detail"].lower()

    def test_returns_500_for_integrity_failure(self, client, mock_repo, mock_dl_service):
        evidence = _make_evidence_mock()
        mock_repo.get_by_id_lightweight.return_value = evidence
        mock_dl_service.create_evidence_package.side_effect = RuntimeError("hash mismatch")

        response = client.get(f"/api/evidence/{evidence.id}/download")
        assert response.status_code == 500
        assert "integrity" in response.json()["detail"].lower()


class TestGetCompetitors:
    """12.8: GET /api/evidence/competitors"""

    def test_returns_name_list(self, client, mock_repo):
        response = client.get("/api/evidence/competitors")
        assert response.status_code == 200
        data = response.json()
        assert data == ["CompetitorA", "CompetitorB"]
        mock_repo.get_distinct_competitors.assert_awaited_once()


class TestGetCompetitorTimeline:
    """12.9: GET /api/evidence/competitors/{name}/timeline"""

    def test_returns_timeline(self, client, mock_repo):
        response = client.get("/api/evidence/competitors/CompetitorA/timeline")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["month"] == "2026-01"
        assert data[0]["count"] == 3
        mock_repo.get_competitor_timeline.assert_awaited_once_with("CompetitorA")
