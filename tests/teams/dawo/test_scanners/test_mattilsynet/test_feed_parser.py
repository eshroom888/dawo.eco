"""Tests for Mattilsynet feed parser.

Epic 6, Story 6-3: Tasks 13.2-13.5.
"""

import pytest

from teams.dawo.scanners.mattilsynet.feed_parser import (
    FeedParseError,
    MattilsynetFeedParser,
)


@pytest.fixture
def parser() -> MattilsynetFeedParser:
    return MattilsynetFeedParser()


class TestParseFeedRSS:
    """Test parsing RSS 2.0 feeds."""

    def test_parses_valid_rss_items(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert len(items) == 2

    def test_extracts_title(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert items[0].title == "Nye regler for kosttilskudd"

    def test_extracts_url(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert items[0].url == "https://www.mattilsynet.no/nyheter/nye-regler-kosttilskudd"

    def test_extracts_published_date(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert items[0].published_at is not None
        assert items[0].published_at.year == 2026

    def test_extracts_summary(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert "kosttilskudd" in items[0].summary

    def test_extracts_categories(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert "Kosttilskudd" in items[0].categories

    def test_computes_content_hash(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "test_feed")
        assert len(items[0].content_hash) == 64  # SHA-256 hex

    def test_sets_feed_name(self, parser: MattilsynetFeedParser, sample_rss_feed: bytes) -> None:
        items = parser.parse_feed(sample_rss_feed, "my_feed")
        assert items[0].feed_name == "my_feed"


class TestParseFeedAtom:
    """Test parsing Atom feeds."""

    def test_parses_valid_atom_items(self, parser: MattilsynetFeedParser, sample_atom_feed: bytes) -> None:
        items = parser.parse_feed(sample_atom_feed, "atom_feed")
        assert len(items) == 1

    def test_extracts_atom_title(self, parser: MattilsynetFeedParser, sample_atom_feed: bytes) -> None:
        items = parser.parse_feed(sample_atom_feed, "atom_feed")
        assert "Tilbakekalling" in items[0].title

    def test_extracts_atom_url(self, parser: MattilsynetFeedParser, sample_atom_feed: bytes) -> None:
        items = parser.parse_feed(sample_atom_feed, "atom_feed")
        assert "tilbakekalling-soppekstrakt" in items[0].url

    def test_extracts_atom_date(self, parser: MattilsynetFeedParser, sample_atom_feed: bytes) -> None:
        items = parser.parse_feed(sample_atom_feed, "atom_feed")
        assert items[0].published_at is not None


class TestParseFeedErrors:
    """Test error handling."""

    def test_malformed_feed_raises_error(self, parser: MattilsynetFeedParser, malformed_feed: bytes) -> None:
        with pytest.raises(FeedParseError, match="Malformed feed"):
            parser.parse_feed(malformed_feed, "bad_feed")

    def test_empty_feed_returns_empty_list(self, parser: MattilsynetFeedParser, empty_feed: bytes) -> None:
        items = parser.parse_feed(empty_feed, "empty_feed")
        assert items == []
