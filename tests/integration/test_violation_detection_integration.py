"""Integration tests for EU violation detection pipeline.

Story 6-7, Task 11: End-to-end integration tests.

Tests the full flow from config → classifier → detector → repository →
event emission, verifying all components work together correctly.
Uses real classifier with mock repositories.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.regulatory.events import RegulatoryEventType
from core.regulatory.models import (
    ClaimStatus,
    CompetitorContent,
    ExtractedHealthClaim,
    HealthClaim,
)
from teams.dawo.scanners.violation_detection.classifier import ViolationClassifier
from teams.dawo.scanners.violation_detection.config import (
    build_violation_detection_config,
)
from teams.dawo.scanners.violation_detection.detector import ViolationDetector
from teams.dawo.scanners.violation_detection.schemas import DetectionBatchResult


@pytest.fixture
def full_config():
    """Realistic config matching production settings."""
    return build_violation_detection_config({
        "enabled": True,
        "batch_size": 50,
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
        "mushroom_substances": [
            "reishi", "lion's mane", "chaga", "cordyceps",
            "turkey tail", "maitake", "shiitake",
        ],
    })


@pytest.fixture
def real_classifier(full_config):
    """Real ViolationClassifier with full config."""
    return ViolationClassifier(config=full_config)


def _make_claim(
    category: str,
    confidence: int,
    claim_text: str,
    context: str,
    competitor_name: str,
    source_url: str,
) -> MagicMock:
    """Create a mock ExtractedHealthClaim with competitor_content relationship."""
    claim = MagicMock(spec=ExtractedHealthClaim)
    claim.id = uuid4()
    claim.claim_text = claim_text
    claim.claim_category = category
    claim.confidence_score = confidence
    claim.surrounding_context = context

    content = MagicMock(spec=CompetitorContent)
    content.competitor_name = competitor_name
    content.source_url = source_url
    claim.competitor_content = content
    return claim


@pytest.fixture
def mock_claim_repo():
    repo = AsyncMock()
    repo.get_high_confidence_claims = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_health_claims_repo():
    repo = AsyncMock()
    repo.get_latest_snapshot = AsyncMock(return_value=None)
    repo.get_relevant_claims = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_violation_repo():
    repo = AsyncMock()
    repo.get_evaluated_claim_ids = AsyncMock(return_value=set())
    repo.save_violations_batch = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_event_emitter():
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter


class TestFullPipeline:
    """11.1: Full pipeline with mixed claim types."""

    @pytest.mark.asyncio
    async def test_mixed_claims_classified_and_saved(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """Treatment + enhancement + wellness → violations + suspect saved."""
        treatment = _make_claim(
            "treatment", 92, "treats brain fog",
            "Lion's mane treats brain fog naturally",
            "CompetitorA", "https://example.com/a",
        )
        enhancement = _make_claim(
            "enhancement", 85, "boosts cognitive function",
            "Lion's mane boosts cognitive function",
            "CompetitorB", "https://example.com/b",
        )
        wellness = _make_claim(
            "general_wellness", 72, "supports overall wellbeing",
            "Reishi mushroom supports overall wellbeing",
            "CompetitorC", "https://example.com/c",
        )
        mock_claim_repo.get_high_confidence_claims.return_value = [
            treatment, enhancement, wellness,
        ]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await detector.execute()

        assert isinstance(result, DetectionBatchResult)
        assert result.total_processed == 3
        assert result.violations_found == 2  # treatment + enhancement
        assert result.suspects_found == 1    # wellness
        assert result.compliant_found == 0
        assert result.errors == 0

        # All 3 results saved in batch
        mock_violation_repo.save_violations_batch.assert_awaited_once()
        saved = mock_violation_repo.save_violations_batch.call_args[0][0]
        assert len(saved) == 3

        # Commit called
        mock_violation_repo.commit.assert_awaited_once()


class TestIdempotency:
    """11.2: Second run skips already-evaluated claims."""

    @pytest.mark.asyncio
    async def test_second_run_skips_all(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """Run once → 1 violation. Run again → 0 new (all skipped)."""
        claim = _make_claim(
            "treatment", 92, "treats brain fog",
            "Lion's mane treats brain fog",
            "CompetitorA", "https://example.com/a",
        )
        claim_id = claim.id
        mock_claim_repo.get_high_confidence_claims.return_value = [claim]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        # First run: no evaluated IDs yet
        result1 = await detector.execute()
        assert result1.violations_found == 1
        assert result1.skipped_already_evaluated == 0

        # Second run: claim_id is now in evaluated set
        mock_violation_repo.get_evaluated_claim_ids.return_value = {claim_id}
        mock_violation_repo.save_violations_batch.reset_mock()
        mock_event_emitter.emit.reset_mock()

        result2 = await detector.execute()
        assert result2.violations_found == 0
        assert result2.skipped_already_evaluated == 1
        mock_violation_repo.save_violations_batch.assert_not_awaited()
        mock_event_emitter.emit.assert_not_awaited()


class TestTreatmentAutoViolation:
    """11.3: Treatment claim → auto-violation path."""

    @pytest.mark.asyncio
    async def test_treatment_high_severity_art10(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """Treatment claim → VIOLATION, HIGH severity, Art. 10."""
        claim = _make_claim(
            "treatment", 95, "cures brain fog",
            "Our lion's mane extract cures brain fog",
            "CompetitorA", "https://example.com/a",
        )
        mock_claim_repo.get_high_confidence_claims.return_value = [claim]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await detector.execute()

        assert result.violations_found == 1
        saved = mock_violation_repo.save_violations_batch.call_args[0][0]
        violation = saved[0]
        assert violation.violation_status == "violation"
        assert violation.severity == "high"
        assert "Art. 10" in violation.regulation_article
        assert violation.violation_type == "unauthorized_treatment_claim"
        # Auto-violation skips register check
        assert violation.authorized_claims_checked == 0


class TestRegisterCrossReference:
    """11.4: Enhancement claim + empty authorized list → VIOLATION."""

    @pytest.mark.asyncio
    async def test_enhancement_no_authorized_claims_violation(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """Enhancement claim with no matching authorized claims → VIOLATION."""
        claim = _make_claim(
            "enhancement", 85, "boosts immune system",
            "Chaga boosts immune system naturally",
            "CompetitorB", "https://example.com/b",
        )
        mock_claim_repo.get_high_confidence_claims.return_value = [claim]

        # EU register has Vitamin D claims but nothing for mushrooms
        snapshot = MagicMock()
        snapshot.id = uuid4()
        mock_health_claims_repo.get_latest_snapshot.return_value = snapshot

        vitamin_d = MagicMock(spec=HealthClaim)
        vitamin_d.substance = "Vitamin D"
        vitamin_d.claim_text = "Vitamin D contributes to immune function"
        mock_health_claims_repo.get_relevant_claims.return_value = [vitamin_d]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await detector.execute()

        assert result.violations_found == 1
        saved = mock_violation_repo.save_violations_batch.call_args[0][0]
        violation = saved[0]
        assert violation.violation_status == "violation"
        assert violation.severity == "medium"
        assert "Art. 13.1" in violation.regulation_article
        assert violation.authorized_claims_checked == 1


class TestSuspectClassification:
    """11.5: General wellness claim → SUSPECT with LOW severity."""

    @pytest.mark.asyncio
    async def test_wellness_suspect_low_severity(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """General wellness claim → SUSPECT, LOW severity, reasoning documented."""
        claim = _make_claim(
            "general_wellness", 72, "supports overall wellbeing",
            "Reishi mushroom supports overall wellbeing and balance",
            "CompetitorC", "https://example.com/c",
        )
        mock_claim_repo.get_high_confidence_claims.return_value = [claim]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        result = await detector.execute()

        assert result.suspects_found == 1
        assert result.violations_found == 0
        saved = mock_violation_repo.save_violations_batch.call_args[0][0]
        suspect = saved[0]
        assert suspect.violation_status == "suspect"
        assert suspect.severity == "low"
        assert suspect.detection_reasoning  # Not empty
        assert "borderline" in suspect.detection_reasoning.lower()


class TestEventEmissionIntegration:
    """11.6: VIOLATION → EU_VIOLATION_DETECTED, SUSPECT → SUSPECT_CLAIM_FLAGGED."""

    @pytest.mark.asyncio
    async def test_violation_and_suspect_events(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """Treatment violation emits EU_VIOLATION_DETECTED, wellness emits SUSPECT_CLAIM_FLAGGED."""
        treatment = _make_claim(
            "treatment", 92, "cures brain fog",
            "Lion's mane cures brain fog",
            "CompetitorA", "https://example.com/a",
        )
        wellness = _make_claim(
            "general_wellness", 72, "supports wellbeing",
            "Reishi supports wellbeing",
            "CompetitorC", "https://example.com/c",
        )
        mock_claim_repo.get_high_confidence_claims.return_value = [
            treatment, wellness,
        ]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        await detector.execute()

        # 2 events: 1 violation + 1 suspect
        assert mock_event_emitter.emit.await_count == 2

        events = [
            call.args[0] for call in mock_event_emitter.emit.call_args_list
        ]
        event_types = {e.event_type for e in events}
        assert RegulatoryEventType.EU_VIOLATION_DETECTED in event_types
        assert RegulatoryEventType.SUSPECT_CLAIM_FLAGGED in event_types

        # Verify violation event data
        violation_event = next(
            e for e in events
            if e.event_type == RegulatoryEventType.EU_VIOLATION_DETECTED
        )
        assert violation_event.severity == "high"
        assert violation_event.data["competitor_name"] == "CompetitorA"
        assert violation_event.data["claim_text"] == "cures brain fog"

        # Verify suspect event data
        suspect_event = next(
            e for e in events
            if e.event_type == RegulatoryEventType.SUSPECT_CLAIM_FLAGGED
        )
        assert suspect_event.severity == "low"
        assert suspect_event.data["competitor_name"] == "CompetitorC"


class TestEvidenceStatusHandoff:
    """11.7: VIOLATION records have evidence_status='pending_collection'."""

    @pytest.mark.asyncio
    async def test_violations_have_pending_collection(
        self,
        full_config,
        real_classifier,
        mock_claim_repo,
        mock_health_claims_repo,
        mock_violation_repo,
        mock_event_emitter,
    ):
        """All violations set evidence_status to 'pending_collection' for Story 6-8."""
        treatment = _make_claim(
            "treatment", 92, "treats brain fog",
            "Lion's mane treats brain fog",
            "CompetitorA", "https://example.com/a",
        )
        enhancement = _make_claim(
            "enhancement", 85, "boosts focus",
            "Lion's mane boosts focus",
            "CompetitorB", "https://example.com/b",
        )
        wellness = _make_claim(
            "general_wellness", 72, "supports wellbeing",
            "Reishi supports wellbeing",
            "CompetitorC", "https://example.com/c",
        )
        mock_claim_repo.get_high_confidence_claims.return_value = [
            treatment, enhancement, wellness,
        ]

        detector = ViolationDetector(
            claim_repository=mock_claim_repo,
            health_claims_repository=mock_health_claims_repo,
            violation_repository=mock_violation_repo,
            classifier=real_classifier,
            event_emitter=mock_event_emitter,
            config=full_config,
        )

        await detector.execute()

        saved = mock_violation_repo.save_violations_batch.call_args[0][0]
        for result in saved:
            assert result.evidence_status == "pending_collection", (
                f"Expected 'pending_collection' for {result.violation_status} "
                f"claim, got '{result.evidence_status}'"
            )
