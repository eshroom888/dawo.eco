"""Tests for news harvester."""

from datetime import datetime, timezone

import pytest

from teams.dawo.scanners.news.schemas import RawNewsArticle, HarvestedArticle
from teams.dawo.scanners.news.harvester import NewsHarvester


class TestNewsHarvester:
    """Tests for NewsHarvester."""

    @pytest.fixture
    def harvester(self) -> NewsHarvester:
        """Create harvester instance."""
        return NewsHarvester()

    def _make_raw_article(
        self,
        title: str = "Test Article",
        summary: str = "Test summary",
        has_html: bool = False,
    ) -> RawNewsArticle:
        """Helper to create raw article."""
        content = summary
        if has_html:
            content = f"<p><strong>{summary}</strong></p>"

        return RawNewsArticle(
            title=title,
            summary=content,
            url="https://example.com/article",
            published=datetime.now(timezone.utc),
            source_name="TestSource",
            is_tier_1=False,
        )

    def test_harvest_single_article(
        self, harvester: NewsHarvester
    ) -> None:
        """Test harvesting a single article."""
        raw = self._make_raw_article()

        result = harvester.harvest([raw])

        assert len(result) == 1
        assert isinstance(result[0], HarvestedArticle)
        assert result[0].title == "Test Article"
        assert result[0].summary == "Test summary"

    def test_harvest_multiple_articles(
        self, harvester: NewsHarvester
    ) -> None:
        """Test harvesting multiple articles."""
        articles = [
            self._make_raw_article(title=f"Article {i}")
            for i in range(3)
        ]

        result = harvester.harvest(articles)

        assert len(result) == 3
        assert result[0].title == "Article 0"
        assert result[1].title == "Article 1"
        assert result[2].title == "Article 2"

    def test_harvest_cleans_html(
        self, harvester: NewsHarvester
    ) -> None:
        """Test that HTML is cleaned from summary."""
        raw = self._make_raw_article(
            summary="<p>This is <strong>bold</strong> text.</p>",
            has_html=True,
        )

        result = harvester.harvest([raw])

        assert len(result) == 1
        # HTML should be stripped
        assert "<p>" not in result[0].summary
        assert "<strong>" not in result[0].summary
        assert "bold" in result[0].summary

    def test_harvest_strips_whitespace(
        self, harvester: NewsHarvester
    ) -> None:
        """Test that whitespace is stripped from title."""
        raw = self._make_raw_article(title="  Test Title  ")

        result = harvester.harvest([raw])

        assert result[0].title == "Test Title"

    def test_harvest_preserves_metadata(
        self, harvester: NewsHarvester
    ) -> None:
        """Test that article metadata is preserved."""
        now = datetime.now(timezone.utc)
        raw = RawNewsArticle(
            title="Test",
            summary="Summary",
            url="https://example.com/test",
            published=now,
            source_name="SourceA",
            is_tier_1=True,
        )

        result = harvester.harvest([raw])

        assert result[0].url == "https://example.com/test"
        assert result[0].published == now
        assert result[0].source_name == "SourceA"
        assert result[0].is_tier_1 is True

    def test_harvest_truncates_long_summary(
        self, harvester: NewsHarvester
    ) -> None:
        """Test that very long summaries are truncated."""
        long_summary = "A" * 15000  # Exceeds MAX_SUMMARY_LENGTH (10000)
        raw = self._make_raw_article(summary=long_summary)

        result = harvester.harvest([raw])

        assert len(result[0].summary) <= 10003  # MAX_SUMMARY_LENGTH + "..."
        assert result[0].summary.endswith("...")

    def test_harvest_empty_list(
        self, harvester: NewsHarvester
    ) -> None:
        """Test harvesting empty list."""
        result = harvester.harvest([])

        assert result == []

    def test_harvest_handles_empty_summary(
        self, harvester: NewsHarvester
    ) -> None:
        """Test handling of article with empty summary."""
        raw = self._make_raw_article(summary="")

        result = harvester.harvest([raw])

        assert len(result) == 1
        assert result[0].summary == ""
