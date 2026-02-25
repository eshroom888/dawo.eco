"""Integration tests for evidence collection pipeline.

Story 6-8, Task 13: End-to-end integration tests.

Tests the full flow from pending violations → screenshot capture (mocked) →
file storage (real, tmp_path) → evidence repository → status update → event emission.
Uses real EvidenceStorageService and EvidenceCollector with mocked I/O.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.regulatory.events import RegulatoryEventType
from core.regulatory.models import Evidence, EvidenceAuditLog, EvidenceCollectionStatus
from teams.dawo.scanners.evidence_collection.collector import EvidenceCollector
from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.repository import EvidenceRepository
from teams.dawo.scanners.evidence_collection.schemas import (
    CaptureResult,
    CollectionBatchResult,
    ImmutableEvidenceError,
)
from teams.dawo.scanners.evidence_collection.storage import EvidenceStorageService
from tests.teams.dawo.test_scanners.test_evidence_collection.conftest import (
    MINIMAL_PNG_BYTES,
)


def _make_violation(
    source_url: str,
    competitor_name: str = "CompetitorA",
    severity: str = "high",
    violation_type: str = "unauthorized_treatment_claim",
    regulation_article: str = "EC 1924/2006 Art. 10",
    claim_text: str = "treats brain fog",
    claim_category: str = "treatment",
    confidence_score: int = 92,
) -> MagicMock:
    """Create a mock CompetitorViolation with extracted_claim relationship."""
    v = MagicMock()
    v.id = uuid4()
    v.extracted_claim_id = uuid4()
    v.violation_status = "violation"
    v.severity = severity
    v.regulation_article = regulation_article
    v.violation_type = violation_type
    v.detection_reasoning = "Treatment claim prohibited"
    v.competitor_name = competitor_name
    v.source_url = source_url
    v.evidence_status = "pending_collection"
    v.detected_at = datetime.now(UTC)

    claim = MagicMock()
    claim.claim_text = claim_text
    claim.claim_category = claim_category
    claim.confidence_score = confidence_score
    v.extracted_claim = claim
    return v


@pytest.fixture
def integration_config(tmp_path: Path) -> EvidenceCollectionConfig:
    """Config with storage pointing to tmp_path."""
    return EvidenceCollectionConfig(
        storage_base_path=str(tmp_path / "evidence" / "screenshots"),
        batch_size=20,
    )


@pytest.fixture
def real_storage(integration_config: EvidenceCollectionConfig) -> EvidenceStorageService:
    """Real EvidenceStorageService writing to tmp_path."""
    return EvidenceStorageService(config=integration_config)


@pytest.fixture
def mock_session():
    """AsyncSession mock for EvidenceRepository."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def real_evidence_repo(mock_session, real_storage) -> EvidenceRepository:
    """Real EvidenceRepository with mocked session and real storage."""
    return EvidenceRepository(session=mock_session, storage_service=real_storage)


@pytest.fixture
def mock_violation_repo():
    """Mock violation repository returning pending violations."""
    repo = AsyncMock()
    repo.get_pending_evidence_collection = AsyncMock(return_value=[])
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_screenshot_service():
    """Mock screenshot service returning CaptureResult with real PNG bytes."""
    service = AsyncMock()
    service.capture = AsyncMock(
        return_value=CaptureResult(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            url="https://www.instagram.com/p/ABC123/embed/",
            captured_at=datetime.now(UTC),
            page_title="Test Page",
            metadata={},
        )
    )
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_event_emitter():
    """Mock event emitter capturing emitted events."""
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter


