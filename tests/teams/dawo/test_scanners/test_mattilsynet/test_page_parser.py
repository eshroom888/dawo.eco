"""Tests for Mattilsynet page parser.

Epic 6, Story 6-3: Tasks 13.6-13.9.
"""

import pytest

from teams.dawo.scanners.mattilsynet.page_parser import (
    MattilsynetPageParser,
    PageParseError,
)


@pytest.fixture
def parser() -> MattilsynetPageParser:
    return MattilsynetPageParser()


class TestExtractMainContent:
    """Test extract_main_content method."""

    def test_strips_nav_and_footer(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        content = parser.extract_main_content(sample_page_html)
        assert "Navigation content to strip" not in content
        assert "Footer content to strip" not in content

    def test_extracts_article_content(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        content = parser.extract_main_content(sample_page_html)
        assert "kosttilskudd" in content

    def test_uses_fallback_selectors(self, parser: MattilsynetPageParser, sample_page_html_fallback: bytes) -> None:
        content = parser.extract_main_content(sample_page_html_fallback)
        assert "Fallback Title" in content or "Content found" in content

    def test_raises_on_no_selectors(self, parser: MattilsynetPageParser, sample_page_html_no_selectors: bytes) -> None:
        with pytest.raises(PageParseError, match="No content found"):
            parser.extract_main_content(sample_page_html_no_selectors)


class TestParseArticle:
    """Test parse_article method."""

    def test_extracts_title(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        article = parser.parse_article(sample_page_html, "https://example.com")
        assert "kosttilskuddsforskriften" in article.title

    def test_extracts_date(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        article = parser.parse_article(sample_page_html, "https://example.com")
        assert article.published_at is not None
        assert article.published_at.year == 2026

    def test_extracts_body(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        article = parser.parse_article(sample_page_html, "https://example.com")
        assert "kosttilskudd" in article.body_text

    def test_computes_content_hash(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        article = parser.parse_article(sample_page_html, "https://example.com")
        assert len(article.content_hash) == 64

    def test_sets_url(self, parser: MattilsynetPageParser, sample_page_html: bytes) -> None:
        article = parser.parse_article(sample_page_html, "https://example.com/test")
        assert article.url == "https://example.com/test"
