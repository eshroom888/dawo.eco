"""Tests for evidence collection schemas (Story 6-8, Task 4).

Tests DTOs, CaptureResult, CollectionBatchResult, and ImmutableEvidenceError.
"""

from datetime import UTC, datetime
from uuid import uuid4

from teams.dawo.scanners.evidence_collection.schemas import (
    CaptureResult,
    CollectionBatchResult,
    EvidenceCreateDTO,
    ImmutableEvidenceError,
)


class TestCaptureResult:
    """Tests for CaptureResult dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """CaptureResult can be created with all fields."""
        now = datetime.now(UTC)
        result = CaptureResult(
            screenshot_bytes=b"\x89PNG",
            url="https://example.com",
            captured_at=now,
            page_title="Test Page",
            metadata={"viewport": "1280x900"},
        )
        assert result.screenshot_bytes == b"\x89PNG"
        assert result.url == "https://example.com"
        assert result.captured_at == now
        assert result.page_title == "Test Page"
        assert result.metadata == {"viewport": "1280x900"}

    def test_default_metadata(self) -> None:
        """CaptureResult defaults metadata to empty dict."""
        result = CaptureResult(
            screenshot_bytes=b"",
            url="https://example.com",
            captured_at=datetime.now(UTC),
            page_title="",
        )
        assert result.metadata == {}


class TestEvidenceCreateDTO:
    """Tests for EvidenceCreateDTO dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """EvidenceCreateDTO can be created with all fields."""
        vid = uuid4()
        now = datetime.now(UTC)
        dto = EvidenceCreateDTO(
            violation_id=vid,
            competitor_name="CompetitorA",
            source_url="https://instagram.com/p/ABC123/",
            source_type="instagram_post",
            claim_text="treats brain fog",
            claim_category="treatment",
            violation_type="unauthorized_treatment_claim",
            severity="high",
            regulation_violated="EC 1924/2006 Art. 10",
            detection_reasoning="Treatment claim prohibited",
            confidence=0.92,
            screenshot_path="evidence/screenshots/2026-02/abc.png",
            screenshot_hash="abcd1234" * 8,
            screenshot_size_bytes=50000,
            captured_at=now,
            evidence_metadata={"page_title": "Post"},
        )
        assert dto.violation_id == vid
        assert dto.competitor_name == "CompetitorA"
        assert dto.confidence == 0.92

    def test_none_regulation_violated(self) -> None:
        """EvidenceCreateDTO accepts None for regulation_violated."""
        dto = EvidenceCreateDTO(
            violation_id=uuid4(),
            competitor_name="Test",
            source_url="https://example.com",
            source_type="website_page",
            claim_text="boosts immunity",
            claim_category="enhancement",
            violation_type="unauthorized_enhancement_claim",
            severity="medium",
            regulation_violated=None,
            detection_reasoning=None,
            confidence=0.75,
            screenshot_path="evidence/screenshots/2026-02/xyz.png",
            screenshot_hash="ef" * 32,
            screenshot_size_bytes=30000,
            captured_at=datetime.now(UTC),
        )
        assert dto.regulation_violated is None
        assert dto.detection_reasoning is None


class TestCollectionBatchResult:
    """Tests for CollectionBatchResult dataclass."""

    def test_creation_with_defaults(self) -> None:
        """CollectionBatchResult defaults all counters to 0."""
        result = CollectionBatchResult()
        assert result.total_processed == 0
        assert result.collected == 0
        assert result.failed == 0
        assert result.skipped_already_collected == 0
        assert result.errors == []


class TestImmutableEvidenceError:
    """Tests for ImmutableEvidenceError exception."""

    def test_is_value_error_subclass(self) -> None:
        """ImmutableEvidenceError is a ValueError subclass."""
        assert issubclass(ImmutableEvidenceError, ValueError)

    def test_can_be_raised_and_caught(self) -> None:
        """ImmutableEvidenceError can be raised with message."""
        try:
            raise ImmutableEvidenceError("Cannot modify evidence")
        except ValueError as e:
            assert "Cannot modify evidence" in str(e)
