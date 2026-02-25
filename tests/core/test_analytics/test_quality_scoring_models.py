"""Tests for PostPublishScoreRecord model.

Epic 7, Story 7-4: Post-Publish Quality Scoring.
Task 1.3: Write model unit tests (field types, defaults, constraints, unique post_id).
"""

from datetime import UTC, datetime
from decimal import Decimal

from core.analytics.quality_scoring_models import PostPublishScoreRecord


class TestPostPublishScoreRecordModel:
    """Tests for PostPublishScoreRecord SQLAlchemy model."""

    def test_tablename(self) -> None:
        assert PostPublishScoreRecord.__tablename__ == "post_publish_scores"

    def test_required_columns_exist(self) -> None:
        """Verify all required columns are defined on the model."""
        columns = {c.name for c in PostPublishScoreRecord.__table__.columns}
        expected = {
            "id",
            "post_id",
            "media_id",
            "pre_publish_score",
            "post_publish_score",
            "variance",
            "component_scores",
            "metrics_snapshot",
            "flagged_for_review",
            "snapshot_label",
            "calculated_at",
            "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_primary_key_is_id(self) -> None:
        pk_cols = [
            c.name for c in PostPublishScoreRecord.__table__.primary_key.columns
        ]
        assert pk_cols == ["id"]

    def test_id_has_server_default(self) -> None:
        col = PostPublishScoreRecord.__table__.c.id
        assert col.server_default is not None

    def test_created_at_has_server_default(self) -> None:
        col = PostPublishScoreRecord.__table__.c.created_at
        assert col.server_default is not None

    def test_post_id_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.post_id
        assert col.nullable is False

    def test_post_id_unique_constraint(self) -> None:
        """post_id must have a unique index for idempotent upserts."""
        table = PostPublishScoreRecord.__table__
        unique_indexes = [
            idx for idx in table.indexes if idx.unique
        ]
        found = False
        for idx in unique_indexes:
            col_names = {c.name for c in idx.columns}
            if col_names == {"post_id"}:
                found = True
                break
        assert found, "Unique index on post_id not found"

    def test_media_id_nullable(self) -> None:
        """media_id nullable for posts not yet published to Instagram."""
        col = PostPublishScoreRecord.__table__.c.media_id
        assert col.nullable is True

    def test_pre_publish_score_nullable(self) -> None:
        """pre_publish_score nullable when no pre-publish score available."""
        col = PostPublishScoreRecord.__table__.c.pre_publish_score
        assert col.nullable is True

    def test_post_publish_score_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.post_publish_score
        assert col.nullable is False

    def test_variance_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.variance
        assert col.nullable is False

    def test_component_scores_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.component_scores
        assert col.nullable is False

    def test_metrics_snapshot_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.metrics_snapshot
        assert col.nullable is False

    def test_flagged_for_review_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.flagged_for_review
        assert col.nullable is False

    def test_flagged_for_review_default_false(self) -> None:
        col = PostPublishScoreRecord.__table__.c.flagged_for_review
        assert col.default is not None
        assert col.default.arg is False

    def test_snapshot_label_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.snapshot_label
        assert col.nullable is False

    def test_snapshot_label_default(self) -> None:
        col = PostPublishScoreRecord.__table__.c.snapshot_label
        assert col.default is not None
        assert col.default.arg == "7d"

    def test_calculated_at_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.calculated_at
        assert col.nullable is False

    def test_created_at_not_nullable(self) -> None:
        col = PostPublishScoreRecord.__table__.c.created_at
        assert col.nullable is False

    def test_indexes_exist(self) -> None:
        """Required indexes for query performance."""
        table = PostPublishScoreRecord.__table__
        index_names = {idx.name for idx in table.indexes}
        expected_indexes = {
            "idx_post_publish_scores_post_id",
            "idx_post_publish_scores_calculated_at",
            "idx_post_publish_scores_flagged",
        }
        assert expected_indexes.issubset(index_names), (
            f"Missing indexes: {expected_indexes - index_names}"
        )

    def test_model_can_be_instantiated(self) -> None:
        """Verify model can be created with required fields."""
        now = datetime.now(UTC)
        record = PostPublishScoreRecord(
            post_id="post-123",
            post_publish_score=Decimal("7.5"),
            variance=Decimal("1.5"),
            component_scores={
                "engagement_vs_avg": {"raw_score": 8.0, "weight": 0.30, "weighted_score": 2.4},
            },
            metrics_snapshot={"engagement_rate": 0.05},
            calculated_at=now,
        )
        assert record.post_id == "post-123"
        assert record.post_publish_score == Decimal("7.5")
        assert record.variance == Decimal("1.5")
        # SQLAlchemy column defaults apply at INSERT, not Python instantiation
        # Column default=False verified separately in test_flagged_for_review_default_false
        # SQLAlchemy column defaults apply at INSERT, not Python instantiation
        # Column defaults verified separately in dedicated tests
        assert record.flagged_for_review in (None, False)
        assert record.snapshot_label in (None, "7d")
        assert record.media_id is None
        assert record.pre_publish_score is None

    def test_model_with_all_fields(self) -> None:
        """Verify model works with all optional fields set."""
        now = datetime.now(UTC)
        record = PostPublishScoreRecord(
            post_id="post-456",
            media_id="17890012345678901",
            pre_publish_score=Decimal("8.0"),
            post_publish_score=Decimal("5.0"),
            variance=Decimal("-3.0"),
            component_scores={
                "engagement_vs_avg": {"raw_score": 4.0, "weight": 0.30, "weighted_score": 1.2},
            },
            metrics_snapshot={"engagement_rate": 0.02},
            flagged_for_review=True,
            snapshot_label="7d",
            calculated_at=now,
        )
        assert record.media_id == "17890012345678901"
        assert record.pre_publish_score == Decimal("8.0")
        assert record.flagged_for_review is True
        assert record.variance == Decimal("-3.0")

    def test_repr(self) -> None:
        """Verify __repr__ includes key fields."""
        now = datetime.now(UTC)
        record = PostPublishScoreRecord(
            post_id="post-789",
            post_publish_score=Decimal("6.0"),
            variance=Decimal("0.0"),
            component_scores={},
            metrics_snapshot={},
            calculated_at=now,
        )
        repr_str = repr(record)
        assert "post-789" in repr_str
        assert "6.0" in repr_str

    def test_numeric_precision_post_publish_score(self) -> None:
        """post_publish_score uses Numeric(4,1) — one decimal place."""
        col = PostPublishScoreRecord.__table__.c.post_publish_score
        assert col.type.precision == 4
        assert col.type.scale == 1

    def test_numeric_precision_pre_publish_score(self) -> None:
        """pre_publish_score uses Numeric(4,1) — one decimal place."""
        col = PostPublishScoreRecord.__table__.c.pre_publish_score
        assert col.type.precision == 4
        assert col.type.scale == 1

    def test_numeric_precision_variance(self) -> None:
        """variance uses Numeric(5,1) — allows negative values + wider range."""
        col = PostPublishScoreRecord.__table__.c.variance
        assert col.type.precision == 5
        assert col.type.scale == 1
