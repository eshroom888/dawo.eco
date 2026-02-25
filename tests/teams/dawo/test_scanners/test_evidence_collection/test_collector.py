"""Tests for EvidenceCollector orchestrator (Story 6-8, Task 8).

Tests full pipeline, idempotency, error handling, and batch results.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.regulatory.models import EvidenceCollectionStatus
from teams.dawo.scanners.evidence_collection.collector import EvidenceCollector
from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.schemas import CaptureResult

from .conftest import MINIMAL_PNG_BYTES


@pytest.fixture
def collector(
    mock_violation_repository,
    mock_evidence_repository,
    mock_screenshot_service,
    mock_storage_service,
    mock_event_emitter,
    sample_config,
) -> EvidenceCollector:
    """EvidenceCollector with all mocked dependencies."""
    return EvidenceCollector(
        violation_repository=mock_violation_repository,
        evidence_repository=mock_evidence_repository,
        screenshot_service=mock_screenshot_service,
        storage_service=mock_storage_service,
        event_emitter=mock_event_emitter,
        config=sample_config,
    )


class TestEvidenceCollectorExecute:
    """Tests for execute() orchestration."""

    async def test_full_pipeline(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        mock_storage_service,
        mock_event_emitter,
        sample_violation_pending,
    ) -> None:
        """Full pipeline: pending -> capture -> store -> create -> update -> emit."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()

        # Mock create to return an evidence with id
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        result = await collector.execute()

        assert result.total_processed == 1
        assert result.collected == 1
        assert result.failed == 0
        assert result.skipped_already_collected == 0
        mock_screenshot_service.capture.assert_called_once()
        mock_storage_service.store_screenshot.assert_called_once()
        mock_evidence_repository.create.assert_called_once()
        mock_event_emitter.emit.assert_called_once()
        mock_evidence_repository.commit.assert_called_once()

    async def test_idempotency_skips_collected(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        sample_violation_pending,
    ) -> None:
        """Already-collected violations are skipped."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = {
            sample_violation_pending.id
        }

        result = await collector.execute()

        assert result.skipped_already_collected == 1
        assert result.collected == 0

    async def test_instagram_url_uses_embed(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        sample_violation_pending,
    ) -> None:
        """Instagram URL is converted to embed URL before capture."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        await collector.execute()

        call_args = mock_screenshot_service.capture.call_args
        captured_url = call_args[0][0]
        assert "/embed/" in captured_url

    async def test_website_url_passed_through(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        sample_violation_website,
    ) -> None:
        """Website URL is passed through unchanged."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_website
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        await collector.execute()

        call_args = mock_screenshot_service.capture.call_args
        captured_url = call_args[0][0]
        assert captured_url == sample_violation_website.source_url

    async def test_per_violation_error_continues(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        sample_violation_pending,
        sample_violation_website,
    ) -> None:
        """One failure doesn't stop batch; others continue."""
        v1 = sample_violation_pending
        v2 = sample_violation_website
        mock_violation_repository.get_pending_evidence_collection.return_value = [v1, v2]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()

        # First capture fails, second succeeds
        mock_screenshot_service.capture.side_effect = [
            RuntimeError("timeout"),
            CaptureResult(
                screenshot_bytes=MINIMAL_PNG_BYTES,
                url=v2.source_url,
                captured_at=datetime.now(UTC),
                page_title="Website",
                metadata={},
            ),
        ]
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        result = await collector.execute()

        assert result.total_processed == 2
        assert result.collected == 1
        assert result.failed == 1
        assert len(result.errors) == 1

    async def test_batch_size_limiting(
        self,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        mock_storage_service,
        mock_event_emitter,
    ) -> None:
        """Respects config.batch_size."""
        config = EvidenceCollectionConfig(batch_size=2)
        collector = EvidenceCollector(
            violation_repository=mock_violation_repository,
            evidence_repository=mock_evidence_repository,
            screenshot_service=mock_screenshot_service,
            storage_service=mock_storage_service,
            event_emitter=mock_event_emitter,
            config=config,
        )

        violations = [MagicMock() for _ in range(5)]
        for v in violations:
            v.id = uuid4()
            v.source_url = "https://example.com"
            v.extracted_claim_id = uuid4()
        mock_violation_repository.get_pending_evidence_collection.return_value = violations
        mock_evidence_repository.get_collected_violation_ids.return_value = set()

        result = await collector.execute()
        assert result.total_processed == 2

    async def test_empty_pending_returns_empty_result(
        self, collector: EvidenceCollector, mock_violation_repository
    ) -> None:
        """No pending violations -> empty batch result."""
        mock_violation_repository.get_pending_evidence_collection.return_value = []
        result = await collector.execute()
        assert result.total_processed == 0
        assert result.collected == 0

    async def test_capture_failure_keeps_pending_status(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        sample_violation_pending,
    ) -> None:
        """Screenshot failure leaves violation as pending_collection."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()
        mock_screenshot_service.capture.side_effect = RuntimeError("network error")

        result = await collector.execute()

        assert result.failed == 1
        assert sample_violation_pending.evidence_status == "pending_collection"

    async def test_success_updates_evidence_status(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        sample_violation_pending,
    ) -> None:
        """Success updates violation evidence_status to 'collected'."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        await collector.execute()

        assert (
            sample_violation_pending.evidence_status
            == EvidenceCollectionStatus.COLLECTED.value
        )

    async def test_event_emitted_for_success(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_event_emitter,
        sample_violation_pending,
    ) -> None:
        """EVIDENCE_COLLECTED event emitted for each success."""
        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = set()
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        await collector.execute()

        mock_event_emitter.emit.assert_called_once()
        event = mock_event_emitter.emit.call_args[0][0]
        assert event.event_type.value == "evidence_collected"

    async def test_batch_result_statistics_accurate(
        self,
        collector: EvidenceCollector,
        mock_violation_repository,
        mock_evidence_repository,
        mock_screenshot_service,
        sample_violation_pending,
        sample_violation_website,
    ) -> None:
        """CollectionBatchResult statistics are accurate."""
        v_skip = MagicMock()
        v_skip.id = uuid4()

        mock_violation_repository.get_pending_evidence_collection.return_value = [
            sample_violation_pending,
            sample_violation_website,
            v_skip,
        ]
        mock_evidence_repository.get_collected_violation_ids.return_value = {v_skip.id}
        mock_evidence = MagicMock()
        mock_evidence.id = uuid4()
        mock_evidence_repository.create.return_value = mock_evidence

        result = await collector.execute()

        assert result.total_processed == 3
        assert result.collected == 2
        assert result.skipped_already_collected == 1
        assert result.failed == 0


class TestDetermineSourceType:
    """Tests for _determine_source_type static method."""

    def test_instagram_url(self) -> None:
        """Instagram URL returns 'instagram_post'."""
        assert (
            EvidenceCollector._determine_source_type(
                "https://www.instagram.com/p/ABC123/"
            )
            == "instagram_post"
        )

    def test_website_url(self) -> None:
        """Non-Instagram URL returns 'website_page'."""
        assert (
            EvidenceCollector._determine_source_type(
                "https://competitor.com/products"
            )
            == "website_page"
        )
