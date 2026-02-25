"""Tests for CompetitorContentParser.

Epic 6, Story 6-5, Task 5: Content parsing and health language detection.
"""

from datetime import datetime, UTC

import pytest

from teams.dawo.scanners.competitor.config import CompetitorConfig
from teams.dawo.scanners.competitor.parser import CompetitorContentParser
from teams.dawo.scanners.competitor.schemas import ScrapedPage


@pytest.fixture
def parser(health_keywords):
    return CompetitorContentParser(health_language_keywords=health_keywords)


class TestParseInstagramPost:
    """Tests for parse_instagram_post()."""

    def test_extracts_caption_hashtags_permalink_timestamp(self, parser, competitor_a):
        post = {
            "id": "123",
            "caption": "Our mushroom boosts immunity! #nootropics #wellness",
            "permalink": "https://www.instagram.com/p/ABC123/",
            "timestamp": "2026-02-10T12:00:00+0000",
            "like_count": 100,
            "comments_count": 5,
            "media_type": "IMAGE",
        }
        result = parser.parse_instagram_post(post, competitor_a)

        assert result.source_type == "instagram"
        assert result.competitor_name == "CompetitorA"
        assert "boosts immunity" in result.content_text
        assert "#nootropics" in result.hashtags
        assert "#wellness" in result.hashtags
        assert result.source_url == "https://www.instagram.com/p/ABC123/"
        assert result.account_or_domain == "competitor_a"

    def test_handles_missing_caption(self, parser, competitor_a):
        post = {
            "id": "456",
            "caption": None,
            "permalink": "https://www.instagram.com/p/XYZ789/",
            "timestamp": "2026-02-11T09:00:00+0000",
        }
        result = parser.parse_instagram_post(post, competitor_a)

        assert result.content_text == ""
        assert result.hashtags == []


class TestParseWebsitePage:
    """Tests for parse_website_page()."""

    def test_extracts_text_url_title(self, parser, competitor_a):
        page = ScrapedPage(
            url="https://competitor-a.com/products",
            title="Brain Boost",
            content_text="This supplement improves cognitive function.",
            meta_description="Brain supplement",
            links=[],
            fetched_at=datetime(2026, 2, 15, tzinfo=UTC),
        )
        result = parser.parse_website_page(page, competitor_a)

        assert result.source_type == "website"
        assert result.competitor_name == "CompetitorA"
        assert "improves cognitive function" in result.content_text
        assert result.source_url == "https://competitor-a.com/products"
        assert result.account_or_domain == "competitor-a.com"


class TestDetectHealthLanguage:
    """Tests for detect_health_language()."""

    def test_returns_true_for_english_health_keywords(self, parser):
        result = parser.detect_health_language("This supplement boosts immunity naturally")
        assert result.has_health_language is True
        assert "boost" in result.keywords_matched
        assert "immunity" in result.keywords_matched

    def test_returns_true_for_norwegian_health_keywords(self, parser):
        result = parser.detect_health_language("Produktet styrker immunforsvaret")
        assert result.has_health_language is True
        assert "styrker" in result.keywords_matched

    def test_returns_false_for_no_keywords(self, parser):
        result = parser.detect_health_language("Mushroom recipes for dinner tonight")
        assert result.has_health_language is False
        assert result.keywords_matched == []
        assert result.keyword_count == 0

    def test_case_insensitive_matching(self, parser):
        result = parser.detect_health_language("This product BOOSTS IMMUNITY")
        assert result.has_health_language is True
        assert "boost" in result.keywords_matched


class TestComputeContentHash:
    """Tests for compute_content_hash()."""

    def test_consistent_sha256(self, parser):
        hash1 = parser.compute_content_hash("Hello World")
        hash2 = parser.compute_content_hash("Hello World")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_normalized_whitespace(self, parser):
        hash1 = parser.compute_content_hash("Hello   World")
        hash2 = parser.compute_content_hash("Hello World")
        assert hash1 == hash2

    def test_normalized_case(self, parser):
        hash1 = parser.compute_content_hash("Hello World")
        hash2 = parser.compute_content_hash("hello world")
        assert hash1 == hash2
