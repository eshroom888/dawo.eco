"""Tests for InstagramMediaMetric model.

Epic 7, Story 7-1: Instagram Engagement Metrics Collection.
Task 1.5: Write tests for model (field validation, unique constraint behavior).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.analytics.models import InstagramMediaMetric, SnapshotLabel


class TestSnapshotLabel:
    """Tests for SnapshotLabel enum."""

    def test_baseline_value(self) -> None:
        assert SnapshotLabel.BASELINE == "baseline"

    def test_day_1_value(self) -> None:
        assert SnapshotLabel.DAY_1 == "24h"

    def test_day_2_value(self) -> None:
        assert SnapshotLabel.DAY_2 == "48h"

    def test_day_7_value(self) -> None:
        assert SnapshotLabel.DAY_7 == "7d"

    def test_all_labels_are_strings(self) -> None:
        for label in SnapshotLabel:
            assert isinstance(label.value, str)


class TestInstagramMediaMetricModel:
    """Tests for InstagramMediaMetric SQLAlchemy model."""

    def test_tablename(self) -> None:
        assert InstagramMediaMetric.__tablename__ == "instagram_media_metrics"

    def test_required_columns_exist(self) -> None:
        """Verify all required columns are defined on the model."""
        columns = {c.name for c in InstagramMediaMetric.__table__.columns}
        expected = {
            "id",
            "media_id",
            "collected_at",
            "snapshot_label",
            "impressions",
            "reach",
            "likes",
            "comments",
            "saved",
            "shares",
            "total_interactions",
            "plays",
            "avg_watch_time_ms",
            "raw_response",
            "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_primary_key_is_id(self) -> None:
        pk_cols = [c.name for c in InstagramMediaMetric.__table__.primary_key.columns]
        assert pk_cols == ["id"]

    def test_media_id_max_length(self) -> None:
        col = InstagramMediaMetric.__table__.c.media_id
        assert col.type.length == 100

    def test_snapshot_label_max_length(self) -> None:
        col = InstagramMediaMetric.__table__.c.snapshot_label
        assert col.type.length == 20

    def test_unique_constraint_on_media_id_snapshot_label(self) -> None:
        """Task 1.2: UNIQUE constraint on (media_id, snapshot_label)."""
        table = InstagramMediaMetric.__table__
        unique_constraints = [
            c for c in table.constraints
            if hasattr(c, "columns") and len(c.columns) == 2
        ]
        found = False
        for uc in unique_constraints:
            col_names = {c.name for c in uc.columns}
            if col_names == {"media_id", "snapshot_label"}:
                found = True
                break
        assert found, "UNIQUE(media_id, snapshot_label) constraint not found"

    def test_nullable_plays(self) -> None:
        col = InstagramMediaMetric.__table__.c.plays
        assert col.nullable is True

    def test_nullable_avg_watch_time_ms(self) -> None:
        col = InstagramMediaMetric.__table__.c.avg_watch_time_ms
        assert col.nullable is True

    def test_raw_response_nullable(self) -> None:
        col = InstagramMediaMetric.__table__.c.raw_response
        assert col.nullable is True

    def test_non_nullable_metrics(self) -> None:
        """Core metrics must be non-nullable."""
        non_nullable = [
            "media_id", "collected_at", "snapshot_label",
            "impressions", "reach", "likes", "comments",
            "saved", "shares", "total_interactions",
        ]
        for name in non_nullable:
            col = InstagramMediaMetric.__table__.c[name]
            assert col.nullable is False, f"{name} should be non-nullable"

    def test_indexes_exist(self) -> None:
        """Task 1.3: Required indexes."""
        table = InstagramMediaMetric.__table__
        index_names = {idx.name for idx in table.indexes}
        expected_indexes = {
            "idx_media_metrics_media_id",
            "idx_media_metrics_collected_at",
            "idx_media_metrics_snapshot_label",
        }
        assert expected_indexes.issubset(index_names), (
            f"Missing indexes: {expected_indexes - index_names}"
        )

    def test_id_has_server_default(self) -> None:
        col = InstagramMediaMetric.__table__.c.id
        assert col.server_default is not None

    def test_created_at_has_server_default(self) -> None:
        col = InstagramMediaMetric.__table__.c.created_at
        assert col.server_default is not None

    def test_model_can_be_instantiated(self) -> None:
        """Verify model can be created with required fields."""
        now = datetime.now(UTC)
        metric = InstagramMediaMetric(
            media_id="17890012345678901",
            collected_at=now,
            snapshot_label="baseline",
            impressions=100,
            reach=80,
            likes=50,
            comments=10,
            saved=5,
            shares=3,
            total_interactions=68,
        )
        assert metric.media_id == "17890012345678901"
        assert metric.snapshot_label == "baseline"
        assert metric.impressions == 100
        assert metric.plays is None
        assert metric.avg_watch_time_ms is None

    def test_model_with_reel_metrics(self) -> None:
        """Verify reel-specific fields can be set."""
        now = datetime.now(UTC)
        metric = InstagramMediaMetric(
            media_id="17890012345678901",
            collected_at=now,
            snapshot_label="24h",
            impressions=200,
            reach=150,
            likes=80,
            comments=15,
            saved=10,
            shares=5,
            total_interactions=110,
            plays=500,
            avg_watch_time_ms=4500,
        )
        assert metric.plays == 500
        assert metric.avg_watch_time_ms == 4500
