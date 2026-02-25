"""SQLAlchemy models for UTM click-through tracking.

Epic 7, Story 7-2: UTM Click-Through Tracking.
Task 1.3: SQLAlchemy async models ShortLink and LinkClick.

ShortLink stores custom short redirect links with UTM parameters.
LinkClick records each click event with hashed IP (GDPR compliant).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base

# Column length constants
MAX_CODE_LENGTH = 12
MAX_SOURCE_LENGTH = 50
MAX_MEDIUM_LENGTH = 50
MAX_CAMPAIGN_LENGTH = 100
MAX_CONTENT_LENGTH = 100
MAX_POST_ID_LENGTH = 100
MAX_SOURCE_TYPE_LENGTH = 20
MAX_IP_HASH_LENGTH = 64  # SHA-256 hex digest
MAX_DEVICE_TYPE_LENGTH = 20


class ShortLink(Base):
    """Short redirect link with UTM tracking parameters.

    Story 7-2, Task 1.3: Stores short link codes and UTM metadata.
    Each short link maps a code to a destination URL with UTM params.
    The UNIQUE index on code ensures no duplicate short codes.

    Post ID is nullable since links may exist independently of posts.
    """

    __tablename__ = "short_links"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Short code for redirect URL (/l/{code})
    code: Mapped[str] = mapped_column(
        String(MAX_CODE_LENGTH),
        nullable=False,
    )

    # Destination URL (full URL with UTM params)
    destination_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # UTM parameters stored individually for querying
    utm_source: Mapped[str] = mapped_column(
        String(MAX_SOURCE_LENGTH),
        nullable=False,
    )
    utm_medium: Mapped[str] = mapped_column(
        String(MAX_MEDIUM_LENGTH),
        nullable=False,
    )
    utm_campaign: Mapped[str] = mapped_column(
        String(MAX_CAMPAIGN_LENGTH),
        nullable=False,
    )
    utm_content: Mapped[str] = mapped_column(
        String(MAX_CONTENT_LENGTH),
        nullable=False,
    )

    # Post association (nullable -- link may not be tied to a specific post)
    post_id: Mapped[Optional[str]] = mapped_column(
        String(MAX_POST_ID_LENGTH),
        nullable=True,
    )

    # Source platform
    source_type: Mapped[str] = mapped_column(
        String(MAX_SOURCE_TYPE_LENGTH),
        nullable=False,
        default="instagram",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship to clicks
    clicks: Mapped[list["LinkClick"]] = relationship(
        "LinkClick",
        back_populates="short_link",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_short_links_code", "code", unique=True),
        Index("idx_short_links_post_id", "post_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ShortLink(code={self.code!r}, "
            f"post_id={self.post_id!r})>"
        )


class LinkClick(Base):
    """Individual click event on a short link.

    Story 7-2, Task 1.3: Records click-through events.
    IP addresses are stored as SHA-256 hashes only (GDPR).
    User-agent is stored for device categorization, not tracking.
    """

    __tablename__ = "link_clicks"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key to short_links
    short_link_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("short_links.id"),
        nullable=False,
    )

    # Click timestamp
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # GDPR: SHA-256 hash of IP address -- NEVER store raw IP
    ip_hash: Mapped[str] = mapped_column(
        String(MAX_IP_HASH_LENGTH),
        nullable=False,
    )

    # Optional metadata
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    device_type: Mapped[Optional[str]] = mapped_column(
        String(MAX_DEVICE_TYPE_LENGTH),
        nullable=True,
    )
    referer: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationship back to short link
    short_link: Mapped["ShortLink"] = relationship(
        "ShortLink",
        back_populates="clicks",
    )

    __table_args__ = (
        Index("idx_link_clicks_short_link_id", "short_link_id"),
        Index("idx_link_clicks_clicked_at", "clicked_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<LinkClick(short_link_id={self.short_link_id!r}, "
            f"clicked_at={self.clicked_at!r})>"
        )


__all__ = [
    "LinkClick",
    "ShortLink",
    "MAX_CAMPAIGN_LENGTH",
    "MAX_CODE_LENGTH",
    "MAX_CONTENT_LENGTH",
    "MAX_DEVICE_TYPE_LENGTH",
    "MAX_IP_HASH_LENGTH",
    "MAX_MEDIUM_LENGTH",
    "MAX_POST_ID_LENGTH",
    "MAX_SOURCE_LENGTH",
    "MAX_SOURCE_TYPE_LENGTH",
]