class TestFullPipeline:
    """13.1: Full pipeline — violation → capture → store → evidence → status."""

    @pytest.mark.asyncio
    async def test_end_to_end_evidence_collection(
        self,
        integration_config,
        real_storage,
        mock_session,
        mock_violation_repo,
        mock_screenshot_service,
        mock_event_emitter,
        tmp_path,
    ):
        """Pending violation → mock screenshot → real file storage → evidence created → status updated."""
        violation = _make_violation(
            source_url="https://www.instagram.com/p/ABC123/",
            competitor_name="CompetitorA",
        )
        mock_violation_repo.get_pending_evidence_collection.return_value = [violation]

        # Real evidence repo with mock session
        evidence_repo = EvidenceRepository(
            session=mock_session, storage_service=real_storage
        )
        # Mock get_collected_violation_ids to return empty (no prior collection)
        evidence_repo.get_collected_violation_ids = AsyncMock(return_value=set())

        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        evidence_repo.create = AsyncMock(return_value=mock_evidence)
        evidence_repo.commit = AsyncMock()

        collector = EvidenceCollector(
            violation_repository=mock_violation_repo,
            evidence_repository=evidence_repo,
            screenshot_service=mock_screenshot_service,
            storage_service=real_storage,
            event_emitter=mock_event_emitter,
            config=integration_config,
        )

        result = await collector.execute()

        # Verify pipeline result
        assert isinstance(result, CollectionBatchResult)
        assert result.total_processed == 1
        assert result.collected == 1
        assert result.failed == 0
        assert result.skipped_already_collected == 0

        # Screenshot service was called with embed URL
        mock_screenshot_service.capture.assert_called_once()
        capture_url = mock_screenshot_service.capture.call_args[0][0]
        assert "/embed/" in capture_url

        # Evidence record created
        evidence_repo.create.assert_called_once()

        # Violation status updated
        assert violation.evidence_status == EvidenceCollectionStatus.COLLECTED.value

        # Event emitted
        mock_event_emitter.emit.assert_called_once()
        event = mock_event_emitter.emit.call_args[0][0]
        assert event.event_type == RegulatoryEventType.EVIDENCE_COLLECTED


class TestIdempotency:
    """13.2: Run twice → second run skips all."""

    @pytest.mark.asyncio
    async def test_second_run_skips_already_collected(
        self,
        integration_config,
        real_storage,
        mock_session,
        mock_violation_repo,
        mock_screenshot_service,
        mock_event_emitter,
    ):
        """First run collects evidence, second run skips (idempotent)."""
        violation = _make_violation(
            source_url="https://competitor.com/products",
            competitor_name="CompetitorB",
        )
        violation_id = violation.id
        mock_violation_repo.get_pending_evidence_collection.return_value = [violation]

        evidence_repo = AsyncMock()
        evidence_repo.get_collected_violation_ids = AsyncMock(return_value=set())
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        evidence_repo.create = AsyncMock(return_value=mock_evidence)
        evidence_repo.commit = AsyncMock()

        collector = EvidenceCollector(
            violation_repository=mock_violation_repo,
            evidence_repository=evidence_repo,
            screenshot_service=mock_screenshot_service,
            storage_service=real_storage,
            event_emitter=mock_event_emitter,
            config=integration_config,
        )

        # First run: collect
        result1 = await collector.execute()
        assert result1.collected == 1
        assert result1.skipped_already_collected == 0

        # Second run: violation_id now in collected set
        evidence_repo.get_collected_violation_ids.return_value = {violation_id}
        mock_screenshot_service.capture.reset_mock()
        mock_event_emitter.emit.reset_mock()
        evidence_repo.create.reset_mock()

        result2 = await collector.execute()
        assert result2.skipped_already_collected == 1
        assert result2.collected == 0
        mock_screenshot_service.capture.assert_not_called()
        mock_event_emitter.emit.assert_not_called()


class TestImmutabilityGuard:
    """13.3: Attempt update → ImmutableEvidenceError."""

    @pytest.mark.asyncio
    async def test_update_always_raises_immutable_error(
        self, real_evidence_repo, mock_session
    ):
        """EvidenceRepository.update() always raises ImmutableEvidenceError."""
        evidence_id = uuid4()

        with pytest.raises(ImmutableEvidenceError):
            await real_evidence_repo.update(evidence_id, claim_text="changed")

        # Audit log entry was added
        mock_session.add.assert_called_once()
        audit_arg = mock_session.add.call_args[0][0]
        assert isinstance(audit_arg, EvidenceAuditLog)
        assert audit_arg.action == "modification_blocked"
        assert "claim_text" in str(audit_arg.details)


