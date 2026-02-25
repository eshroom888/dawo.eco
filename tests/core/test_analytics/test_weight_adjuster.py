"""Tests for WeightAdjuster.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 4.3: Write adjuster tests (target: 15+ tests).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.analytics.weight_adjuster import (
    WeightAdjuster,
    WeightAdjustmentProposal,
)
from core.analytics.quality_scoring_analyzer import CorrelationReport
from core.analytics.feedback_loop_models import WeightAdjustmentRecord
from core.config import QualityScoringConfig


@pytest.fixture
def mock_variance_analyzer() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_feedback_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def config() -> QualityScoringConfig:
    return QualityScoringConfig(
        weights={
            "engagement_vs_avg": 0.30,
            "reach_vs_avg": 0.20,
            "click_through_rate": 0.20,
            "conversions": 0.15,
            "comment_sentiment": 0.15,
        }
    )


@pytest.fixture
def adjuster(
    mock_variance_analyzer: AsyncMock,
    mock_feedback_repo: AsyncMock,
    config: QualityScoringConfig,
) -> WeightAdjuster:
    return WeightAdjuster(mock_variance_analyzer, mock_feedback_repo, config)


class TestProposeWeightAdjustment:
    """Tests for propose_weight_adjustment method."""

    async def test_returns_proposal_when_significant_change(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        """Proposal generated when delta > threshold (5%)."""
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={
                "engagement_vs_avg": 0.8,
                "reach_vs_avg": 0.3,
                "click_through_rate": 0.5,
                "conversions": 0.2,
                "comment_sentiment": 0.1,
            },
            recommended_weights={
                "engagement_vs_avg": 0.40,
                "reach_vs_avg": 0.15,
                "click_through_rate": 0.25,
                "conversions": 0.10,
                "comment_sentiment": 0.10,
            },
            generated_at=datetime.now(UTC),
        )

        result = await adjuster.propose_weight_adjustment()

        assert result is not None
        assert isinstance(result, WeightAdjustmentProposal)
        assert result.current_weights == adjuster._config.weights
        assert sum(result.proposed_weights.values()) == pytest.approx(1.0, abs=0.01)

    async def test_returns_none_when_no_correlation_data(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        mock_variance_analyzer.run_correlation_analysis.return_value = None

        result = await adjuster.propose_weight_adjustment()
        assert result is None

    async def test_returns_none_when_no_significant_change(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        """No proposal when all weight deltas < threshold."""
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={
                "engagement_vs_avg": 0.6,
                "reach_vs_avg": 0.4,
                "click_through_rate": 0.4,
                "conversions": 0.3,
                "comment_sentiment": 0.3,
            },
            # Recommended weights very close to current
            recommended_weights={
                "engagement_vs_avg": 0.31,
                "reach_vs_avg": 0.20,
                "click_through_rate": 0.20,
                "conversions": 0.15,
                "comment_sentiment": 0.14,
            },
            generated_at=datetime.now(UTC),
        )

        result = await adjuster.propose_weight_adjustment()
        assert result is None

    async def test_proposed_weights_normalize_to_one(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={"engagement_vs_avg": 0.9, "reach_vs_avg": 0.1},
            recommended_weights={"engagement_vs_avg": 0.80, "reach_vs_avg": 0.20},
            generated_at=datetime.now(UTC),
        )

        result = await adjuster.propose_weight_adjustment()
        if result is not None:
            assert sum(result.proposed_weights.values()) == pytest.approx(1.0, abs=0.01)

    async def test_proposal_includes_change_rationale(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={
                "engagement_vs_avg": 0.8,
                "reach_vs_avg": 0.1,
                "click_through_rate": 0.5,
                "conversions": 0.2,
                "comment_sentiment": 0.1,
            },
            recommended_weights={
                "engagement_vs_avg": 0.45,
                "reach_vs_avg": 0.05,
                "click_through_rate": 0.25,
                "conversions": 0.15,
                "comment_sentiment": 0.10,
            },
            generated_at=datetime.now(UTC),
        )

        result = await adjuster.propose_weight_adjustment()
        assert result is not None
        assert isinstance(result.change_rationale, list)
        assert len(result.change_rationale) > 0

    async def test_proposal_includes_correlations(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        correlations = {"engagement_vs_avg": 0.8, "reach_vs_avg": 0.3}
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations=correlations,
            recommended_weights={"engagement_vs_avg": 0.70, "reach_vs_avg": 0.30},
            generated_at=datetime.now(UTC),
        )

        result = await adjuster.propose_weight_adjustment()
        if result is not None:
            assert result.correlations == correlations


class TestProposalRationale:
    """Tests for proposal rationale and edge cases."""

    async def test_rationale_includes_direction_and_correlation(
        self, adjuster: WeightAdjuster, mock_variance_analyzer: AsyncMock,
    ) -> None:
        """Rationale text includes increase/decrease and correlation value."""
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={
                "engagement_vs_avg": 0.8,
                "reach_vs_avg": 0.1,
                "click_through_rate": 0.5,
                "conversions": 0.2,
                "comment_sentiment": 0.1,
            },
            recommended_weights={
                "engagement_vs_avg": 0.50,
                "reach_vs_avg": 0.05,
                "click_through_rate": 0.25,
                "conversions": 0.10,
                "comment_sentiment": 0.10,
            },
            generated_at=datetime.now(UTC),
        )

        result = await adjuster.propose_weight_adjustment()
        assert result is not None
        # Check rationale mentions "increase" or "decrease"
        for line in result.change_rationale:
            assert "increase" in line or "decrease" in line
            assert "correlation" in line

    async def test_current_weights_preserved_for_missing_recommended_keys(
        self, mock_variance_analyzer: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        """If recommended omits a key, current weight is retained."""
        config = QualityScoringConfig(
            weights={"a": 0.50, "b": 0.30, "c": 0.20}
        )
        adj = WeightAdjuster(mock_variance_analyzer, mock_feedback_repo, config)

        # Recommended only has 'a' — 'b' and 'c' should use current
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={"a": 0.9},
            recommended_weights={"a": 0.90},
            generated_at=datetime.now(UTC),
        )

        result = await adj.propose_weight_adjustment()
        if result is not None:
            assert "b" in result.proposed_weights
            assert "c" in result.proposed_weights
            assert sum(result.proposed_weights.values()) == pytest.approx(1.0, abs=0.01)

    async def test_below_threshold_boundary_no_proposal(
        self, mock_variance_analyzer: AsyncMock,
        mock_feedback_repo: AsyncMock,
    ) -> None:
        """Delta below 5% threshold should NOT generate proposal."""
        config = QualityScoringConfig(weights={"a": 0.50, "b": 0.50})
        adj = WeightAdjuster(mock_variance_analyzer, mock_feedback_repo, config)

        # Deltas: abs(0.50 - 0.52) = 0.02 and abs(0.50 - 0.49) = 0.01
        # Both < 0.05, so no proposal
        mock_variance_analyzer.run_correlation_analysis.return_value = CorrelationReport(
            total_posts=100,
            correlations={"a": 0.6, "b": 0.5},
            recommended_weights={"a": 0.52, "b": 0.49},
            generated_at=datetime.now(UTC),
        )

        result = await adj.propose_weight_adjustment()
        assert result is None


class TestApplyAdjustment:
    """Tests for apply_adjustment method."""

    async def test_marks_record_as_applied(
        self, adjuster: WeightAdjuster, mock_feedback_repo: AsyncMock,
    ) -> None:
        record_id = uuid4()
        mock_feedback_repo.mark_adjustment_applied.return_value = None

        await adjuster.apply_adjustment(record_id)

        mock_feedback_repo.mark_adjustment_applied.assert_awaited_once_with(record_id)

    async def test_propagates_repo_error(
        self, adjuster: WeightAdjuster, mock_feedback_repo: AsyncMock,
    ) -> None:
        """ValueError from repo propagates to caller."""
        mock_feedback_repo.mark_adjustment_applied.side_effect = ValueError("not found")

        with pytest.raises(ValueError, match="not found"):
            await adjuster.apply_adjustment(uuid4())

    async def test_accepts_uuid(
        self, adjuster: WeightAdjuster, mock_feedback_repo: AsyncMock,
    ) -> None:
        """Accepts UUID type for record_id."""
        rid = uuid4()
        await adjuster.apply_adjustment(rid)
        args = mock_feedback_repo.mark_adjustment_applied.call_args[0]
        assert args[0] == rid


class TestNormalizeWeights:
    """Tests for _normalize_weights static helper."""

    def test_sums_to_one(self) -> None:
        result = WeightAdjuster._normalize_weights(
            {"a": 0.6, "b": 0.4}, {"a": 0.5, "b": 0.5}
        )
        assert sum(result.values()) == pytest.approx(1.0, abs=0.01)

    def test_retains_current_for_missing_keys(self) -> None:
        result = WeightAdjuster._normalize_weights(
            {"a": 0.8}, {"a": 0.5, "b": 0.3, "c": 0.2}
        )
        assert "b" in result
        assert "c" in result

    def test_zero_total_returns_current(self) -> None:
        result = WeightAdjuster._normalize_weights(
            {"a": 0.0, "b": 0.0}, {"a": 0.5, "b": 0.5}
        )
        assert result == {"a": 0.5, "b": 0.5}


class TestWeightAdjustmentProposalDTO:
    """Tests for WeightAdjustmentProposal frozen dataclass."""

    def test_frozen(self) -> None:
        proposal = WeightAdjustmentProposal(
            current_weights={"a": 0.5},
            proposed_weights={"a": 0.6},
            correlations={"a": 0.8},
            change_rationale=["Increase a weight"],
        )
        with pytest.raises(AttributeError):
            proposal.current_weights = {}  # type: ignore[misc]

    def test_fields(self) -> None:
        proposal = WeightAdjustmentProposal(
            current_weights={"a": 0.5, "b": 0.5},
            proposed_weights={"a": 0.6, "b": 0.4},
            correlations={"a": 0.8, "b": 0.3},
            change_rationale=["Increase a", "Decrease b"],
        )
        assert proposal.current_weights == {"a": 0.5, "b": 0.5}
        assert proposal.proposed_weights == {"a": 0.6, "b": 0.4}
        assert len(proposal.change_rationale) == 2

    def test_empty_rationale_allowed(self) -> None:
        proposal = WeightAdjustmentProposal(
            current_weights={"a": 1.0},
            proposed_weights={"a": 1.0},
            correlations={},
            change_rationale=[],
        )
        assert proposal.change_rationale == []
