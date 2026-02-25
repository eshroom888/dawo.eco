"""Mattilsynet RSS/Atom feed parser.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 5: Parse RSS 2.0 and Atom feeds using feedparser.
"""

import hashlib
import logging
from datetime import datetime, UTC

import feedparser

from teams.dawo.scanners.mattilsynet.schemas import FeedItemRecord

logger = logging.getLogger(__name__)


class FeedParseError(Exception):
    """Error parsing RSS/Atom feed data."""


class MattilsynetFeedParser:
    """Parser for Mattilsynet RSS/Atom feeds.

    Parses feed bytes into FeedItemRecord DTOs using feedparser.
    Handles both RSS 2.0 and Atom feed formats.
    """

    def parse_feed(self, data: bytes, feed_name: str) -> list[FeedItemRecord]:
        """Parse RSS/Atom feed bytes into FeedItemRecord list.

        Args:
            data: Raw feed content bytes
            feed_name: Human-readable feed name for logging

        Returns:
            List of parsed feed items

        Raises:
            FeedParseError: If feed is malformed and has no entries
        """
        feed = feedparser.parse(data)

        if feed.bozo and not feed.entries:
            raise FeedParseError(
                f"Malformed feed '{feed_name}': {feed.bozo_exception}"
            )

        if not feed.entries:
            logger.warning("Feed '%s' returned zero items", feed_name)
            return []

        items: list[FeedItemRecord] = []
        for entry in feed.entries:
            published = self._extract_date(entry)
            content_str = entry.get("summary", entry.get("title", ""))
            content_hash = hashlib.sha256(
                content_str.encode("utf-8")
            ).hexdigest()

            items.append(
                FeedItemRecord(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    published_at=published,
                    summary=entry.get("summary", ""),
                    categories=tuple(
                        tag.get("term", "")
                        for tag in entry.get("tags", [])
                    ),
                    content_hash=content_hash,
                    feed_name=feed_name,
                )
            )

        logger.debug(
            "Parsed %d items from feed '%s'", len(items), feed_name
        )
        return items

    def _extract_date(self, entry: dict) -> datetime | None:
        """Extract publication date from feed entry.

        Args:
            entry: feedparser entry dict

        Returns:
            Timezone-aware datetime or None
        """
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=UTC)
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6], tzinfo=UTC)
        return None


__all__ = [
    "FeedParseError",
    "MattilsynetFeedParser",
]
