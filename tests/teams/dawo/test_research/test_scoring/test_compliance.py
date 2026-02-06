"""Tests for compliance adjustment component.

Tests:
    - ComplianceAdjuster class creation
    - COMPLIANT: +1 to final score (capped at 10)
    - WARNING: no adjustment
    - REJECTED: final score = 0 (override all)
    - Return adjustment value and rejection flag
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.scoring.components.compliance import (
    ComplianceAdjuster,
    ComplianceAdjustment,
    COMPLIANT_BONUS,
)


@pytest.fixture
def compliance_adjuster() -> ComplianceAdjuster:
    """ComplianceAdjuster instance."""
    return ComplianceAdjuster()


class TestComplianceAdjuster:
    """Tests for ComplianceAdjuster class."""

    def test_create_adjuster(self):
        """ComplianceAdjuster should be instantiable."""
        adjuster = ComplianceAdjuster()
        assert adjuster is not None

    def test_compliant_status_bonus(self, compliance_adjuster: ComplianceAdjuster):
        """COMPLIANT status should add +1 bonus."""
        item = _create_test_item(compliance_status=ComplianceStatus.COMPLIANT.value)

        result = compliance_adjuster.adjust(item)

        assert result.adjustment == COMPLIANT_BONUS  # +1
        assert result.is_rejected is False

    def test_warning_status_no_adjustment(self, compliance_adjuster: ComplianceAdjuster):
        """WARNING status should have no adjustment."""
        item = _create_test_item(compliance_status=ComplianceStatus.WARNING.value)

        result = compliance_adjuster.adjust(item)

        assert result.adjustment == 0.0
        assert result.is_rejected is False

    def test_rejected_status_zero_score(self, compliance_adjuster: ComplianceAdjuster):
        """REJECTED status should flag for zero score."""
        item = _create_test_item(compliance_status=ComplianceStatus.REJECTED.value)

        result = compliance_adjuster.adjust(item)

        assert result.is_rejected is True
        assert result.adjustment == 0.0

    def test_apply_bonus_capped_at_10(self, compliance_adjuster: ComplianceAdjuster):
        """Applying bonus to 10 should stay at 10."""
        base_score = 10.0

        final_score = compliance_adjuster.apply_adjustment(
            base_score,
            ComplianceAdjustment(adjustment=COMPLIANT_BONUS, is_rejected=False, notes="")
        )

        assert final_score == 10.0

    def test_apply_bonus_normal(self, compliance_adjuster: ComplianceAdjuster):
        """Applying bonus to 8 should yield 9."""
        base_score = 8.0

        final_score = compliance_adjuster.apply_adjustment(
            base_score,
            ComplianceAdjustment(adjustment=COMPLIANT_BONUS, is_rejected=False, notes="")
        )

        assert final_score == 9.0

    def test_apply_rejection_zeroes_score(self, compliance_adjuster: ComplianceAdjuster):
        """Rejected items should have score forced to 0."""
        base_score = 8.5

        final_score = compliance_adjuster.apply_adjustment(
            base_score,
            ComplianceAdjustment(adjustment=0.0, is_rejected=True, notes="")
        )

        assert final_score == 0.0

    def test_adjustment_includes_notes(self, compliance_adjuster: ComplianceAdjuster):
        """Adjustment should include explanatory notes."""
        item = _create_test_item(compliance_status=ComplianceStatus.COMPLIANT.value)

        result = compliance_adjuster.adjust(item)

        assert "compliant" in result.notes.lower()


class TestComplianceAdjustment:
    """Tests for ComplianceAdjustment dataclass."""

    def test_create_adjustment(self):
        """ComplianceAdjustment should be creatable."""
        adjustment = ComplianceAdjustment(
            adjustment=1.0,
            is_rejected=False,
            notes="COMPLIANT status",
        )

        assert adjustment.adjustment == 1.0
        assert adjustment.is_rejected is False
        assert adjustment.notes == "COMPLIANT status"


class TestComplianceConstants:
    """Tests for compliance adjustment constants."""

    def test_compliant_bonus(self):
        """COMPLIANT bonus should be +1."""
        assert COMPLIANT_BONUS == 1.0


def _create_test_item(compliance_status: str) -> dict:
    """Create a test research item dictionary.

    Args:
        compliance_status: Compliance status value.

    Returns:
        Dictionary with item data.
    """
    return {
        "id": uuid4(),
        "source": ResearchSource.REDDIT.value,
        "title": "Test article",
        "content": "Test content.",
        "url": "https://example.com/test",
        "tags": [],
        "source_metadata": {},
        "created_at": datetime.now(timezone.utc),
        "score": 0.0,
        "compliance_status": compliance_status,
    }
