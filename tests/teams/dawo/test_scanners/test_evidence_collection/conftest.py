"""Shared fixtures for evidence collection tests (Story 6-8).

Provides mock objects and sample data for all test modules.
"""

import struct
import zlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.schemas import CaptureResult
from teams.dawo.scanners.evidence_collection.screenshot_service import (
    ScreenshotServiceProtocol,
)
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService


def _create_minimal_png() -> bytes:
    """Create a minimal valid 1x1 white PNG."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr = (
        struct.pack(">I", 13)
        + b"IHDR"
        + ihdr_data
        + struct.pack(">I", ihdr_crc & 0xFFFFFFFF)
    )
    raw_data = b"\x00\xFF\xFF\xFF"
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    idat = (
        struct.pack(">I", len(compressed))
        + b"IDAT"
        + compressed
        + struct.pack(">I", idat_crc & 0xFFFFFFFF)
    )
    iend_crc = zlib.crc32(b"IEND")
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc & 0xFFFFFFFF)
    return signature + ihdr + idat + iend


MINIMAL_PNG_BYTES = _create_minimal_png()


@pytest.fixture
def minimal_png_bytes() -> bytes:
    """Minimal valid 1x1 PNG bytes for testing."""
    return MINIMAL_PNG_BYTES


@pytest.fixture
def sample_config() -> EvidenceCollectionConfig:
    """Default EvidenceCollectionConfig."""
    return EvidenceCollectionConfig()


@pytest.fixture
def sample_capture_result() -> CaptureResult:
    """CaptureResult with minimal valid PNG bytes."""
    return CaptureResult(
        screenshot_bytes=MINIMAL_PNG_BYTES,
        url="https://www.instagram.com/p/ABC123/embed/",
        captured_at=datetime.now(UTC),
        page_title="Instagram Post",
        metadata={},
    )


@pytest.fixture
def sample_violation_pending():
    """CompetitorViolation mock with evidence_status=pending_collection (Instagram)."""
    v = MagicMock()
    v.id = uuid4()
    v.extracted_claim_id = uuid4()
    v.violation_status = "violation"
    v.severity = "high"
    v.regulation_article = "EC 1924/2006 Art. 10"
    v.violation_type = "unauthorized_treatment_claim"
    v.detection_reasoning = "Treatment claim prohibited"
    v.authorized_claims_checked = 0
    v.nearest_authorized_claim = None
    v.competitor_name = "CompetitorA"
    v.source_url = "https://www.instagram.com/p/ABC123/"
    v.evidence_status = "pending_collection"
    v.detected_at = datetime.now(UTC)
    claim = MagicMock()
    claim.claim_text = "treats brain fog"
    claim.claim_category = "treatment"
    claim.confidence_score = 92
    v.extracted_claim = claim
    return v


@pytest.fixture
def sample_violation_website():
    """CompetitorViolation mock with website source_url."""
    v = MagicMock()
    v.id = uuid4()
    v.extracted_claim_id = uuid4()
    v.violation_status = "violation"
    v.severity = "medium"
    v.regulation_article = "EC 1924/2006 Art. 13.1"
    v.violation_type = "unauthorized_enhancement_claim"
    v.detection_reasoning = "Enhancement claim without authorization"
    v.authorized_claims_checked = 5
    v.nearest_authorized_claim = None
    v.competitor_name = "CompetitorB"
    v.source_url = "https://competitor-b.com/products/mushroom-blend"
    v.evidence_status = "pending_collection"
    v.detected_at = datetime.now(UTC)
    claim = MagicMock()
    claim.claim_text = "boosts brain function"
    claim.claim_category = "enhancement"
    claim.confidence_score = 78
    v.extracted_claim = claim
    return v


@pytest.fixture
def mock_session():
    """AsyncSession mock. session.add is sync MagicMock (not AsyncMock)."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_screenshot_service():
    """ScreenshotServiceProtocol mock."""
    service = AsyncMock(spec=ScreenshotServiceProtocol)
    service.capture = AsyncMock(
        return_value=CaptureResult(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            url="https://www.instagram.com/p/ABC123/embed/",
            captured_at=datetime.now(UTC),
            page_title="Instagram Post",
            metadata={},
        )
    )
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_storage_service():
    """EvidenceStorageService mock."""
    service = AsyncMock(spec=EvidenceStorageService)
    service.store_screenshot = AsyncMock(
        return_value=(
            "evidence/screenshots/2026-02/test-uuid.png",
            "a" * 64,
            len(MINIMAL_PNG_BYTES),
        )
    )
    service.verify_integrity = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_violation_repository():
    """ViolationRepository mock with get_pending_evidence_collection."""
    repo = AsyncMock()
    repo.get_pending_evidence_collection = AsyncMock(return_value=[])
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_evidence_repository():
    """EvidenceRepository mock."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_collected_violation_ids = AsyncMock(return_value=set())
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_event_emitter():
    """RegulatoryEventEmitter mock."""
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter
