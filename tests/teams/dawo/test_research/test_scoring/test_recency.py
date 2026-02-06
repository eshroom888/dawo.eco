"""Tests for recency scoring component.

Tests:
    - RecencyScorer class creation
    - Decay formula: 10 * (1 - days_old / 30) capped at 0
    - Items from today score 10
    - Items 15 days old score 5
    - Items 30 days old score 0
    - Items older than 30 days score 0
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from teams.dawo.research.models import ResearchSource, ComplianceStatus
from teams.dawo.research.scoring.components.recency import (
    RecencyScorer,
    RecencyConfig,
    RECENCY_DECAY_DAYS,
    MAX_RECENCY_SCORE,
    MIN_RECENCY_SCORE,
)


@pytest.fixture
def default_recency_config() -> RecencyConfig:
    """Default recency configuration."""
    return RecencyConfig()


@pytest.fixture
def recency_scorer(default_recency_config: RecencyConfig) -> RecencyScorer:
    """RecencyScorer with default configuration."""
    return RecencyScorer(config=default_recency_config)


class TestRecencyConfig:
    """Tests for RecencyConfig dataclass."""

    def test_default_decay_days(self):
        """Default decay period should be 30 days."""
        config = RecencyConfig()
        assert config.decay_days == 30

    def test_custom_decay_days(self):
        """Config should accept custom decay period."""
        config = RecencyConfig(decay_days=14)
        assert config.decay_days == 14


class TestRecencyScorer:
    """Tests for RecencyScorer class."""

    def test_create_with_config(self, default_recency_config: RecencyConfig):
        """RecencyScorer should accept config via constructor injection."""
        scorer = RecencyScorer(config=default_recency_config)
        assert scorer._config is not None

    def test_score_item_from_today(self, recency_scorer: RecencyScorer):
        """Item from today should score 10."""
        item = _create_test_item(days_old=0)

        result = recency_scorer.score(item)

        assert result.raw_score == MAX_RECENCY_SCORE  # 10.0

    def test_score_item_15_days_old(self, recency_scorer: RecencyScorer):
        """Item 15 days old should score 5 (halfway through decay)."""
        item = _create_test_item(days_old=15)

        result = recency_scorer.score(item)

        assert result.raw_score == 5.0

    def test_score_item_30_days_old(self, recency_scorer: RecencyScorer):
        """Item 30 days old should score 0 (end of decay window)."""
        item = _create_test_item(days_old=30)

        result = recency_scorer.score(item)

        assert result.raw_score == MIN_RECENCY_SCORE  # 0.0

    def test_score_item_45_days_old(self, recency_scorer: RecencyScorer):
        """Item older than 30 days should score 0 (capped at minimum)."""
        item = _create_test_item(days_old=45)

        result = recency_scorer.score(item)

        assert result.raw_score == MIN_RECENCY_SCORE  # 0.0

    def test_score_item_1_day_old(self, recency_scorer: RecencyScorer):
        """Item 1 day old should score ~9.67."""
        item = _create_test_item(days_old=1)

        result = recency_scorer.score(item)

        # 10 * (1 - 1/30) = 10 * (29/30) ≈ 9.67
        expected = 10.0 * (1 - 1/30)
        assert abs(result.raw_score - expected) < 0.01

    def test_score_item_7_days_old(self, recency_scorer: RecencyScorer):
        """Item 7 days old should score ~7.67."""
        item = _create_test_item(days_old=7)

        result = recency_scorer.score(item)

        # 10 * (1 - 7/30) = 10 * (23/30) ≈ 7.67
        expected = 10.0 * (1 - 7/30)
        assert abs(result.raw_score - expected) < 0.01

    def test_score_includes_component_name(self, recency_scorer: RecencyScorer):
        """Result should include component name."""
        item = _create_test_item(days_old=0)

        result = recency_scorer.score(item)

        assert result.component_name == "recency"

    def test_score_includes_notes_with_age(self, recency_scorer: RecencyScorer):
        """Result notes should mention item age."""
        item = _create_test_item(days_old=10)

        result = recency_scorer.score(item)

        assert "10" in result.notes or "day" in result.notes.lower()

    def test_score_with_custom_decay_period(self):
        """Scorer with custom decay period should use that period."""
        config = RecencyConfig(decay_days=14)
        scorer = RecencyScorer(config=config)
        item = _create_test_item(days_old=7)  # Halfway through 14-day window

        result = scorer.score(item)

        assert result.raw_score == 5.0  # 10 * (1 - 7/14) = 5.0

    def test_score_never_negative(self, recency_scorer: RecencyScorer):
        """Score should never be negative."""
        item = _create_test_item(days_old=100)

        result = recency_scorer.score(item)

        assert result.raw_score >= 0.0

    def test_score_never_exceeds_max(self, recency_scorer: RecencyScorer):
        """Score should never exceed 10."""
        # Create item with future date (shouldn't happen but handle gracefully)
        item = _create_test_item(days_old=-1)

        result = recency_scorer.score(item)

        assert result.raw_score <= MAX_RECENCY_SCORE


class TestRecencyConstants:
    """Tests for recency scoring constants."""

    def test_recency_decay_days(self):
        """Decay period should be 30 days."""
        assert RECENCY_DECAY_DAYS == 30

    def test_max_recency_score(self):
        """Max recency score should be 10."""
        assert MAX_RECENCY_SCORE == 10.0

    def test_min_recency_score(self):
        """Min recency score should be 0."""
        assert MIN_RECENCY_SCORE == 0.0


def _create_test_item(days_old: int) -> dict:
    """Create a test research item with specified age.

    Args:
        days_old: Number of days since item was created.

    Returns:
        Dictionary with item data for scoring.
    """
    created_at = datetime.now(timezone.utc) - timedelta(days=days_old)

    return {
        "id": uuid4(),
        "source": ResearchSource.REDDIT.value,
        "title": "Test article",
        "content": "Test content.",
        "url": "https://example.com/test",
        "tags": [],
        "source_metadata": {},
        "created_at": created_at,
        "score": 0.0,
        "compliance_status": ComplianceStatus.COMPLIANT.value,
    }
