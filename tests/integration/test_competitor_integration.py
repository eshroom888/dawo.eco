"""Integration tests for competitor content scanner pipeline.

Story 6-5, Task 13: End-to-end integration tests.

Tests the full flow from config → pipeline → mock sources → parse → dedup → store → events,
verifying all components work together correctly.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventEmitter,
    RegulatoryEventType,
)
from teams.dawo.scanners.competitor.config import (
    CompetitorConfig,
    CompetitorScannerConfig,
    InstagramScanConfig,
    WebsiteScanConfig,
)
from teams.dawo.scanners.competitor.duplicate_checker import CompetitorDuplicateChecker
from teams.dawo.scanners.competitor.parser import CompetitorContentParser
from teams.dawo.scanners.competitor.pipeline import CompetitorScanPipeline
from teams.dawo.scanners.competitor.repository import CompetitorRepository
from teams.dawo.scanners.competitor.schemas import (
    CompetitorScanStatus,
    ParsedContent,
    ScrapedPage,
)
from teams.dawo.scanners.competitor.website_client import WebsiteScraperClient


@pytest.fixture
def competitor():
    return CompetitorConfig(
        name="TestComp",
        instagram_username="testcomp",
        website_urls=("https://testcomp.com/products",),
        is_primary=True,
    )


@pytest.fixture
def health_keywords():
    return ("boost", "improve", "enhance", "immunity", "cognitive", "styrker")


@pytest.fixture
def config(competitor, health_keywords):
    return CompetitorScannerConfig(
        competitors=(competitor,),
        health_language_keywords=health_keywords,
        request_delay_seconds=0,
        instagram=InstagramScanConfig(
            enabled=True, scan_window_days=7, max_posts_per_competitor=25,
        ),
        websites=WebsiteScanConfig(
            enabled=True, request_delay_seconds=0, max_pages_per_domain=20,
        ),
    )


@pytest.fixture
def parser(health_keywords):
    return CompetitorContentParser(health_language_keywords=health_keywords)


@pytest.fixture
def mock_session():
    """Mock AsyncSession that tracks added objects."""
    session = AsyncMock()
    added_objects = []

    def track_add(obj):
        added_objects.append(obj)

    def track_add_all(objs):
        added_objects.extend(objs)

    session.add = MagicMock(side_effect=track_add)
    session.add_all = MagicMock(side_effect=track_add_all)
    session.commit = AsyncMock()
    session._added = added_objects
    return session


@pytest.fixture
def mock_dup_checker_fresh():
    """Duplicate checker that considers all items new."""
    checker = AsyncMock(spec=CompetitorDuplicateChecker)
    checker.check_duplicates = AsyncMock(side_effect=lambda items: items)
    return checker


@pytest.fixture
def mock_dup_checker_all_dupes():
    """Duplicate checker that considers all items duplicates."""
    checker = AsyncMock(spec=CompetitorDuplicateChecker)
    checker.check_duplicates = AsyncMock(return_value=[])
    return checker


@pytest.fixture
def mock_repo():
    """Mock repository with snapshot tracking."""
    repo = AsyncMock(spec=CompetitorRepository)

    snapshot = MagicMock()
    snapshot.id = "snapshot-001"
    repo.create_snapshot = AsyncMock(return_value=snapshot)
    repo.save_content_batch = AsyncMock(return_value=0)
    repo.update_snapshot_stats = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_emitter():
    """Mock event emitter that tracks emitted events."""
    emitter = AsyncMock(spec=RegulatoryEventEmitter)
    emitter.emit = AsyncMock()
    return emitter


@pytest.fixture
def sample_ig_posts():
    """Instagram posts — one with health language, one without."""
    return [
        {
            "id": "post-001",
            "caption": "Our lion's mane extract boosts cognitive function! #nootropics",
            "permalink": "https://www.instagram.com/p/ABC123/",
            "timestamp": "2026-02-10T12:00:00+0000",
            "like_count": 150,
            "comments_count": 12,
            "media_type": "IMAGE",
        },
        {
            "id": "post-002",
            "caption": "Beautiful mushroom harvest today #mushrooms",
            "permalink": "https://www.instagram.com/p/DEF456/",
            "timestamp": "2026-02-11T09:30:00+0000",
            "like_count": 85,
            "comments_count": 5,
            "media_type": "IMAGE",
        },
    ]


@pytest.fixture
def sample_scraped_page():
    """Website page with health language."""
    return ScrapedPage(
        url="https://testcomp.com/products",
        title="Brain Boost Lion's Mane",
        content_text="This supplement improves memory and boosts immunity naturally.",
        meta_description="Mushroom supplement",
        links=["https://testcomp.com/about"],
        fetched_at=datetime(2026, 2, 15, 3, 0, 0, tzinfo=UTC),
    )


class TestFullFlowInstagram:
    """13.1: Full flow config → pipeline → Instagram → parse → dedup → repository."""

    @pytest.mark.asyncio
    async def test_instagram_posts_parsed_deduped_and_saved(
        self,
        config,
        parser,
        mock_dup_checker_fresh,
        mock_repo,
        mock_emitter,
        sample_ig_posts,
        competitor,
    ):
        """Instagram posts flow through parse → dedup → save with correct counts."""
        mock_ig = AsyncMock()
        mock_ig.get_user_media = AsyncMock(return_value=sample_ig_posts)

        mock_website = AsyncMock()
        mock_website.scrape_competitor_pages = AsyncMock(return_value=[])

        # Set repo to return saved count matching new items
        mock_repo.save_content_batch = AsyncMock(return_value=2)

        pipeline = CompetitorScanPipeline(
            instagram_client=mock_ig,
            website_client=mock_website,
            parser=parser,
            duplicate_checker=mock_dup_checker_fresh,
            repository=mock_repo,
            event_emitter=mock_emitter,
            config=config,
        )

        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.COMPLETE
        assert result.total_content_found == 2
        assert result.new_content_saved == 2
        assert result.duplicates_skipped == 0
        mock_ig.get_user_media.assert_called_once_with(
            username="testcomp", limit=25,
        )
        mock_repo.create_snapshot.assert_called_once()
        mock_repo.save_content_batch.assert_called_once()
        mock_repo.commit.assert_called()


class TestFullFlowWebsite:
    """13.2: Full flow config → pipeline → website → parse → dedup → repository."""

    @pytest.mark.asyncio
    async def test_website_pages_parsed_deduped_and_saved(
        self,
        config,
        parser,
        mock_dup_checker_fresh,
        mock_repo,
        mock_emitter,
        sample_scraped_page,
        competitor,
    ):
        """Website pages flow through parse → dedup → save with correct counts."""
        # Disable Instagram for this test
        config_web_only = CompetitorScannerConfig(
            competitors=config.competitors,
            health_language_keywords=config.health_language_keywords,
            request_delay_seconds=0,
            instagram=InstagramScanConfig(enabled=False),
            websites=WebsiteScanConfig(enabled=True, request_delay_seconds=0),
        )

        mock_ig = AsyncMock()
        mock_website = AsyncMock()
        mock_website.scrape_competitor_pages = AsyncMock(
            return_value=[sample_scraped_page],
        )

        mock_repo.save_content_batch = AsyncMock(return_value=1)

        pipeline = CompetitorScanPipeline(
            instagram_client=mock_ig,
            website_client=mock_website,
            parser=parser,
            duplicate_checker=mock_dup_checker_fresh,
            repository=mock_repo,
            event_emitter=mock_emitter,
            config=config_web_only,
        )

        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.COMPLETE
        assert result.total_content_found == 1
        assert result.new_content_saved == 1
        mock_website.scrape_competitor_pages.assert_called_once_with(competitor)
        mock_repo.save_content_batch.assert_called_once()


class TestDeduplication:
    """13.3: Second run with same content saves 0 new items."""

    @pytest.mark.asyncio
    async def test_duplicate_content_not_saved(
        self,
        config,
        parser,
        mock_dup_checker_all_dupes,
        mock_repo,
        mock_emitter,
        sample_ig_posts,
    ):
        """All items are duplicates → 0 saved, duplicates_skipped > 0."""
        mock_ig = AsyncMock()
        mock_ig.get_user_media = AsyncMock(return_value=sample_ig_posts)

        mock_website = AsyncMock()
        mock_website.scrape_competitor_pages = AsyncMock(return_value=[])

        pipeline = CompetitorScanPipeline(
            instagram_client=mock_ig,
            website_client=mock_website,
            parser=parser,
            duplicate_checker=mock_dup_checker_all_dupes,
            repository=mock_repo,
            event_emitter=mock_emitter,
            config=config,
        )

        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.COMPLETE
        assert result.total_content_found == 2
        assert result.new_content_saved == 0
        assert result.duplicates_skipped == 2
        # save_content_batch should NOT be called when no new items
        mock_repo.save_content_batch.assert_not_called()


class TestHealthLanguageFlagging:
    """13.4: Content with health language flagged correctly."""

    @pytest.mark.asyncio
    async def test_health_language_detected_in_parsed_content(
        self,
        config,
        parser,
        mock_dup_checker_fresh,
        mock_repo,
        mock_emitter,
        sample_ig_posts,
    ):
        """Posts with 'boost' + 'cognitive' → has_health_language=True, counted in result."""
        mock_ig = AsyncMock()
        mock_ig.get_user_media = AsyncMock(return_value=sample_ig_posts)

        mock_website = AsyncMock()
        mock_website.scrape_competitor_pages = AsyncMock(return_value=[])

        mock_repo.save_content_batch = AsyncMock(return_value=2)

        pipeline = CompetitorScanPipeline(
            instagram_client=mock_ig,
            website_client=mock_website,
            parser=parser,
            duplicate_checker=mock_dup_checker_fresh,
            repository=mock_repo,
            event_emitter=mock_emitter,
            config=config,
        )

        result = await pipeline.execute()

        # First post has "boosts cognitive" → health language
        # Second post has no health keywords
        assert result.health_language_detected >= 1

        # Verify the parsed content passed to save_content_batch has correct flags
        saved_items = mock_repo.save_content_batch.call_args[0][0]
        health_items = [item for item in saved_items if item.has_health_language]
        assert len(health_items) >= 1
        assert any("boost" in item.health_keywords_matched for item in health_items)


class TestHealthLanguageEventEmission:
    """13.5: Health language content emits COMPETITOR_HEALTH_LANGUAGE_DETECTED event."""

    @pytest.mark.asyncio
    async def test_event_emitted_for_health_language_content(
        self,
        config,
        parser,
        mock_dup_checker_fresh,
        mock_repo,
        mock_emitter,
        sample_ig_posts,
    ):
        """Health language in new content → RegulatoryEvent emitted."""
        mock_ig = AsyncMock()
        mock_ig.get_user_media = AsyncMock(return_value=sample_ig_posts)

        mock_website = AsyncMock()
        mock_website.scrape_competitor_pages = AsyncMock(return_value=[])

        mock_repo.save_content_batch = AsyncMock(return_value=2)

        pipeline = CompetitorScanPipeline(
            instagram_client=mock_ig,
            website_client=mock_website,
            parser=parser,
            duplicate_checker=mock_dup_checker_fresh,
            repository=mock_repo,
            event_emitter=mock_emitter,
            config=config,
        )

        result = await pipeline.execute()

        # At least one event should be emitted (for post with "boosts cognitive")
        mock_emitter.emit.assert_called()

        # Verify event type
        emitted_event = mock_emitter.emit.call_args[0][0]
        assert emitted_event.event_type == RegulatoryEventType.COMPETITOR_HEALTH_LANGUAGE_DETECTED
        assert emitted_event.data["competitor_name"] == "TestComp"
        assert emitted_event.data["source_type"] == "instagram"
        assert "keywords_matched" in emitted_event.data
