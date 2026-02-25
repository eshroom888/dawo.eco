"""Tests for ViolationClassifier (Story 6-7, Task 5)."""

from unittest.mock import MagicMock

import pytest

from core.regulatory.models import HealthClaim
from teams.dawo.scanners.violation_detection.classifier import ViolationClassifier
from teams.dawo.scanners.violation_detection.schemas import ViolationResult


class TestViolationClassifier:
    """Tests for ViolationClassifier classification logic."""

    def test_treatment_claim_auto_violation(
        self, sample_config, sample_treatment_claim
    ) -> None:
        """Treatment claim is always VIOLATION with HIGH severity, Art. 10."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_treatment_claim,
            authorized_claims=[],
            competitor_name="CompetitorA",
            source_url="https://instagram.com/p/abc123",
        )

        assert result.violation_status == "violation"
        assert result.severity == "high"
        assert "Art. 10" in result.regulation_article
        assert result.violation_type == "unauthorized_treatment_claim"
        assert result.evidence_status == "pending_collection"

    def test_prevention_claim_no_authorized_violation(
        self, sample_config, sample_prevention_claim, sample_authorized_claims
    ) -> None:
        """Prevention claim with no matching authorized claim is VIOLATION."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_prevention_claim,
            authorized_claims=sample_authorized_claims,
            competitor_name="CompetitorD",
            source_url="https://competitor-d.com/reishi",
        )

        assert result.violation_status == "violation"
        assert result.severity == "high"
        assert "Art. 14.1a" in result.regulation_article

    def test_enhancement_claim_no_authorized_violation(
        self, sample_config, sample_enhancement_claim, sample_authorized_claims
    ) -> None:
        """Enhancement claim with no matching authorized claim is VIOLATION."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_enhancement_claim,
            authorized_claims=sample_authorized_claims,
            competitor_name="CompetitorB",
            source_url="https://competitor-b.com/products/lions-mane",
        )

        assert result.violation_status == "violation"
        assert result.severity == "medium"
        assert "Art. 13.1" in result.regulation_article

    def test_wellness_claim_suspect(
        self, sample_config, sample_wellness_claim
    ) -> None:
        """General wellness claim is SUSPECT with LOW severity."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_wellness_claim,
            authorized_claims=[],
            competitor_name="CompetitorC",
            source_url="https://competitor-c.com/blog/reishi",
        )

        assert result.violation_status == "suspect"
        assert result.severity == "low"
        assert "Art. 13.1" in result.regulation_article
        assert result.evidence_status == "pending_collection"

    def test_reasoning_includes_claim_text_and_regulation(
        self, sample_config, sample_treatment_claim
    ) -> None:
        """Detection reasoning includes claim text and regulation reference."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_treatment_claim,
            authorized_claims=[],
            competitor_name="CompetitorA",
            source_url="https://instagram.com/p/abc123",
        )

        assert "treats brain fog" in result.detection_reasoning
        assert "1924/2006" in result.detection_reasoning

    def test_violation_type_format(
        self, sample_config, sample_enhancement_claim, sample_authorized_claims
    ) -> None:
        """violation_type follows 'unauthorized_{category}_claim' format."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_enhancement_claim,
            authorized_claims=sample_authorized_claims,
            competitor_name="CompetitorB",
            source_url="https://competitor-b.com/products/lions-mane",
        )

        assert result.violation_type == "unauthorized_enhancement_claim"

    def test_authorized_claims_checked_count(
        self, sample_config, sample_enhancement_claim, sample_authorized_claims
    ) -> None:
        """authorized_claims_checked matches input list length."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_enhancement_claim,
            authorized_claims=sample_authorized_claims,
            competitor_name="CompetitorB",
            source_url="https://competitor-b.com/products/lions-mane",
        )

        assert result.authorized_claims_checked == len(sample_authorized_claims)

    def test_nearest_authorized_claim_populated_when_match(
        self, sample_config, sample_enhancement_claim
    ) -> None:
        """nearest_authorized_claim populated when substance match found."""
        # Create an authorized claim that contains "lion" to match
        authorized = MagicMock(spec=HealthClaim)
        authorized.substance = "Lion's Mane Extract"
        authorized.claim_text = "No authorized claims"
        authorized.status = "authorised"

        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_enhancement_claim,
            authorized_claims=[authorized],
            competitor_name="CompetitorB",
            source_url="https://competitor-b.com/products/lions-mane",
        )

        # Should find "lion's mane" match
        assert result.nearest_authorized_claim is not None

    def test_nearest_authorized_claim_none_when_no_match(
        self, sample_config, sample_enhancement_claim, sample_authorized_claims
    ) -> None:
        """nearest_authorized_claim is None when no substance match."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_enhancement_claim,
            authorized_claims=sample_authorized_claims,  # Only Vitamin D
            competitor_name="CompetitorB",
            source_url="https://competitor-b.com/products/lions-mane",
        )

        assert result.nearest_authorized_claim is None

    def test_extract_substance_keywords_matches_known_mushrooms(
        self, sample_config, sample_treatment_claim
    ) -> None:
        """_extract_substance_keywords matches known mushroom substances."""
        classifier = ViolationClassifier(config=sample_config)

        keywords = classifier._extract_substance_keywords(sample_treatment_claim)

        # "lion's mane" appears in surrounding_context
        assert "lion's mane" in keywords

    def test_competitor_info_populated(
        self, sample_config, sample_treatment_claim
    ) -> None:
        """competitor_name and source_url populated from input."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_treatment_claim,
            authorized_claims=[],
            competitor_name="CompetitorA",
            source_url="https://instagram.com/p/abc123",
        )

        assert result.competitor_name == "CompetitorA"
        assert result.source_url == "https://instagram.com/p/abc123"

    def test_returns_violation_result_type(
        self, sample_config, sample_treatment_claim
    ) -> None:
        """classify() returns a ViolationResult instance."""
        classifier = ViolationClassifier(config=sample_config)

        result = classifier.classify(
            claim=sample_treatment_claim,
            authorized_claims=[],
            competitor_name="CompetitorA",
            source_url="https://instagram.com/p/abc123",
        )

        assert isinstance(result, ViolationResult)
