"""Tests for competitor scanner schemas/DTOs.

Epic 6, Story 6-5, Task 9: Data transfer objects.
"""

from datetime import datetime, UTC
from enum import Enum

import pytest

from teams.dawo.scanners.competitor.schemas import (
    ParsedContent,
    ScrapedPage,
    RobotsTxtResult,
    HealthLanguageResult,
    CompetitorScanResult,
    CompetitorScanStatus,
)


class TestParsedContent:
    """Tests for ParsedContent dataclass."""

    def test_creation_with_all_fields(self):
        pc = ParsedContent(
            source_type="instagram",
            competitor_name="CompA",
            source_url="https://instagram.com/p/ABC123",
            content_text="Great mushroom supplement!",
            hashtags=["#mushroom", "#wellness"],
            account_or_domain="comp_a",
            published_at=datetime(2026, 2, 10, tzinfo=UTC),
            content_hash="abc123hash",
            has_health_language=True,
            health_keywords_matched=["boost", "immunity"],
        )
        assert pc.source_type == "instagram"
        assert pc.competitor_name == "CompA"
        assert pc.has_health_language is True
        assert len(pc.health_keywords_matched) == 2


class TestScrapedPage:
    """Tests for ScrapedPage dataclass."""

    def test_creation(self):
        page = ScrapedPage(
            url="https://comp.com/products",
            title="Brain Boost",
            content_text="Our supplement enhances cognitive function.",
            meta_description="Brain boost supplement",
            links=["https://comp.com/about"],
            fetched_at=datetime(2026, 2, 15, tzinfo=UTC),
        )
        assert page.url == "https://comp.com/products"
        assert page.title == "Brain Boost"
        assert len(page.links) == 1


class TestRobotsTxtResult:
    """Tests for RobotsTxtResult dataclass."""

    def test_creation(self):
        result = RobotsTxtResult(
            allowed=True,
            checked_at=datetime(2026, 2, 15, tzinfo=UTC),
            robots_url="https://comp.com/robots.txt",
        )
        assert result.allowed is True
        assert result.robots_url == "https://comp.com/robots.txt"


class TestHealthLanguageResult:
    """Tests for HealthLanguageResult dataclass."""

    def test_creation(self):
        result = HealthLanguageResult(
            has_health_language=True,
            keywords_matched=["boost", "immunity"],
            keyword_count=2,
        )
        assert result.has_health_language is True
        assert result.keyword_count == 2


class TestCompetitorScanResult:
    """Tests for CompetitorScanResult dataclass."""

    def test_creation(self):
        result = CompetitorScanResult(
            status=CompetitorScanStatus.COMPLETE,
            competitors_scanned=3,
            total_content_found=25,
            new_content_saved=20,
            duplicates_skipped=5,
            health_language_detected=8,
            errors=[],
        )
        assert result.status == CompetitorScanStatus.COMPLETE
        assert result.competitors_scanned == 3
        assert result.total_content_found == 25


class TestCompetitorScanStatus:
    """Tests for CompetitorScanStatus enum."""

    def test_enum_values(self):
        assert CompetitorScanStatus.COMPLETE == "complete"
        assert CompetitorScanStatus.PARTIAL == "partial"
        assert CompetitorScanStatus.FAILED == "failed"

    def test_is_str_enum(self):
        assert issubclass(CompetitorScanStatus, str)
        assert issubclass(CompetitorScanStatus, Enum)
