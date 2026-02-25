"""Tests for FeedbackReport and WeightAdjustmentRecord models.

Epic 7, Story 7-5: Performance Feedback Loop.
Task 1.4: Write model unit tests (target: 20+ tests covering
constraints, defaults, JSONB storage).
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from core.analytics.feedback_loop_models import (
    FeedbackReport,
    WeightAdjustmentRecord,
)


class TestFeedbackReportModel:
    """Tests for FeedbackReport SQLAlchemy model."""

    def test_tablename(self) -> None:
        assert FeedbackReport.__tablename__ == "feedback_reports"

    def test_required_columns_exist(self) -> None:
        columns = {c.name for c in FeedbackReport.__table__.columns}
        expected = {
            "id",
            "report_date",
            "min_posts_threshold",
            "total_posts_analyzed",
            "content_type_rankings",
            "time_slot_analysis",
            "hashtag_rankings",
            "weight_adjustment_proposal",
            "source_performance",
            "recommendations",
            "status",
            "missing_sections",
            "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_primary_key_is_id(self) -> None:
        pk_cols = [
            c.name for c in FeedbackReport.__table__.primary_key.columns
        ]
        assert pk_cols == ["id"]

    def test_id_has_server_default(self) -> None:
        col = FeedbackReport.__table__.c.id
        assert col.server_default is not None

    def test_created_at_has_server_default(self) -> None:
        col = FeedbackReport.__table__.c.created_at
        assert col.server_default is not None

    def test_report_date_not_nullable(self) -> None:
        col = FeedbackReport.__table__.c.report_date
        assert col.nullable is False

    def test_report_date_unique_index(self) -> None:
        """report_date must have a unique index for one-report-per-week."""
        table = FeedbackReport.__table__
        unique_indexes = [idx for idx in table.indexes if idx.unique]
        found = any(
            {c.name for c in idx.columns} == {"report_date"}
            for idx in unique_indexes
        )
        assert found, "Unique index on report_date not found"

    def test_min_posts_threshold_not_nullable(self) -> None:
        col = FeedbackReport.__table__.c.min_posts_threshold
        assert col.nullable is False

    def test_total_posts_analyzed_not_nullable(self) -> None:
        col = FeedbackReport.__table__.c.total_posts_analyzed
        assert col.nullable is False

    def test_status_not_nullable(self) -> None:
        col = FeedbackReport.__table__.c.status
        assert col.nullable is False

    def test_content_type_rankings_nullable(self) -> None:
        """JSONB fields nullable to support partial reports."""
        col = FeedbackReport.__table__.c.content_type_rankings
        assert col.nullable is True

    def test_time_slot_analysis_nullable(self) -> None:
        col = FeedbackReport.__table__.c.time_slot_analysis
        assert col.nullable is True

    def test_hashtag_rankings_nullable(self) -> None:
        col = FeedbackReport.__table__.c.hashtag_rankings
        assert col.nullable is True

    def test_weight_adjustment_proposal_nullable(self) -> None:
        col = FeedbackReport.__table__.c.weight_adjustment_proposal
        assert col.nullable is True

    def test_source_performance_nullable(self) -> None:
        col = FeedbackReport.__table__.c.source_performance
        assert col.nullable is True

    def test_recommendations_nullable(self) -> None:
        col = FeedbackReport.__table__.c.recommendations
        assert col.nullable is True

    def test_missing_sections_nullable(self) -> None:
        col = FeedbackReport.__table__.c.missing_sections
        assert col.nullable is True

    def test_model_can_be_instantiated_complete(self) -> None:
        """FeedbackReport with all sections present (status=complete)."""
        report = FeedbackReport(
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=150,
            content_type_rankings=[
                {"type": "reel", "avg_score": 8.2, "count": 50},
            ],
            time_slot_analysis={"best_slots": [{"day": "Tuesday", "hour": 18}]},
            hashtag_rankings=[{"hashtag": "#wellness", "avg_score": 7.5}],
            weight_adjustment_proposal={"engagement_vs_avg": 0.35},
            source_performance={"reddit": {"avg_score": 7.0, "count": 20}},
            recommendations=["Increase reel content"],
            status="complete",
            missing_sections=[],
        )
        assert report.report_date == date(2026, 2, 23)
        assert report.total_posts_analyzed == 150
        assert report.status == "complete"

    def test_model_can_be_instantiated_partial(self) -> None:
        """FeedbackReport with missing sections (status=partial)."""
        report = FeedbackReport(
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=80,
            content_type_rankings=None,
            time_slot_analysis=None,
            hashtag_rankings=None,
            weight_adjustment_proposal=None,
            source_performance=None,
            recommendations=None,
            status="partial",
            missing_sections=["content_types", "time_slots", "hashtags"],
        )
        assert report.status == "partial"
        assert report.content_type_rankings is None

    def test_repr(self) -> None:
        report = FeedbackReport(
            report_date=date(2026, 2, 23),
            min_posts_threshold=100,
            total_posts_analyzed=150,
            status="complete",
        )
        repr_str = repr(report)
        assert "2026-02-23" in repr_str
        assert "complete" in repr_str

    def test_indexes_exist(self) -> None:
        table = FeedbackReport.__table__
        index_names = {idx.name for idx in table.indexes}
        expected_indexes = {
            "idx_feedback_reports_report_date",
            "idx_feedback_reports_created_at",
        }
        assert expected_indexes.issubset(index_names), (
            f"Missing indexes: {expected_indexes - index_names}"
        )


class TestWeightAdjustmentRecordModel:
    """Tests for WeightAdjustmentRecord SQLAlchemy model."""

    def test_tablename(self) -> None:
        assert WeightAdjustmentRecord.__tablename__ == "weight_adjustment_records"

    def test_required_columns_exist(self) -> None:
        columns = {c.name for c in WeightAdjustmentRecord.__table__.columns}
        expected = {
            "id",
            "adjustment_type",
            "previous_weights",
            "new_weights",
            "correlation_data",
            "applied",
            "applied_at",
            "feedback_report_id",
            "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_primary_key_is_id(self) -> None:
        pk_cols = [
            c.name for c in WeightAdjustmentRecord.__table__.primary_key.columns
        ]
        assert pk_cols == ["id"]

    def test_id_has_server_default(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.id
        assert col.server_default is not None

    def test_created_at_has_server_default(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.created_at
        assert col.server_default is not None

    def test_adjustment_type_not_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.adjustment_type
        assert col.nullable is False

    def test_previous_weights_not_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.previous_weights
        assert col.nullable is False

    def test_new_weights_not_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.new_weights
        assert col.nullable is False

    def test_correlation_data_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.correlation_data
        assert col.nullable is True

    def test_applied_not_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.applied
        assert col.nullable is False

    def test_applied_default_false(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.applied
        assert col.default is not None
        assert col.default.arg is False

    def test_applied_at_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.applied_at
        assert col.nullable is True

    def test_feedback_report_id_not_nullable(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.feedback_report_id
        assert col.nullable is False

    def test_feedback_report_id_is_foreign_key(self) -> None:
        col = WeightAdjustmentRecord.__table__.c.feedback_report_id
        fk_refs = [str(fk.target_fullname) for fk in col.foreign_keys]
        assert "feedback_reports.id" in fk_refs

    def test_model_can_be_instantiated(self) -> None:
        report_id = uuid4()
        record = WeightAdjustmentRecord(
            adjustment_type="quality_scoring",
            previous_weights={"engagement_vs_avg": 0.30, "reach_vs_avg": 0.20},
            new_weights={"engagement_vs_avg": 0.35, "reach_vs_avg": 0.18},
            correlation_data={"engagement_vs_avg": 0.72},
            feedback_report_id=report_id,
        )
        assert record.adjustment_type == "quality_scoring"
        assert record.feedback_report_id == report_id
        assert record.applied in (None, False)
        assert record.applied_at is None

    def test_model_with_applied_state(self) -> None:
        now = datetime.now(UTC)
        report_id = uuid4()
        record = WeightAdjustmentRecord(
            adjustment_type="source_scoring",
            previous_weights={"reddit": 0.5},
            new_weights={"reddit": 0.6},
            feedback_report_id=report_id,
            applied=True,
            applied_at=now,
        )
        assert record.applied is True
        assert record.applied_at == now

    def test_repr(self) -> None:
        report_id = uuid4()
        record = WeightAdjustmentRecord(
            adjustment_type="quality_scoring",
            previous_weights={},
            new_weights={},
            feedback_report_id=report_id,
        )
        repr_str = repr(record)
        assert "quality_scoring" in repr_str

    def test_indexes_exist(self) -> None:
        table = WeightAdjustmentRecord.__table__
        index_names = {idx.name for idx in table.indexes}
        expected_indexes = {
            "idx_weight_adj_feedback_report_id",
            "idx_weight_adj_adjustment_type",
        }
        assert expected_indexes.issubset(index_names), (
            f"Missing indexes: {expected_indexes - index_names}"
        )
