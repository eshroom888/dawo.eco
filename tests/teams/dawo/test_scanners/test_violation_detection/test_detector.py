"""Tests for ViolationDetector (Story 6-7, Task 7)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.regulatory.events import RegulatoryEventType
from teams.dawo.scanners.violation_detection.classifier import ViolationClassifier
from teams.dawo.scanners.violation_detection.detector import ViolationDetector
from teams.dawo.scanners.violation_detection.schemas import (
    DetectionBatchResult,
    ViolationResult,
)


def _make_violation_result(status: str = "violation", **kwargs) -> ViolationResult:
    """Create a ViolationResult with defaults."""
    defaults = {
        "extracted_claim_id": uuid4(),
        "claim_text": "test claim",
        "claim_category": "treatment",
        "confidence_score": 90,
        "violation_status": status,
        "severity": "high",
        "regulation_article": "EC 1924/2006 Art. 10",
        "violation_type": "unauthorized_treatment_claim",
        "detection_reasoning": "Test reasoning.",
        "authorized_claims_checked": 0,
        "nearest_authorized_claim": None,
        "competitor_name": "TestCompetitor",
        "source_url": "https://test.com",
        "evidence_status": "pending_collection",
    }
    defaults.update(kwargs)
    return ViolationResult(**defaults)


class TestViolationDetector:
    """Tests for ViolationDetector engine."""

    @pytest.fixture
    def mock_claim_repo(self):
        repo = AsyncMock()
        repo.get_high_confidence_claims = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_health_claims_repo(self):
        repo = AsyncMock()
        snapshot = MagicMock()
        snapshot.id = uuid4()
        repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        repo.get_relevant_claims = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_violation_repo(self):
        repo = AsyncMock()
        repo.get_evaluated_claim_ids = AsyncMock(return_value=set())
        repo.save_violations_batch = AsyncMock(return_value=0)
        repo.commit = AsyncMock()
        return repo

    @pytest.fixture
    def mock_classifier(self, sample_config):
        return ViolationClassifier(config=sample_config)

    @pytest.fixture
    def detector(
        self,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_classifier,
        mock_event_emitter,
        sample_config,
    ):
        return ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=mock_classifier,
            event_emitter=mock_event_emitter,
            config=sample_config,
        )

    @pytest.mark.asyncio
    async def test_full_pipeline(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_treatment_claim,
    ) -> None:
        """Full pipeline: claims → classify → save → events emitted."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim
        ]
        mock_violation_repo.save_violations_batch.return_value = 1

        result = await detector.execute()

        assert isinstance(result, DetectionBatchResult)
        assert result.total_processed == 1
        assert result.violations_found == 1
        mock_violation_repo.save_violations_batch.assert_awaited_once()
        mock_event_emitter.emit.assert_awaited()
        mock_violation_repo.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotency_skips_evaluated(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        sample_treatment_claim,
    ) -> None:
        """Already-evaluated claims are skipped."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim
        ]
        mock_violation_repo.get_evaluated_claim_ids.return_value = {
            sample_treatment_claim.id
        }

        result = await detector.execute()

        assert result.skipped_already_evaluated == 1
        assert result.total_processed == 0

    @pytest.mark.asyncio
    async def test_treatment_violation_event(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_treatment_claim,
    ) -> None:
        """Treatment VIOLATION emits EU_VIOLATION_DETECTED event."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim
        ]
        mock_violation_repo.save_violations_batch.return_value = 1

        await detector.execute()

        # Check that at least one emit call had EU_VIOLATION_DETECTED
        calls = mock_event_emitter.emit.call_args_list
        event_types = [
            call.args[0].event_type for call in calls
        ]
        assert RegulatoryEventType.EU_VIOLATION_DETECTED in event_types

    @pytest.mark.asyncio
    async def test_wellness_suspect_event(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_wellness_claim,
    ) -> None:
        """General wellness SUSPECT emits SUSPECT_CLAIM_FLAGGED event."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_wellness_claim
        ]
        mock_violation_repo.save_violations_batch.return_value = 1

        await detector.execute()

        calls = mock_event_emitter.emit.call_args_list
        event_types = [
            call.args[0].event_type for call in calls
        ]
        assert RegulatoryEventType.SUSPECT_CLAIM_FLAGGED in event_types

    @pytest.mark.asyncio
    async def test_no_claims_empty_result(
        self,
        detector,
        mock_claim_repo,
        mock_event_emitter,
    ) -> None:
        """No high-confidence claims → empty batch result, no events."""
        mock_claim_repo.get_high_confidence_claims.return_value = []

        result = await detector.execute()

        assert result.total_processed == 0
        assert result.violations_found == 0
        mock_event_emitter.emit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_eu_register_unavailable(
        self,
        detector,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        sample_treatment_claim,
    ) -> None:
        """EU register unavailable → classify with empty authorized list."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim
        ]
        mock_health_claims_repo.get_latest_snapshot.return_value = None
        mock_violation_repo.save_violations_batch.return_value = 1

        result = await detector.execute()

        # Should still work — treatment claims are always violations
        assert result.violations_found == 1

    @pytest.mark.asyncio
    async def test_per_claim_error_handling(
        self,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_config,
        sample_treatment_claim,
        sample_enhancement_claim,
    ) -> None:
        """Per-claim error: one fails, others continue."""
        # Create a classifier that raises on the first claim
        bad_classifier = MagicMock(spec=ViolationClassifier)
        good_result = _make_violation_result(status="violation")

        bad_classifier.classify = MagicMock(
            side_effect=[RuntimeError("classify failed"), good_result]
        )

        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim,
            sample_enhancement_claim,
        ]
        mock_violation_repo.save_violations_batch.return_value = 1

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=bad_classifier,
            event_emitter=mock_event_emitter,
            config=sample_config,
        )

        result = await detector.execute()

        assert result.errors == 1
        assert result.total_processed == 1

    @pytest.mark.asyncio
    async def test_batch_result_statistics(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_treatment_claim,
        sample_wellness_claim,
    ) -> None:
        """DetectionBatchResult statistics are accurate."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim,
            sample_wellness_claim,
        ]
        mock_violation_repo.save_violations_batch.return_value = 2

        result = await detector.execute()

        assert result.total_processed == 2
        assert result.violations_found == 1
        assert result.suspects_found == 1

    @pytest.mark.asyncio
    async def test_enhancement_violation_event(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_enhancement_claim,
    ) -> None:
        """Enhancement VIOLATION emits EU_VIOLATION_DETECTED event."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_enhancement_claim
        ]
        mock_violation_repo.save_violations_batch.return_value = 1

        await detector.execute()

        calls = mock_event_emitter.emit.call_args_list
        event_types = [
            call.args[0].event_type for call in calls
        ]
        assert RegulatoryEventType.EU_VIOLATION_DETECTED in event_types

    @pytest.mark.asyncio
    async def test_competitor_info_from_claim_relationship(
        self,
        detector,
        mock_claim_repo,
        mock_violation_repo,
        mock_event_emitter,
        sample_treatment_claim,
    ) -> None:
        """Competitor name/source_url from claim.competitor_content."""
        mock_claim_repo.get_high_confidence_claims.return_value = [
            sample_treatment_claim
        ]
        mock_violation_repo.save_violations_batch.return_value = 1

        await detector.execute()

        # Verify save was called with results containing competitor info
        save_call = mock_violation_repo.save_violations_batch.call_args
        results = save_call.args[0]
        assert results[0].competitor_name == "CompetitorA"
        assert results[0].source_url == "https://instagram.com/p/abc123"

    @pytest.mark.asyncio
    async def test_batch_size_limiting(
        self,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ) -> None:
        """Respects config.batch_size — processes at most batch_size claims."""
        from tests.teams.dawo.test_scanners.test_violation_detection.conftest import (
            _make_claim,
        )

        from teams.dawo.scanners.violation_detection.config import (
            build_violation_detection_config,
        )

        config = build_violation_detection_config({
            "batch_size": 2,
            "min_confidence": 70,
            "auto_violation_categories": ["treatment"],
            "register_check_categories": ["prevention", "enhancement"],
            "suspect_categories": ["general_wellness"],
            "severity_mapping": {
                "treatment": "high",
                "prevention": "high",
                "enhancement": "medium",
                "general_wellness": "low",
            },
            "regulation_mapping": {
                "treatment": "EC 1924/2006 Art. 10",
                "prevention": "EC 1924/2006 Art. 14.1a",
                "enhancement": "EC 1924/2006 Art. 13.1",
                "general_wellness": "EC 1924/2006 Art. 13.1",
            },
            "mushroom_substances": ["reishi"],
        })

        # Provide 5 claims but batch_size=2 → only 2 should be processed
        claims = [
            _make_claim(
                "treatment", 90, f"claim {i}", f"reishi claim {i}",
                f"Competitor{i}", f"https://example.com/{i}",
            )
            for i in range(5)
        ]
        mock_claim_repo.get_high_confidence_claims.return_value = claims

        classifier = ViolationClassifier(config=config)
        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=classifier,
            event_emitter=mock_event_emitter,
            config=config,
        )

        result = await detector.execute()

        # Only batch_size (2) claims should be processed, not all 5
        assert result.total_processed == 2
        saved = mock_violation_repo.save_violations_batch.call_args[0][0]
        assert len(saved) == 2
