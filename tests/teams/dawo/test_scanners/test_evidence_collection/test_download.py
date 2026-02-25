"""Tests for EvidenceDownloadService (Story 6-9, Task 5).

Tests ZIP package creation with screenshot, metadata, and integrity file.
"""

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from teams.dawo.scanners.evidence_collection.download import EvidenceDownloadService
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService


@pytest.fixture
def mock_storage() -> AsyncMock:
    """EvidenceStorageService mock."""
    return AsyncMock(spec=EvidenceStorageService)


@pytest.fixture
def download_service(mock_storage) -> EvidenceDownloadService:
    """EvidenceDownloadService with mocked storage."""
    return EvidenceDownloadService(storage_service=mock_storage)


@pytest.fixture
def sample_evidence(minimal_png_bytes) -> MagicMock:
    """Mock Evidence with valid screenshot data."""
    sha = hashlib.sha256(minimal_png_bytes).hexdigest()
    e = MagicMock()
    e.id = uuid4()
    e.competitor_name = "CompetitorA"
    e.source_url = "https://instagram.com/p/ABC123/"
    e.source_type = "instagram_post"
    e.claim_text = "treats brain fog"
    e.claim_category = "treatment"
    e.violation_type = "unauthorized_treatment_claim"
    e.severity = "high"
    e.regulation_violated = "EC 1924/2006 Art. 10"
    e.confidence = 0.92
    e.captured_at = datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC)
    e.screenshot_path = "evidence/screenshots/2026-02/test.png"
    e.screenshot_hash = sha
    e.screenshot_size_bytes = len(minimal_png_bytes)
    return e


class TestCreateEvidencePackage:
    """Tests for create_evidence_package()."""

    async def test_returns_valid_zip_bytes(
        self, download_service, sample_evidence, minimal_png_bytes, tmp_path
    ) -> None:
        """create_evidence_package() returns valid ZIP bytes."""
        # Write screenshot to temp path
        screenshot_file = tmp_path / "test.png"
        screenshot_file.write_bytes(minimal_png_bytes)
        sample_evidence.screenshot_path = str(screenshot_file)

        result = await download_service.create_evidence_package(sample_evidence)
        assert isinstance(result, bytes)
        assert len(result) > 0

        # Verify it's a valid ZIP
        zf = zipfile.ZipFile(io.BytesIO(result))
        assert zf.testzip() is None

    async def test_zip_contains_expected_files(
        self, download_service, sample_evidence, minimal_png_bytes, tmp_path
    ) -> None:
        """ZIP contains screenshot.png, metadata.json, integrity.txt."""
        screenshot_file = tmp_path / "test.png"
        screenshot_file.write_bytes(minimal_png_bytes)
        sample_evidence.screenshot_path = str(screenshot_file)

        result = await download_service.create_evidence_package(sample_evidence)
        zf = zipfile.ZipFile(io.BytesIO(result))
        names = zf.namelist()
        assert "screenshot.png" in names
        assert "metadata.json" in names
        assert "integrity.txt" in names

    async def test_metadata_has_correct_fields(
        self, download_service, sample_evidence, minimal_png_bytes, tmp_path
    ) -> None:
        """metadata.json has correct evidence fields."""
        screenshot_file = tmp_path / "test.png"
        screenshot_file.write_bytes(minimal_png_bytes)
        sample_evidence.screenshot_path = str(screenshot_file)

        result = await download_service.create_evidence_package(sample_evidence)
        zf = zipfile.ZipFile(io.BytesIO(result))
        metadata = json.loads(zf.read("metadata.json"))
        assert metadata["evidence_id"] == str(sample_evidence.id)
        assert metadata["competitor_name"] == "CompetitorA"
        assert metadata["source_url"] == "https://instagram.com/p/ABC123/"
        assert metadata["severity"] == "high"
        assert metadata["confidence"] == 0.92
        assert metadata["screenshot_hash"] == sample_evidence.screenshot_hash

    async def test_hash_verification_failure_raises(
        self, download_service, sample_evidence, tmp_path
    ) -> None:
        """create_evidence_package() raises RuntimeError on hash mismatch."""
        screenshot_file = tmp_path / "test.png"
        screenshot_file.write_bytes(b"tampered data")
        sample_evidence.screenshot_path = str(screenshot_file)
        sample_evidence.screenshot_hash = "a" * 64  # Wrong hash

        with pytest.raises(RuntimeError, match="Integrity check failed"):
            await download_service.create_evidence_package(sample_evidence)
