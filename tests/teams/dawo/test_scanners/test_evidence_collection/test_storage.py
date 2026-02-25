"""Tests for EvidenceStorageService (Story 6-8, Task 6).

Tests SHA-256 hashing, directory creation, and integrity verification.
"""

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService


@pytest.fixture
def storage_config(tmp_path: Path) -> EvidenceCollectionConfig:
    """Config with storage_base_path pointing to tmp_path."""
    return EvidenceCollectionConfig(
        storage_base_path=str(tmp_path / "evidence" / "screenshots")
    )


@pytest.fixture
def storage_service(storage_config: EvidenceCollectionConfig) -> EvidenceStorageService:
    """EvidenceStorageService with tmp_path config."""
    return EvidenceStorageService(config=storage_config)


class TestStoreScreenshot:
    """Tests for store_screenshot method."""

    async def test_computes_sha256_before_writing(
        self, storage_service: EvidenceStorageService, minimal_png_bytes: bytes
    ) -> None:
        """Hash is computed before writing to disk."""
        eid = uuid4()
        path, hash_val, size = await storage_service.store_screenshot(
            minimal_png_bytes, eid
        )
        expected_hash = hashlib.sha256(minimal_png_bytes).hexdigest()
        assert hash_val == expected_hash

    async def test_creates_directory_structure(
        self,
        storage_service: EvidenceStorageService,
        storage_config: EvidenceCollectionConfig,
        minimal_png_bytes: bytes,
    ) -> None:
        """Creates {base}/{YYYY-MM}/{uuid}.png directory structure."""
        eid = uuid4()
        path, _, _ = await storage_service.store_screenshot(minimal_png_bytes, eid)
        assert Path(path).exists()
        assert str(eid) in path
        assert path.endswith(".png")

    async def test_returns_path_hash_size_tuple(
        self, storage_service: EvidenceStorageService, minimal_png_bytes: bytes
    ) -> None:
        """Returns (path, hash, size) tuple."""
        eid = uuid4()
        path, hash_val, size = await storage_service.store_screenshot(
            minimal_png_bytes, eid
        )
        assert isinstance(path, str)
        assert len(hash_val) == 64  # SHA-256 hex
        assert size == len(minimal_png_bytes)

    async def test_verifies_hash_after_write(
        self, storage_service: EvidenceStorageService, minimal_png_bytes: bytes
    ) -> None:
        """Re-reads file and verifies hash matches."""
        eid = uuid4()
        path, hash_val, _ = await storage_service.store_screenshot(
            minimal_png_bytes, eid
        )
        # Verify file contents match
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert actual == hash_val


class TestVerifyIntegrity:
    """Tests for verify_integrity method."""

    async def test_returns_true_for_valid_hash(
        self, storage_service: EvidenceStorageService, minimal_png_bytes: bytes
    ) -> None:
        """Returns True when hash matches."""
        eid = uuid4()
        path, hash_val, _ = await storage_service.store_screenshot(
            minimal_png_bytes, eid
        )
        assert await storage_service.verify_integrity(path, hash_val) is True

    async def test_returns_false_for_tampered_file(
        self, storage_service: EvidenceStorageService, minimal_png_bytes: bytes
    ) -> None:
        """Returns False when file has been modified."""
        eid = uuid4()
        path, hash_val, _ = await storage_service.store_screenshot(
            minimal_png_bytes, eid
        )
        # Tamper with file
        p = Path(path)
        try:
            p.chmod(0o644)
        except OSError:
            pass
        p.write_bytes(b"tampered data")
        assert await storage_service.verify_integrity(path, hash_val) is False

    async def test_returns_false_for_missing_file(
        self, storage_service: EvidenceStorageService
    ) -> None:
        """Returns False when file doesn't exist."""
        result = await storage_service.verify_integrity(
            "nonexistent/path.png", "a" * 64
        )
        assert result is False