class TestHashIntegrity:
    """13.4: SHA-256 integrity verification through storage service."""

    @pytest.mark.asyncio
    async def test_store_and_verify_integrity(self, real_storage):
        """Store screenshot → verify integrity → True. Tamper → False."""
        evidence_id = uuid4()

        # Store
        path, hash_val, size = await real_storage.store_screenshot(
            MINIMAL_PNG_BYTES, evidence_id
        )

        # Verify file exists and hash matches
        assert Path(path).exists()
        assert len(hash_val) == 64
        assert size == len(MINIMAL_PNG_BYTES)

        # Verify integrity passes
        assert await real_storage.verify_integrity(path, hash_val) is True

        # Compute expected hash independently
        expected = hashlib.sha256(MINIMAL_PNG_BYTES).hexdigest()
        assert hash_val == expected

        # Tamper with file
        p = Path(path)
        try:
            p.chmod(0o644)
        except OSError:
            pass
        p.write_bytes(b"tampered data")

        # Integrity check now fails
        assert await real_storage.verify_integrity(path, hash_val) is False

    @pytest.mark.asyncio
    async def test_missing_file_returns_false(self, real_storage):
        """verify_integrity returns False for nonexistent file."""
        result = await real_storage.verify_integrity(
            "nonexistent/path.png", "a" * 64
        )
        assert result is False


class TestInstagramEmbedUrl:
    """13.5: Instagram URL → embed URL conversion in collector pipeline."""

    @pytest.mark.asyncio
    async def test_instagram_url_converted_to_embed(
        self,
        integration_config,
        real_storage,
        mock_session,
        mock_violation_repo,
        mock_screenshot_service,
        mock_event_emitter,
    ):
        """Instagram /p/ URL → /p/{shortcode}/embed/ for capture."""
        violation = _make_violation(
            source_url="https://www.instagram.com/p/XYZ789/",
        )
        mock_violation_repo.get_pending_evidence_collection.return_value = [violation]

        evidence_repo = AsyncMock()
        evidence_repo.get_collected_violation_ids = AsyncMock(return_value=set())
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        evidence_repo.create = AsyncMock(return_value=mock_evidence)
        evidence_repo.commit = AsyncMock()

        collector = EvidenceCollector(
            violation_repository=mock_violation_repo,
            evidence_repository=evidence_repo,
            screenshot_service=mock_screenshot_service,
            storage_service=real_storage,
            event_emitter=mock_event_emitter,
            config=integration_config,
        )

        await collector.execute()

        capture_url = mock_screenshot_service.capture.call_args[0][0]
        assert capture_url == "https://www.instagram.com/p/XYZ789/embed/"

    @pytest.mark.asyncio
    async def test_website_url_passed_through(
        self,
        integration_config,
        real_storage,
        mock_session,
        mock_violation_repo,
        mock_screenshot_service,
        mock_event_emitter,
    ):
        """Non-Instagram URL passed through unchanged."""
        website_url = "https://competitor.com/products/mushroom"
        violation = _make_violation(source_url=website_url)
        mock_violation_repo.get_pending_evidence_collection.return_value = [violation]

        mock_screenshot_service.capture.return_value = CaptureResult(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            url=website_url,
            captured_at=datetime.now(UTC),
            page_title="Product Page",
            metadata={},
        )

        evidence_repo = AsyncMock()
        evidence_repo.get_collected_violation_ids = AsyncMock(return_value=set())
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        evidence_repo.create = AsyncMock(return_value=mock_evidence)
        evidence_repo.commit = AsyncMock()

        collector = EvidenceCollector(
            violation_repository=mock_violation_repo,
            evidence_repository=evidence_repo,
            screenshot_service=mock_screenshot_service,
            storage_service=real_storage,
            event_emitter=mock_event_emitter,
            config=integration_config,
        )

        await collector.execute()

        capture_url = mock_screenshot_service.capture.call_args[0][0]
        assert capture_url == website_url


