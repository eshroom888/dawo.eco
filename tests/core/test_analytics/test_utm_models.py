"""Tests for UTM tracking SQLAlchemy models.

Story 7-2, Task 1.4: Tests for ShortLink and LinkClick models.
Tests field validation, relationships, unique constraints, and defaults.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import inspect

from core.analytics.utm_models import (
    LinkClick,
    ShortLink,
    MAX_CODE_LENGTH,
    MAX_CAMPAIGN_LENGTH,
    MAX_CONTENT_LENGTH,
    MAX_DEVICE_TYPE_LENGTH,
    MAX_IP_HASH_LENGTH,
    MAX_MEDIUM_LENGTH,
    MAX_POST_ID_LENGTH,
    MAX_SOURCE_LENGTH,
    MAX_SOURCE_TYPE_LENGTH,
)


class TestShortLinkModel:
    """Tests for ShortLink SQLAlchemy model."""

    def test_tablename(self) -> None:
        """ShortLink uses 'short_links' table name."""
        assert ShortLink.__tablename__ == "short_links"

    def test_has_required_columns(self) -> None:
        """ShortLink has all required columns from Task 1.1."""
        mapper = inspect(ShortLink)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id",
            "code",
            "destination_url",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "post_id",
            "source_type",
            "created_at",
            "expires_at",
        }
        assert expected.issubset(column_names)

    def test_id_is_uuid_primary_key(self) -> None:
        """ShortLink id is UUID primary key."""
        mapper = inspect(ShortLink)
        pk_columns = [c.key for c in mapper.columns if c.primary_key]
        assert pk_columns == ["id"]

    def test_code_column_properties(self) -> None:
        """Code column has proper length and is not nullable."""
        mapper = inspect(ShortLink)
        code_col = mapper.columns["code"]
        assert not code_col.nullable
        assert code_col.type.length == MAX_CODE_LENGTH

    def test_destination_url_not_nullable(self) -> None:
        """Destination URL cannot be null."""
        mapper = inspect(ShortLink)
        col = mapper.columns["destination_url"]
        assert not col.nullable

    def test_post_id_is_nullable(self) -> None:
        """Post ID is nullable (links may not be tied to a post)."""
        mapper = inspect(ShortLink)
        col = mapper.columns["post_id"]
        assert col.nullable

    def test_source_type_default(self) -> None:
        """Source type has 'instagram' as column default for INSERT."""
        mapper = inspect(ShortLink)
        col = mapper.columns["source_type"]
        assert col.default is not None
        assert col.default.arg == "instagram"

    def test_source_type_explicit(self) -> None:
        """Source type can be set explicitly."""
        link = ShortLink(
            code="abc123",
            destination_url="https://example.com",
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed",
            utm_content="post123",
            source_type="facebook",
        )
        assert link.source_type == "facebook"

    def test_expires_at_is_nullable(self) -> None:
        """Expires_at is nullable for links without expiration."""
        mapper = inspect(ShortLink)
        col = mapper.columns["expires_at"]
        assert col.nullable

    def test_has_unique_code_index(self) -> None:
        """ShortLink table has unique index on code."""
        indexes = ShortLink.__table__.indexes
        code_indexes = [idx for idx in indexes if "code" in [c.name for c in idx.columns]]
        assert any(idx.unique for idx in code_indexes), "No unique index on code column"

    def test_has_post_id_index(self) -> None:
        """ShortLink table has index on post_id."""
        indexes = ShortLink.__table__.indexes
        post_id_indexes = [
            idx for idx in indexes if "post_id" in [c.name for c in idx.columns]
        ]
        assert len(post_id_indexes) > 0, "No index on post_id column"

    def test_repr(self) -> None:
        """ShortLink has readable repr."""
        link = ShortLink(
            code="abc123",
            destination_url="https://example.com",
            utm_source="instagram",
            utm_medium="post",
            utm_campaign="feed",
            utm_content="post123",
        )
        r = repr(link)
        assert "abc123" in r
        assert "ShortLink" in r

    def test_max_length_constants(self) -> None:
        """Length constants are defined correctly."""
        assert MAX_CODE_LENGTH == 12
        assert MAX_SOURCE_LENGTH == 50
        assert MAX_MEDIUM_LENGTH == 50
        assert MAX_CAMPAIGN_LENGTH == 100
        assert MAX_CONTENT_LENGTH == 100
        assert MAX_POST_ID_LENGTH == 100
        assert MAX_SOURCE_TYPE_LENGTH == 20


class TestLinkClickModel:
    """Tests for LinkClick SQLAlchemy model."""

    def test_tablename(self) -> None:
        """LinkClick uses 'link_clicks' table name."""
        assert LinkClick.__tablename__ == "link_clicks"

    def test_has_required_columns(self) -> None:
        """LinkClick has all required columns from Task 1.1."""
        mapper = inspect(LinkClick)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id",
            "short_link_id",
            "clicked_at",
            "ip_hash",
            "user_agent",
            "device_type",
            "referer",
        }
        assert expected.issubset(column_names)

    def test_id_is_uuid_primary_key(self) -> None:
        """LinkClick id is UUID primary key."""
        mapper = inspect(LinkClick)
        pk_columns = [c.key for c in mapper.columns if c.primary_key]
        assert pk_columns == ["id"]

    def test_short_link_id_is_foreign_key(self) -> None:
        """short_link_id references short_links.id."""
        mapper = inspect(LinkClick)
        col = mapper.columns["short_link_id"]
        fk = list(col.foreign_keys)
        assert len(fk) == 1
        assert "short_links.id" in str(fk[0])

    def test_ip_hash_column_properties(self) -> None:
        """IP hash has correct length for SHA-256 (64 chars)."""
        mapper = inspect(LinkClick)
        col = mapper.columns["ip_hash"]
        assert not col.nullable
        assert col.type.length == MAX_IP_HASH_LENGTH

    def test_user_agent_is_nullable(self) -> None:
        """User agent is nullable."""
        mapper = inspect(LinkClick)
        col = mapper.columns["user_agent"]
        assert col.nullable

    def test_device_type_is_nullable(self) -> None:
        """Device type is nullable."""
        mapper = inspect(LinkClick)
        col = mapper.columns["device_type"]
        assert col.nullable

    def test_referer_is_nullable(self) -> None:
        """Referer is nullable."""
        mapper = inspect(LinkClick)
        col = mapper.columns["referer"]
        assert col.nullable

    def test_has_short_link_id_index(self) -> None:
        """LinkClick table has index on short_link_id."""
        indexes = LinkClick.__table__.indexes
        fk_indexes = [
            idx for idx in indexes if "short_link_id" in [c.name for c in idx.columns]
        ]
        assert len(fk_indexes) > 0, "No index on short_link_id column"

    def test_has_clicked_at_index(self) -> None:
        """LinkClick table has index on clicked_at."""
        indexes = LinkClick.__table__.indexes
        at_indexes = [
            idx for idx in indexes if "clicked_at" in [c.name for c in idx.columns]
        ]
        assert len(at_indexes) > 0, "No index on clicked_at column"

    def test_repr(self) -> None:
        """LinkClick has readable repr."""
        click = LinkClick(
            short_link_id=uuid4(),
            clicked_at=datetime.now(UTC),
            ip_hash="a" * 64,
        )
        r = repr(click)
        assert "LinkClick" in r

    def test_max_length_constants(self) -> None:
        """Length constants for LinkClick are correct."""
        assert MAX_IP_HASH_LENGTH == 64
        assert MAX_DEVICE_TYPE_LENGTH == 20


class TestModelExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """utm_models module exports all public names."""
        from core.analytics import utm_models

        assert hasattr(utm_models, "__all__")
        expected_exports = {"ShortLink", "LinkClick"}
        assert expected_exports.issubset(set(utm_models.__all__))
