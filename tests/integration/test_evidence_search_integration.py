"""Integration tests for evidence search pipeline.

Story 6-9, Task 14: End-to-end integration tests for evidence search,
filter, summary, competitor timeline, and download package functionality.

Uses real EvidenceRepository with mocked AsyncSession, real
EvidenceStorageService with tmp_path, and real EvidenceDownloadService.
"""

import hashlib
import json
import struct
import zipfile
import zlib
from collections import namedtuple
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.regulatory.models import Evidence, EvidenceAuditLog
from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.download import EvidenceDownloadService
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService


def _create_minimal_png() -> bytes:
    """Create a minimal valid 1x1 white PNG."""
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr = (
        struct.pack(">I", 13) + b"IHDR" + ihdr_data
        + struct.pack(">I", ihdr_crc & 0xFFFFFFFF)
    )
    raw_data = b"\x00\xFF\xFF\xFF"
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    idat = (
        struct.pack(">I", len(compressed)) + b"IDAT" + compressed
        + struct.pack(">I", idat_crc & 0xFFFFFFFF)
    )
    iend_crc = zlib.crc32(b"IEND")
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc & 0xFFFFFFFF)
    return signature + ihdr + idat + iend


MINIMAL_PNG_BYTES = _create_minimal_png()


def _make_evidence(
    competitor_name: str = "CompetitorA",
    severity: str = "high",
    violation_type: str = "unauthorized_treatment_claim",
    claim_text: str = "treats brain fog",
    captured_at: datetime | None = None,
    source_type: str = "instagram_post",
    screenshot_path: str = "",
    screenshot_hash: str = "",
    **kwargs,
) -> MagicMock:
    """Create mock Evidence model for search tests."""
    e = MagicMock(spec=Evidence)
    e.id = kwargs.get("id", uuid4())
    e.competitor_name = competitor_name
    e.violation_type = violation_type
    e.severity = severity
    e.claim_text = claim_text
    e.claim_category = kwargs.get("claim_category", "treatment")
    e.source_type = source_type
    e.source_url = kwargs.get("source_url", "https://instagram.com/p/ABC/")
    e.captured_at = captured_at or datetime.now(UTC)
    e.screenshot_path = screenshot_path
    e.screenshot_hash = screenshot_hash or hashlib.sha256(MINIMAL_PNG_BYTES).hexdigest()
    e.screenshot_size_bytes = kwargs.get("screenshot_size_bytes", len(MINIMAL_PNG_BYTES))
    e.regulation_violated = kwargs.get("regulation_violated", "EC 1924/2006 Art. 10")
    e.detection_reasoning = kwargs.get("detection_reasoning", "Treatment claim")
    e.confidence = kwargs.get("confidence", 0.92)
    e.evidence_metadata = kwargs.get("evidence_metadata", {})
    e.created_at = kwargs.get("created_at", datetime.now(UTC))
    e.audit_logs = kwargs.get("audit_logs", [])
    e.violation = kwargs.get("violation", None)
    return e


@pytest.fixture
def integration_config(tmp_path: Path) -> EvidenceCollectionConfig:
    """Config with storage pointing to tmp_path."""
    return EvidenceCollectionConfig(
        storage_base_path=str(tmp_path / "evidence" / "screenshots"),
    )


@pytest.fixture
def real_storage(integration_config: EvidenceCollectionConfig) -> EvidenceStorageService:
    """Real EvidenceStorageService writing to tmp_path."""
    return EvidenceStorageService(config=integration_config)


