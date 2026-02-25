"""Tests for violation detection schemas (Story 6-7, Task 4)."""

from uuid import uuid4

from teams.dawo.scanners.violation_detection.schemas import (
    AuthorizedClaimInfo,
    DetectionBatchResult,
    ViolationResult,
)


class TestViolationResult:
    """Tests for ViolationResult dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """ViolationResult can be created with all fields."""
        result = ViolationResult(
            extracted_claim_id=uuid4(),
            claim_text="treats brain fog",
            claim_category="treatment",
            confidence_score=92,
            violation_status="violation",
            severity="high",
            regulation_article="EC 1924/2006 Art. 10",
            violation_type="unauthorized_treatment_claim",
            detection_reasoning="Treatment claim prohibited under Art. 10.",
            authorized_claims_checked=50,
            nearest_authorized_claim=None,
            competitor_name="CompetitorA",
            source_url="https://example.com/post/123",
        )

        assert result.claim_text == "treats brain fog"
        assert result.violation_status == "violation"
        assert result.severity == "high"
        assert result.evidence_status == "pending_collection"

    def test_creation_with_nearest_authorized_claim_none(self) -> None:
        """ViolationResult works with None nearest_authorized_claim."""
        result = ViolationResult(
            extracted_claim_id=uuid4(),
            claim_text="boosts immunity",
            claim_category="enhancement",
            confidence_score=85,
            violation_status="violation",
            severity="medium",
            regulation_article="EC 1924/2006 Art. 13.1",
            violation_type="unauthorized_enhancement_claim",
            detection_reasoning="No authorized claim found.",
            authorized_claims_checked=0,
            nearest_authorized_claim=None,
            competitor_name="CompetitorB",
            source_url="https://example.com/page",
        )

        assert result.nearest_authorized_claim is None


class TestDetectionBatchResult:
    """Tests for DetectionBatchResult dataclass."""

    def test_creation_with_defaults(self) -> None:
        """DetectionBatchResult has sensible defaults."""
        result = DetectionBatchResult()

        assert result.total_processed == 0
        assert result.violations_found == 0
        assert result.suspects_found == 0
        assert result.compliant_found == 0
        assert result.skipped_already_evaluated == 0
        assert result.errors == 0


class TestAuthorizedClaimInfo:
    """Tests for AuthorizedClaimInfo dataclass."""

    def test_creation(self) -> None:
        """AuthorizedClaimInfo can be created with all fields."""
        info = AuthorizedClaimInfo(
            claim_id="EU-2012-001",
            substance="Vitamin D",
            claim_text="Vitamin D contributes to normal immune function",
            status="authorised",
            food_category="Vitamin D containing foods",
        )

        assert info.claim_id == "EU-2012-001"
        assert info.substance == "Vitamin D"
        assert info.food_category == "Vitamin D containing foods"

    def test_food_category_defaults_none(self) -> None:
        """food_category defaults to None."""
        info = AuthorizedClaimInfo(
            claim_id="EU-2012-002",
            substance="Zinc",
            claim_text="Zinc contributes to normal function of immune system",
            status="authorised",
        )

        assert info.food_category is None