class TestEventEmission:
    """13.6: EVIDENCE_COLLECTED event emitted with correct data."""

    @pytest.mark.asyncio
    async def test_event_contains_violation_and_evidence_data(
        self,
        integration_config,
        real_storage,
        mock_session,
        mock_violation_repo,
        mock_screenshot_service,
        mock_event_emitter,
    ):
        """EVIDENCE_COLLECTED event has violation_id, evidence_id, competitor, hash."""
        violation = _make_violation(
            source_url="https://www.instagram.com/p/EVT123/",
            competitor_name="EventTestCo",
        )
        mock_violation_repo.get_pending_evidence_collection.return_value = [violation]

        evidence_repo = AsyncMock()
        evidence_repo.get_collected_violation_ids = AsyncMock(return_value=set())
        mock_evidence = MagicMock()
        evidence_id = uuid4()
        mock_evidence.id = evidence_id
        evidence_repo.create = AsyncMock(return_value=mock_evidence)
        evidence_repo.commit = AsyncMock()

        collector = EvidenceCollector(
            violation_repository=mock_violation_repo,
            evidence_repository=evidence_repo,
            screenshot_service=mock_screenshot_service,
            storage_service=real_storage,
            event_emitter=mock_event_emitter,
            config=integration_config,
        )

        await collector.execute()

        mock_event_emitter.emit.assert_called_once()
        event = mock_event_emitter.emit.call_args[0][0]

        assert event.event_type == RegulatoryEventType.EVIDENCE_COLLECTED
        assert event.severity == "high"
        assert event.data["competitor_name"] == "EventTestCo"
        assert event.data["violation_id"] == str(violation.id)
        assert event.data["evidence_id"] == str(evidence_id)
        assert "screenshot_hash" in event.data
        assert "screenshot_path" in event.data


class TestBatchMixedResults:
    """13.7: Batch with mixed success/failure/skip results."""

    @pytest.mark.asyncio
    async def test_batch_continues_after_failure(
        self,
        integration_config,
        real_storage,
        mock_session,
        mock_violation_repo,
        mock_screenshot_service,
        mock_event_emitter,
    ):
        """One failure + one skip + one success → accurate statistics."""
        v_success = _make_violation(
            source_url="https://competitor.com/products",
            competitor_name="SuccessCo",
        )
        v_fail = _make_violation(
            source_url="https://competitor.com/fail",
            competitor_name="FailCo",
        )
        v_skip = _make_violation(
            source_url="https://competitor.com/skip",
            competitor_name="SkipCo",
        )

        mock_violation_repo.get_pending_evidence_collection.return_value = [
            v_success, v_fail, v_skip,
        ]

        evidence_repo = AsyncMock()
        # v_skip is already collected
        evidence_repo.get_collected_violation_ids = AsyncMock(
            return_value={v_skip.id}
        )
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        evidence_repo.create = AsyncMock(return_value=mock_evidence)
        evidence_repo.commit = AsyncMock()

        # First capture succeeds, second fails
        success_result = CaptureResult(
            screenshot_bytes=MINIMAL_PNG_BYTES,
            url="https://competitor.com/products",
            captured_at=datetime.now(UTC),
            page_title="Products",
            metadata={},
        )
        mock_screenshot_service.capture.side_effect = [
            success_result,
            RuntimeError("network timeout"),
        ]

        collector = EvidenceCollector(
            violation_repository=mock_violation_repo,
            evidence_repository=evidence_repo,
            screenshot_service=mock_screenshot_service,
            storage_service=real_storage,
            event_emitter=mock_event_emitter,
            config=integration_config,
        )

        result = await collector.execute()

        assert result.total_processed == 3
        assert result.collected == 1
        assert result.failed == 1
        assert result.skipped_already_collected == 1
        assert len(result.errors) == 1
        assert "network timeout" in result.errors[0]

        # Only one event emitted (for success)
        mock_event_emitter.emit.assert_called_once()

        # Success violation status updated
        assert v_success.evidence_status == EvidenceCollectionStatus.COLLECTED.value

        # Failed violation status unchanged (still pending)
        assert v_fail.evidence_status == "pending_collection"
