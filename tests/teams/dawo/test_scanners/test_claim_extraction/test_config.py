"""Tests for HealthClaimExtractionConfig.

Story 6-6, Task 1: Extraction config and validation.
"""

import pytest

from teams.dawo.scanners.claim_extraction.config import (
    HealthClaimExtractionConfig,
    ClaimPattern,
    build_health_claim_extraction_config,
)


@pytest.fixture
def valid_config_data() -> dict:
    """Minimal valid config data for building HealthClaimExtractionConfig."""
    return {
        "enabled": True,
        "batch_size": 20,
        "confidence_threshold": 70,
        "max_claims_per_content": 10,
        "context_window_chars": 100,
        "use_llm": True,
        "prohibited_patterns": [
            {"pattern": "cures cancer", "category": "treatment", "language": "en"},
        ],
        "borderline_patterns": [
            {"pattern": "boosts immunity", "category": "enhancement", "language": "en"},
        ],
        "permitted_patterns": [
            {"pattern": "wellbeing", "category": "general_wellness", "language": "en"},
        ],
        "claim_categories": ["treatment", "prevention", "enhancement", "general_wellness"],
        "eu_article_mapping": {
            "treatment": "prohibited",
            "prevention": "14.1a",
            "enhancement": "13.1",
            "general_wellness": "13.1",
        },
    }


class TestClaimPattern:
    """Tests for ClaimPattern frozen dataclass."""

    def test_create_claim_pattern(self) -> None:
        pattern = ClaimPattern(pattern="cures cancer", category="treatment", language="en")
        assert pattern.pattern == "cures cancer"
        assert pattern.category == "treatment"
        assert pattern.language == "en"

    def test_claim_pattern_is_frozen(self) -> None:
        pattern = ClaimPattern(pattern="cures", category="treatment", language="en")
        with pytest.raises(AttributeError):
            pattern.pattern = "something else"  # type: ignore[misc]


class TestHealthClaimExtractionConfig:
    """Tests for HealthClaimExtractionConfig frozen dataclass."""

    def test_valid_config_creation(self, valid_config_data: dict) -> None:
        config = build_health_claim_extraction_config(valid_config_data)
        assert config.enabled is True
        assert config.batch_size == 20
        assert config.confidence_threshold == 70
        assert config.max_claims_per_content == 10
        assert config.context_window_chars == 100
        assert config.use_llm is True
        assert len(config.prohibited_patterns) == 1
        assert len(config.borderline_patterns) == 1
        assert len(config.permitted_patterns) == 1
        assert len(config.claim_categories) == 4
        assert config.eu_article_mapping["treatment"] == "prohibited"

    def test_empty_prohibited_patterns_raises(self, valid_config_data: dict) -> None:
        valid_config_data["prohibited_patterns"] = []
        with pytest.raises(ValueError, match="prohibited"):
            build_health_claim_extraction_config(valid_config_data)

    def test_invalid_confidence_threshold_too_high(self, valid_config_data: dict) -> None:
        valid_config_data["confidence_threshold"] = 101
        with pytest.raises(ValueError, match="confidence_threshold"):
            build_health_claim_extraction_config(valid_config_data)

    def test_invalid_confidence_threshold_negative(self, valid_config_data: dict) -> None:
        valid_config_data["confidence_threshold"] = -1
        with pytest.raises(ValueError, match="confidence_threshold"):
            build_health_claim_extraction_config(valid_config_data)

    def test_non_positive_batch_size(self, valid_config_data: dict) -> None:
        valid_config_data["batch_size"] = 0
        with pytest.raises(ValueError, match="batch_size"):
            build_health_claim_extraction_config(valid_config_data)

    def test_build_from_json_dict(self, valid_config_data: dict) -> None:
        config = build_health_claim_extraction_config(valid_config_data)
        assert isinstance(config, HealthClaimExtractionConfig)
        assert isinstance(config.prohibited_patterns[0], ClaimPattern)

    def test_default_values(self) -> None:
        config = HealthClaimExtractionConfig(
            prohibited_patterns=(
                ClaimPattern(pattern="cures", category="treatment", language="en"),
            ),
        )
        assert config.enabled is True
        assert config.batch_size == 20
        assert config.confidence_threshold == 70
        assert config.max_claims_per_content == 10
        assert config.context_window_chars == 100
        assert config.use_llm is True

    def test_frozen_immutability(self, valid_config_data: dict) -> None:
        config = build_health_claim_extraction_config(valid_config_data)
        with pytest.raises(AttributeError):
            config.batch_size = 50  # type: ignore[misc]
