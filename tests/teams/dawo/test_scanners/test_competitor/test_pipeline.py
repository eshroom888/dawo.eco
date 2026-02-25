"""Tests for CompetitorScanPipeline.

Epic 6, Story 6-5, Task 8: Pipeline orchestrator tests.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from teams.dawo.scanners.competitor.config import (
    CompetitorConfig,
    CompetitorScannerConfig,
    InstagramScanConfig,
    WebsiteScanConfig,
)
from teams.dawo.scanners.competitor.pipeline import CompetitorScanPipeline
from teams.dawo.scanners.competitor.schemas import (
    CompetitorScanStatus,
    ParsedContent,
    ScrapedPage,
)


def _make_parsed(
    name: str = "CompA",
    source: str = "instagram",
    health: bool = False,
    hash_val: str = "hash1",
) -> ParsedContent:
    return ParsedContent(
        source_type=source,
        competitor_name=name,
        source_url=f"https://example.com/{hash_val}",
        content_text=f"Content {hash_val}",
        hashtags=[],
        account_or_domain="comp_a",
        published_at=datetime(2026, 2, 10, tzinfo=UTC),
        content_hash=hash_val,
        has_health_language=health,
        health_keywords_matched=["boost"] if health else [],
    )


@pytest.fixture
def mock_event_emitter():
    emitter = AsyncMock()
    emitter.emit = AsyncMock()
    return emitter


@pytest.fixture
def mock_parser():
    parser = MagicMock()
    return parser


@pytest.fixture
def mock_dup_checker():
    checker = AsyncMock()
    checker.check_duplicates = AsyncMock()
    return checker


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    snapshot = MagicMock()
    snapshot.id = uuid4()
    repo.create_snapshot = AsyncMock(return_value=snapshot)
    repo.save_content_batch = AsyncMock(return_value=0)
    repo.update_snapshot_stats = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_website_client():
    client = AsyncMock()
    client.scrape_competitor_pages = AsyncMock(return_value=[])
    return client


@pytest.fixture
def ig_and_web_config():
    """Config with both Instagram and website enabled."""
    return CompetitorScannerConfig(
        competitors=(
            CompetitorConfig(
                name="CompA",
                instagram_username="comp_a",
                website_urls=("https://comp-a.com/products",),
                is_primary=True,
            ),
        ),
        health_language_keywords=("boost", "immunity"),
        instagram=InstagramScanConfig(enabled=True),
        websites=WebsiteScanConfig(enabled=True, request_delay_seconds=0),
        request_delay_seconds=0,
    )


@pytest.fixture
def ig_only_config():
    """Config with only Instagram enabled."""
    return CompetitorScannerConfig(
        competitors=(
            CompetitorConfig(name="CompA", instagram_username="comp_a"),
        ),
        health_language_keywords=("boost",),
        instagram=InstagramScanConfig(enabled=True),
        websites=WebsiteScanConfig(enabled=False),
        request_delay_seconds=0,
    )


@pytest.fixture
def web_only_config():
    """Config with only website enabled."""
    return CompetitorScannerConfig(
        competitors=(
            CompetitorConfig(
                name="CompA",
                website_urls=("https://comp-a.com",),
            ),
        ),
        health_language_keywords=("boost",),
        instagram=InstagramScanConfig(enabled=False),
        websites=WebsiteScanConfig(enabled=True, request_delay_seconds=0),
        request_delay_seconds=0,
    )


def _build_pipeline(
    config,
    mock_instagram_client,
    mock_website_client,
    mock_parser,
    mock_dup_checker,
    mock_repo,
    mock_event_emitter,
):
    return CompetitorScanPipeline(
        instagram_client=mock_instagram_client,
        website_client=mock_website_client,
        parser=mock_parser,
        duplicate_checker=mock_dup_checker,
        repository=mock_repo,
        event_emitter=mock_event_emitter,
        config=config,
    )


class TestFullPipeline:
    """Tests for complete pipeline execution."""

    @pytest.mark.asyncio
    async def test_instagram_and_website_saves_content(
        self, ig_and_web_config, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        # Setup: Instagram returns 1 post, website returns 1 page
        mock_instagram_client.get_user_media = AsyncMock(return_value=[
            {"id": "1", "caption": "Boost immunity", "permalink": "https://ig.com/p/1", "timestamp": "2026-02-10T12:00:00+0000"},
        ])
        scraped_page = ScrapedPage(
            url="https://comp-a.com/products", title="Products",
            content_text="Brain boost", meta_description="",
            links=[], fetched_at=datetime(2026, 2, 15, tzinfo=UTC),
        )
        mock_website_client.scrape_competitor_pages = AsyncMock(return_value=[scraped_page])

        ig_parsed = _make_parsed(health=True, hash_val="ig_hash")
        web_parsed = _make_parsed(source="website", health=True, hash_val="web_hash")
        mock_parser.parse_instagram_post.return_value = ig_parsed
        mock_parser.parse_website_page.return_value = web_parsed

        mock_dup_checker.check_duplicates = AsyncMock(return_value=[ig_parsed, web_parsed])
        mock_repo.save_content_batch = AsyncMock(return_value=2)

        pipeline = _build_pipeline(
            ig_and_web_config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.COMPLETE
        assert result.competitors_scanned == 1
        assert result.new_content_saved == 2

    @pytest.mark.asyncio
    async def test_instagram_only(
        self, ig_only_config, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        mock_instagram_client.get_user_media = AsyncMock(return_value=[
            {"id": "1", "caption": "Test post", "permalink": "https://ig.com/p/1", "timestamp": "2026-02-10T12:00:00+0000"},
        ])
        parsed = _make_parsed(hash_val="ig1")
        mock_parser.parse_instagram_post.return_value = parsed
        mock_dup_checker.check_duplicates = AsyncMock(return_value=[parsed])
        mock_repo.save_content_batch = AsyncMock(return_value=1)

        pipeline = _build_pipeline(
            ig_only_config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.COMPLETE
        mock_website_client.scrape_competitor_pages.assert_not_called()

    @pytest.mark.asyncio
    async def test_website_only(
        self, web_only_config, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        scraped = ScrapedPage(
            url="https://comp-a.com", title="Comp",
            content_text="Content", meta_description="",
            links=[], fetched_at=datetime(2026, 2, 15, tzinfo=UTC),
        )
        mock_website_client.scrape_competitor_pages = AsyncMock(return_value=[scraped])
        parsed = _make_parsed(source="website", hash_val="web1")
        mock_parser.parse_website_page.return_value = parsed
        mock_dup_checker.check_duplicates = AsyncMock(return_value=[parsed])
        mock_repo.save_content_batch = AsyncMock(return_value=1)

        pipeline = _build_pipeline(
            web_only_config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.COMPLETE
        mock_instagram_client.get_user_media.assert_not_called()


class TestDuplicateHandling:
    """Tests for duplicate content skipping."""

    @pytest.mark.asyncio
    async def test_duplicates_not_saved(
        self, ig_only_config, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        mock_instagram_client.get_user_media = AsyncMock(return_value=[
            {"id": "1", "caption": "Dup", "permalink": "https://ig.com/p/1", "timestamp": "2026-02-10T12:00:00+0000"},
        ])
        parsed = _make_parsed(hash_val="dup_hash")
        mock_parser.parse_instagram_post.return_value = parsed
        # Duplicate checker returns empty — all duplicates
        mock_dup_checker.check_duplicates = AsyncMock(return_value=[])
        mock_repo.save_content_batch = AsyncMock(return_value=0)

        pipeline = _build_pipeline(
            ig_only_config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.duplicates_skipped == 1
        assert result.new_content_saved == 0


class TestHealthLanguageEvents:
    """Tests for event emission on health language detection."""

    @pytest.mark.asyncio
    async def test_events_emitted_for_health_content(
        self, ig_only_config, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        mock_instagram_client.get_user_media = AsyncMock(return_value=[
            {"id": "1", "caption": "Boost!", "permalink": "https://ig.com/p/1", "timestamp": "2026-02-10T12:00:00+0000"},
        ])
        parsed = _make_parsed(health=True, hash_val="health_hash")
        mock_parser.parse_instagram_post.return_value = parsed
        mock_dup_checker.check_duplicates = AsyncMock(return_value=[parsed])
        mock_repo.save_content_batch = AsyncMock(return_value=1)

        pipeline = _build_pipeline(
            ig_only_config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.health_language_detected == 1
        mock_event_emitter.emit.assert_called()


class TestErrorHandling:
    """Tests for per-competitor error handling."""

    @pytest.mark.asyncio
    async def test_per_competitor_error_continues(
        self, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        config = CompetitorScannerConfig(
            competitors=(
                CompetitorConfig(name="FailComp", instagram_username="fail"),
                CompetitorConfig(name="OKComp", instagram_username="ok"),
            ),
            health_language_keywords=("boost",),
            request_delay_seconds=0,
        )

        call_count = 0

        async def side_effect(username, limit=25):
            nonlocal call_count
            call_count += 1
            if username == "fail":
                raise Exception("API error")
            return [{"id": "1", "caption": "OK", "permalink": "https://ig.com/p/1", "timestamp": "2026-02-10T12:00:00+0000"}]

        mock_instagram_client.get_user_media = AsyncMock(side_effect=side_effect)
        parsed = _make_parsed(name="OKComp", hash_val="ok_hash")
        mock_parser.parse_instagram_post.return_value = parsed
        mock_dup_checker.check_duplicates = AsyncMock(return_value=[parsed])
        mock_repo.save_content_batch = AsyncMock(return_value=1)

        pipeline = _build_pipeline(
            config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.PARTIAL
        assert result.competitors_scanned == 2
        assert len(result.errors) == 1
        assert "FailComp" in result.errors[0]

    @pytest.mark.asyncio
    async def test_all_fail_returns_failed(
        self, mock_instagram_client, mock_website_client,
        mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
    ):
        config = CompetitorScannerConfig(
            competitors=(
                CompetitorConfig(name="Fail1", instagram_username="f1"),
            ),
            health_language_keywords=("boost",),
            request_delay_seconds=0,
        )

        mock_instagram_client.get_user_media = AsyncMock(side_effect=Exception("API fail"))

        pipeline = _build_pipeline(
            config, mock_instagram_client, mock_website_client,
            mock_parser, mock_dup_checker, mock_repo, mock_event_emitter,
        )
        result = await pipeline.execute()

        assert result.status == CompetitorScanStatus.FAILED