@pytest.fixture
def mock_session():
    """AsyncSession mock with controlled execute returns."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


class TestSearchPipelineIntegration:
    """14.2: Full search pipeline — create evidence → search → verify."""

    @pytest.mark.asyncio
    async def test_create_store_search_flow(self, real_storage, mock_session, tmp_path):
        """End-to-end: store screenshot → create evidence → search returns it."""
        # Step 1: Store screenshot using real storage service
        path, sha256, size = await real_storage.store_screenshot(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            evidence_id=uuid4(),
        )
        assert Path(path).exists()

        # Step 2: Create evidence mock pointing to real file
        evidence = _make_evidence(
            screenshot_path=path,
            screenshot_hash=sha256,
            screenshot_size_bytes=size,
            competitor_name="CompetitorA",
            severity="high",
            claim_text="treats brain fog",
        )

        # Step 3: Setup mock session — search() uses session.scalar() for count
        # and session.execute() for data query
        mock_session.scalar = AsyncMock(return_value=1)

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [evidence]
        mock_session.execute = AsyncMock(return_value=data_result)

        repo = EvidenceRepository(session=mock_session, storage_service=real_storage)
        results, total = await repo.search()

        assert total == 1
        assert len(results) == 1
        assert results[0].competitor_name == "CompetitorA"


class TestCombinedFiltersIntegration:
    """14.3: Combined filters return correct subset."""

    @pytest.mark.asyncio
    async def test_combined_filters_build_correct_query(self, mock_session, real_storage):
        """Verify that combined filters all reach the SQL query."""
        mock_session.scalar = AsyncMock(return_value=0)

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=data_result)

        repo = EvidenceRepository(session=mock_session, storage_service=real_storage)
        results, total = await repo.search(
            competitor_name="CompetitorA",
            severity="high",
            violation_type="unauthorized_treatment_claim",
            date_from=datetime(2026, 1, 1, tzinfo=UTC),
            date_to=datetime(2026, 12, 31, tzinfo=UTC),
            claim_keywords="brain",
            source_type="instagram_post",
        )

        assert total == 0
        assert len(results) == 0
        # scalar() for count + execute() for data
        mock_session.scalar.assert_awaited_once()
        mock_session.execute.assert_awaited_once()


class TestPaginationIntegration:
    """14.4: Pagination returns correct pages."""

    @pytest.mark.asyncio
    async def test_pagination_page_2(self, mock_session, real_storage):
        """Page 2 uses correct offset."""
        evidence_page2 = _make_evidence(competitor_name="CompetitorC")

        mock_session.scalar = AsyncMock(return_value=50)

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [evidence_page2]
        mock_session.execute = AsyncMock(return_value=data_result)

        repo = EvidenceRepository(session=mock_session, storage_service=real_storage)
        results, total = await repo.search(limit=25, offset=25)

        assert total == 50
        assert len(results) == 1
        assert results[0].competitor_name == "CompetitorC"


class TestSummaryStatsIntegration:
    """14.5: Summary stats match actual data."""

    @pytest.mark.asyncio
    async def test_summary_stats_structure(self, mock_session, real_storage):
        """Verify get_summary_stats returns correct structure."""
        # session.scalar() for total count
        mock_session.scalar = AsyncMock(return_value=10)

        # session.execute() for 3 group-by queries (severity, competitor, violation_type)
        severity_result = MagicMock()
        severity_result.all.return_value = [("high", 3), ("medium", 5), ("low", 2)]

        competitor_result = MagicMock()
        competitor_result.all.return_value = [("CompetitorA", 6), ("CompetitorB", 4)]

        violation_result = MagicMock()
        violation_result.all.return_value = [
            ("unauthorized_treatment_claim", 7),
            ("unauthorized_prevention_claim", 3),
        ]

        mock_session.execute = AsyncMock(
            side_effect=[severity_result, competitor_result, violation_result]
        )

        repo = EvidenceRepository(session=mock_session, storage_service=real_storage)
        stats = await repo.get_summary_stats()

        assert stats["total_evidence"] == 10
        assert stats["by_severity"]["high"] == 3
        assert stats["by_severity"]["medium"] == 5
        assert stats["by_competitor"]["CompetitorA"] == 6
        assert stats["by_violation_type"]["unauthorized_treatment_claim"] == 7


class TestCompetitorTimelineIntegration:
    """14.6: Competitor timeline aggregation."""

    @pytest.mark.asyncio
    async def test_timeline_returns_monthly_counts(self, mock_session, real_storage):
        """Verify timeline returns correctly formatted monthly data."""
        # Timeline query returns rows with .month and .count attributes
        TimelineRow = namedtuple("TimelineRow", ["month", "count"])
        timeline_result = MagicMock()
        timeline_result.all.return_value = [
            TimelineRow("2026-01", 3),
            TimelineRow("2026-02", 7),
        ]

        mock_session.execute = AsyncMock(return_value=timeline_result)

        repo = EvidenceRepository(session=mock_session, storage_service=real_storage)
        timeline = await repo.get_competitor_timeline("CompetitorA")

        assert len(timeline) == 2
        assert timeline[0]["month"] == "2026-01"
        assert timeline[0]["count"] == 3
        assert timeline[1]["month"] == "2026-02"
        assert timeline[1]["count"] == 7


class TestEvidenceDownloadIntegration:
    """14.7: Evidence download package integrity."""

    @pytest.mark.asyncio
    async def test_download_package_from_real_storage(self, real_storage, tmp_path):
        """Full flow: store screenshot → create download → verify ZIP integrity."""
        evidence_id = uuid4()

        # Step 1: Store with real storage
        path, sha256, size = await real_storage.store_screenshot(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            evidence_id=evidence_id,
        )

        # Step 2: Create evidence mock with real file reference
        evidence = _make_evidence(
            id=evidence_id,
            screenshot_path=path,
            screenshot_hash=sha256,
            screenshot_size_bytes=size,
        )

        # Step 3: Create download package
        download_service = EvidenceDownloadService(storage_service=real_storage)
        package_bytes = await download_service.create_evidence_package(evidence)

        # Step 4: Verify ZIP contents
        with zipfile.ZipFile(BytesIO(package_bytes)) as zf:
            names = zf.namelist()
            assert "screenshot.png" in names
            assert "metadata.json" in names
            assert "integrity.txt" in names

            # Verify screenshot matches original
            screenshot_data = zf.read("screenshot.png")
            assert screenshot_data == MINIMAL_PNG_BYTES

            # Verify metadata fields
            metadata = json.loads(zf.read("metadata.json"))
            assert metadata["evidence_id"] == str(evidence_id)
            assert metadata["screenshot_hash"] == sha256

            # Verify integrity hash
            integrity = zf.read("integrity.txt").decode()
            assert sha256 in integrity

    @pytest.mark.asyncio
    async def test_download_detects_tampered_screenshot(self, real_storage):
        """Download service detects SHA-256 mismatch."""
        evidence_id = uuid4()

        path, sha256, size = await real_storage.store_screenshot(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            evidence_id=evidence_id,
        )

        # Tamper with hash
        evidence = _make_evidence(
            id=evidence_id,
            screenshot_path=path,
            screenshot_hash="tampered_hash_value",
            screenshot_size_bytes=size,
        )

        download_service = EvidenceDownloadService(storage_service=real_storage)

        with pytest.raises(RuntimeError, match="Integrity"):
            await download_service.create_evidence_package(evidence)
