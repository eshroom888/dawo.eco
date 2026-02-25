"""Tests for Mattilsynet SQLAlchemy models.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 1 / Task 13.37: Validate model definitions, enums, and constraints.
"""

import pytest
from uuid import UUID

from core.regulatory.models import (
    MattilsynetSnapshot,
    MattilsynetUpdate,
    MattilsynetPageHash,
    MattilsynetSourceType,
    MattilsynetCategory,
    ChangeSeverity,
    MAX_URL_LENGTH,
    MAX_HASH_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_PAGE_NAME_LENGTH,
    MAX_SUMMARY_LENGTH,
)


class TestMattilsynetSourceTypeEnum:
    """Test MattilsynetSourceType enum values."""

    def test_rss_news_value(self) -> None:
        assert MattilsynetSourceType.RSS_NEWS.value == "rss_news"

    def test_rss_warning_value(self) -> None:
        assert MattilsynetSourceType.RSS_WARNING.value == "rss_warning"

    def test_page_change_value(self) -> None:
        assert MattilsynetSourceType.PAGE_CHANGE.value == "page_change"

    def test_sitemap_new_value(self) -> None:
        assert MattilsynetSourceType.SITEMAP_NEW.value == "sitemap_new"

    def test_is_str_subclass(self) -> None:
        assert isinstance(MattilsynetSourceType.RSS_NEWS, str)


class TestMattilsynetCategoryEnum:
    """Test MattilsynetCategory enum values."""

    def test_enforcement_value(self) -> None:
        assert MattilsynetCategory.ENFORCEMENT.value == "enforcement"

    def test_regulation_value(self) -> None:
        assert MattilsynetCategory.REGULATION.value == "regulation"

    def test_guidance_value(self) -> None:
        assert MattilsynetCategory.GUIDANCE.value == "guidance"

    def test_news_value(self) -> None:
        assert MattilsynetCategory.NEWS.value == "news"

    def test_recall_value(self) -> None:
        assert MattilsynetCategory.RECALL.value == "recall"

    def test_import_ban_value(self) -> None:
        assert MattilsynetCategory.IMPORT_BAN.value == "import_ban"

    def test_is_str_subclass(self) -> None:
        assert isinstance(MattilsynetCategory.ENFORCEMENT, str)


class TestMattilsynetSnapshotModel:
    """Test MattilsynetSnapshot model definition."""

    def test_tablename(self) -> None:
        assert MattilsynetSnapshot.__tablename__ == "mattilsynet_snapshots"

    def test_has_id_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "id" in columns

    def test_has_snapshot_hash_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "snapshot_hash" in columns

    def test_has_total_updates_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "total_updates" in columns

    def test_has_relevant_updates_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "relevant_updates" in columns

    def test_has_feeds_checked_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "feeds_checked" in columns

    def test_has_pages_checked_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "pages_checked" in columns

    def test_has_scan_duration_seconds_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "scan_duration_seconds" in columns

    def test_has_created_at_column(self) -> None:
        columns = MattilsynetSnapshot.__table__.columns
        assert "created_at" in columns

    def test_id_is_primary_key(self) -> None:
        col = MattilsynetSnapshot.__table__.columns["id"]
        assert col.primary_key


class TestMattilsynetUpdateModel:
    """Test MattilsynetUpdate model definition."""

    def test_tablename(self) -> None:
        assert MattilsynetUpdate.__tablename__ == "mattilsynet_updates"

    def test_has_snapshot_id_fk(self) -> None:
        col = MattilsynetUpdate.__table__.columns["snapshot_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "mattilsynet_snapshots.id"

    def test_has_title_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "title" in columns

    def test_has_url_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "url" in columns

    def test_has_content_summary_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "content_summary" in columns

    def test_has_source_type_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "source_type" in columns

    def test_has_category_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "category" in columns

    def test_has_keywords_matched_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "keywords_matched" in columns

    def test_has_relevance_tier_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "relevance_tier" in columns

    def test_has_severity_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "severity" in columns

    def test_has_is_relevant_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "is_relevant" in columns

    def test_has_raw_content_hash_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "raw_content_hash" in columns

    def test_has_published_at_column(self) -> None:
        columns = MattilsynetUpdate.__table__.columns
        assert "published_at" in columns

    def test_snapshot_id_cascade_delete(self) -> None:
        col = MattilsynetUpdate.__table__.columns["snapshot_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE"

    def test_indexes_exist(self) -> None:
        index_names = {idx.name for idx in MattilsynetUpdate.__table__.indexes}
        assert "idx_mattilsynet_updates_snapshot" in index_names
        assert "idx_mattilsynet_updates_relevant" in index_names
        assert "idx_mattilsynet_updates_url" in index_names


class TestMattilsynetPageHashModel:
    """Test MattilsynetPageHash model definition."""

    def test_tablename(self) -> None:
        assert MattilsynetPageHash.__tablename__ == "mattilsynet_page_hashes"

    def test_has_url_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "url" in columns

    def test_has_page_name_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "page_name" in columns

    def test_has_content_hash_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "content_hash" in columns

    def test_has_last_checked_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "last_checked" in columns

    def test_has_last_changed_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "last_changed" in columns

    def test_has_created_at_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "created_at" in columns

    def test_has_updated_at_column(self) -> None:
        columns = MattilsynetPageHash.__table__.columns
        assert "updated_at" in columns

    def test_url_index_exists(self) -> None:
        index_names = {idx.name for idx in MattilsynetPageHash.__table__.indexes}
        assert "idx_mattilsynet_page_hashes_url" in index_names


class TestModelConstants:
    """Test model constants for Mattilsynet-specific fields."""

    def test_max_title_length(self) -> None:
        assert MAX_TITLE_LENGTH == 500

    def test_max_page_name_length(self) -> None:
        assert MAX_PAGE_NAME_LENGTH == 200

    def test_max_summary_length_is_text(self) -> None:
        # content_summary uses Text, so no length constant needed
        # But MAX_SUMMARY_LENGTH constant should exist for reference
        assert MAX_SUMMARY_LENGTH == 2000


__all__ = [
    "TestMattilsynetSourceTypeEnum",
    "TestMattilsynetCategoryEnum",
    "TestMattilsynetSnapshotModel",
    "TestMattilsynetUpdateModel",
    "TestMattilsynetPageHashModel",
    "TestModelConstants",
]
