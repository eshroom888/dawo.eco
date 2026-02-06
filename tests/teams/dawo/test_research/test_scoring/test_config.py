"""Tests for scoring configuration schema.

Tests:
    - ScoringWeights dataclass creation and validation
    - ScoringConfig dataclass creation with component weights
    - Default weight values (relevance 25%, recency 20%, source_quality 25%, engagement 20%, compliance 10%)
    - Weight normalization (sum to 1.0)
    - Per-source weight overrides via ScoringWeights
"""

import pytest
from dataclasses import FrozenInstanceError

from teams.dawo.research.scoring.config import (
    ScoringConfig,
    ScoringWeights,
    DEFAULT_RELEVANCE_WEIGHT,
    DEFAULT_RECENCY_WEIGHT,
    DEFAULT_SOURCE_QUALITY_WEIGHT,
    DEFAULT_ENGAGEMENT_WEIGHT,
    DEFAULT_COMPLIANCE_WEIGHT,
)


class TestScoringWeights:
    """Tests for ScoringWeights dataclass."""

    def test_create_with_defaults(self):
        """ScoringWeights should have sensible defaults."""
        weights = ScoringWeights()

        assert weights.relevance == DEFAULT_RELEVANCE_WEIGHT
        assert weights.recency == DEFAULT_RECENCY_WEIGHT
        assert weights.source_quality == DEFAULT_SOURCE_QUALITY_WEIGHT
        assert weights.engagement == DEFAULT_ENGAGEMENT_WEIGHT
        assert weights.compliance == DEFAULT_COMPLIANCE_WEIGHT

    def test_create_with_custom_values(self):
        """ScoringWeights should accept custom weight values."""
        weights = ScoringWeights(
            relevance=0.30,
            recency=0.15,
            source_quality=0.30,
            engagement=0.15,
            compliance=0.10,
        )

        assert weights.relevance == 0.30
        assert weights.recency == 0.15
        assert weights.source_quality == 0.30
        assert weights.engagement == 0.15
        assert weights.compliance == 0.10

    def test_weights_sum_to_one(self):
        """Default weights should sum to 1.0."""
        weights = ScoringWeights()
        total = (
            weights.relevance
            + weights.recency
            + weights.source_quality
            + weights.engagement
            + weights.compliance
        )

        assert abs(total - 1.0) < 0.001  # Allow small float tolerance

    def test_weights_are_immutable(self):
        """ScoringWeights should be frozen (immutable)."""
        weights = ScoringWeights()

        with pytest.raises(FrozenInstanceError):
            weights.relevance = 0.5

    def test_weights_validation_negative_values(self):
        """ScoringWeights should reject negative weight values."""
        with pytest.raises(ValueError, match="must be non-negative"):
            ScoringWeights(relevance=-0.1)

    def test_weights_validation_exceeds_one(self):
        """ScoringWeights should reject individual weights > 1.0."""
        with pytest.raises(ValueError, match="cannot exceed 1.0"):
            ScoringWeights(relevance=1.5)


class TestScoringConfig:
    """Tests for ScoringConfig dataclass."""

    def test_create_with_defaults(self):
        """ScoringConfig should create with default weights."""
        config = ScoringConfig()

        assert isinstance(config.weights, ScoringWeights)
        assert config.source_overrides == {}

    def test_create_with_custom_weights(self):
        """ScoringConfig should accept custom ScoringWeights."""
        custom_weights = ScoringWeights(
            relevance=0.30,
            recency=0.10,
            source_quality=0.30,
            engagement=0.20,
            compliance=0.10,
        )
        config = ScoringConfig(weights=custom_weights)

        assert config.weights.relevance == 0.30
        assert config.weights.recency == 0.10

    def test_create_with_source_overrides(self):
        """ScoringConfig should support per-source weight overrides."""
        reddit_weights = ScoringWeights(
            relevance=0.20,
            recency=0.25,
            source_quality=0.20,
            engagement=0.30,  # Higher engagement weight for Reddit
            compliance=0.05,
        )

        config = ScoringConfig(
            source_overrides={"reddit": reddit_weights}
        )

        assert "reddit" in config.source_overrides
        assert config.source_overrides["reddit"].engagement == 0.30

    def test_get_weights_for_source_with_override(self):
        """get_weights_for_source should return override when available."""
        reddit_weights = ScoringWeights(engagement=0.35, relevance=0.20, recency=0.15, source_quality=0.20, compliance=0.10)
        config = ScoringConfig(source_overrides={"reddit": reddit_weights})

        weights = config.get_weights_for_source("reddit")

        assert weights.engagement == 0.35

    def test_get_weights_for_source_without_override(self):
        """get_weights_for_source should return default weights when no override."""
        config = ScoringConfig()

        weights = config.get_weights_for_source("pubmed")

        assert weights.relevance == DEFAULT_RELEVANCE_WEIGHT

    def test_config_from_dict(self):
        """ScoringConfig should be creatable from dictionary."""
        config_dict = {
            "weights": {
                "relevance": 0.25,
                "recency": 0.20,
                "source_quality": 0.25,
                "engagement": 0.20,
                "compliance": 0.10,
            },
            "source_overrides": {
                "reddit": {
                    "relevance": 0.20,
                    "recency": 0.20,
                    "source_quality": 0.20,
                    "engagement": 0.30,
                    "compliance": 0.10,
                }
            }
        }

        config = ScoringConfig.from_dict(config_dict)

        assert config.weights.relevance == 0.25
        assert config.source_overrides["reddit"].engagement == 0.30


class TestDefaultWeightConstants:
    """Tests for default weight constants."""

    def test_default_relevance_weight(self):
        """Default relevance weight should be 25%."""
        assert DEFAULT_RELEVANCE_WEIGHT == 0.25

    def test_default_recency_weight(self):
        """Default recency weight should be 20%."""
        assert DEFAULT_RECENCY_WEIGHT == 0.20

    def test_default_source_quality_weight(self):
        """Default source quality weight should be 25%."""
        assert DEFAULT_SOURCE_QUALITY_WEIGHT == 0.25

    def test_default_engagement_weight(self):
        """Default engagement weight should be 20%."""
        assert DEFAULT_ENGAGEMENT_WEIGHT == 0.20

    def test_default_compliance_weight(self):
        """Default compliance weight should be 10%."""
        assert DEFAULT_COMPLIANCE_WEIGHT == 0.10

    def test_all_defaults_sum_to_one(self):
        """All default weights should sum to 1.0."""
        total = (
            DEFAULT_RELEVANCE_WEIGHT
            + DEFAULT_RECENCY_WEIGHT
            + DEFAULT_SOURCE_QUALITY_WEIGHT
            + DEFAULT_ENGAGEMENT_WEIGHT
            + DEFAULT_COMPLIANCE_WEIGHT
        )

        assert abs(total - 1.0) < 0.001
