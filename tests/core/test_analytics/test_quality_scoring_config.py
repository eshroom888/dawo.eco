"""Tests for quality scoring configuration.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 7.2: QualityScoringConfig frozen dataclass.
Task 7.3: Config wiring into get_config().

TDD RED phase: Tests written before implementation (already GREEN).
"""

from core.config import (
    CTRScale,
    Config,
    ConversionScale,
    QualityScoringConfig,
    get_config,
)


# === Task 7.2: QualityScoringConfig dataclass ===


class TestQualityScoringConfig:
    """Task 7.2: Frozen dataclass tests."""

    def test_default_variance_threshold(self) -> None:
        """Default variance threshold is 3.0."""
        cfg = QualityScoringConfig()
        assert cfg.variance_threshold == 3.0

    def test_default_min_posts_for_correlation(self) -> None:
        """Default min posts for correlation is 50."""
        cfg = QualityScoringConfig()
        assert cfg.min_posts_for_correlation == 50

    def test_default_scoring_delay_days(self) -> None:
        """Default scoring delay is 7 days."""
        cfg = QualityScoringConfig()
        assert cfg.scoring_delay_days == 7

    def test_default_weights_sum_to_one(self) -> None:
        """Default component weights sum to 1.0."""
        cfg = QualityScoringConfig()
        total = sum(cfg.weights.values())
        assert abs(total - 1.0) < 0.001

    def test_default_weights_have_five_components(self) -> None:
        """Default weights have all 5 components."""
        cfg = QualityScoringConfig()
        expected_keys = {
            "engagement_vs_avg",
            "reach_vs_avg",
            "click_through_rate",
            "conversions",
            "comment_sentiment",
        }
        assert set(cfg.weights.keys()) == expected_keys

    def test_ctr_scale_defaults(self) -> None:
        """CTRScale has correct defaults."""
        scale = CTRScale()
        assert scale.max_ctr_pct == 5.0
        assert scale.min_score == 1.0
        assert scale.max_score == 10.0

    def test_conversion_scale_defaults(self) -> None:
        """ConversionScale has correct defaults."""
        scale = ConversionScale()
        assert scale.max_orders == 5
        assert scale.min_score == 2.0
        assert scale.max_score == 10.0

    def test_frozen_immutability(self) -> None:
        """Config is frozen (immutable)."""
        cfg = QualityScoringConfig()
        try:
            cfg.variance_threshold = 5.0  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass  # Expected

    def test_custom_values(self) -> None:
        """Can construct with custom values."""
        cfg = QualityScoringConfig(
            variance_threshold=5.0,
            min_posts_for_correlation=100,
            scoring_delay_days=14,
        )
        assert cfg.variance_threshold == 5.0
        assert cfg.min_posts_for_correlation == 100
        assert cfg.scoring_delay_days == 14


# === Task 7.3: Config wiring ===


class TestConfigWiring:
    """Task 7.3: QualityScoringConfig wired into get_config()."""

    def test_config_has_quality_scoring(self) -> None:
        """Config dataclass has quality_scoring field."""
        cfg = Config()
        assert hasattr(cfg, "quality_scoring")
        assert isinstance(cfg.quality_scoring, QualityScoringConfig)

    def test_get_config_returns_quality_scoring(self) -> None:
        """get_config() includes quality_scoring."""
        cfg = get_config()
        assert isinstance(cfg.quality_scoring, QualityScoringConfig)

    def test_quality_scoring_in_module_all(self) -> None:
        """QualityScoringConfig is exported in __all__."""
        from core.config import __all__

        assert "QualityScoringConfig" in __all__
        assert "CTRScale" in __all__
        assert "ConversionScale" in __all__
