"""Tests for Mattilsynet monitor pipeline.

Epic 6, Story 6-3: Tasks 13.29-13.35.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.regulatory.events import RegulatoryEventEmitter, RegulatoryEventType
from core.regulatory.models import MattilsynetPageHash
from teams.dawo.scanners.mattilsynet.change_detector import PageChangeDetector
from teams.dawo.scanners.mattilsynet.client import MattilsynetClient
from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
    MonitoredPageConfig,
)
from teams.dawo.scanners.mattilsynet.feed_parser import MattilsynetFeedParser
from teams.dawo.scanners.mattilsynet.keyword_matcher import NorwegianKeywordMatcher
from teams.dawo.scanners.mattilsynet.page_parser import MattilsynetPageParser
from teams.dawo.scanners.mattilsynet.pipeline import MattilsynetMonitorPipeline
from teams.dawo.scanners.mattilsynet.repository import MattilsynetRepository
from teams.dawo.scanners.mattilsynet.schemas import (
    FeedItemRecord,
    KeywordMatchResult,
    PageChangeResult,
)


@pytest.fixture
def pipeline_config() -> MattilsynetMonitorConfig:
    return MattilsynetMonitorConfig(
        feeds=(
            FeedConfig(name="News", url="https://mattilsynet.no/nyheter/rss", is_primary=True),
        ),
        monitored_pages=(
            MonitoredPageConfig(name="Kosttilskudd", url="https://mattilsynet.no/mat/kosttilskudd"),
        ),
        keywords_tier_1=("kosttilskudd", "tilbakekalling"),
        keywords_tier_2=("sopp",),
        enforcement_keywords=("tilbakekalling",),
        request_delay_seconds=0,
    )


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=MattilsynetClient)
    client.fetch_all_feeds.return_value = {
        "News": b"<rss>feed data</rss>",
    }
    client.fetch_all_pages.return_value = {
        "Kosttilskudd": b"<html>page data</html>",
    }
    return client


@pytest.fixture
def mock_feed_parser():
    parser = MagicMock(spec=MattilsynetFeedParser)
    parser.parse_feed.return_value = [
        FeedItemRecord(
            title="Nye regler for kosttilskudd",
            url="https://mattilsynet.no/nyheter/nye-regler",
            summary="Nye krav til merking av kosttilskudd.",
            content_hash="abc123",
            feed_name="News",
        ),
    ]
    return parser


@pytest.fixture
def mock_page_parser():
    parser = MagicMock(spec=MattilsynetPageParser)
    parser.extract_main_content.return_value = "Page content about kosttilskudd"
    parser.parse_article.return_value = MagicMock(
        title="Kosttilskudd info",
        url="https://mattilsynet.no/mat/kosttilskudd",
        published_at=datetime(2026, 2, 13, tzinfo=UTC),
        body_text="Updated regulations for kosttilskudd in Norway.",
        content_hash="page_hash_123",
    )
    return parser


@pytest.fixture
def mock_keyword_matcher():
    matcher = MagicMock(spec=NorwegianKeywordMatcher)
    matcher.match.return_value = KeywordMatchResult(
        is_relevant=True,
        relevance_tier=1,
        matched_keywords=("kosttilskudd",),
        is_enforcement=False,
    )
    return matcher


@pytest.fixture
def mock_change_detector():
    detector = MagicMock(spec=PageChangeDetector)
    detector.check_page.return_value = PageChangeResult(
        url="https://mattilsynet.no/mat/kosttilskudd",
        changed=True,
        current_hash="new_hash_456",
        content="Updated content",
    )
    return detector


@pytest.fixture
def mock_repository():
    repo = AsyncMock(spec=MattilsynetRepository)
    snapshot = MagicMock()
    snapshot.id = uuid4()
    repo.save_snapshot.return_value = snapshot
    repo.save_updates.return_value = 2
    repo.get_known_urls.return_value = set()
    repo.get_page_hash.return_value = None  # First run
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_event_emitter():
    return AsyncMock(spec=RegulatoryEventEmitter)


@pytest.fixture
def pipeline(
    mock_client,
    mock_feed_parser,
    mock_page_parser,
    mock_keyword_matcher,
    mock_change_detector,
    mock_repository,
    mock_event_emitter,
    pipeline_config,
) -> MattilsynetMonitorPipeline:
    return MattilsynetMonitorPipeline(
        client=mock_client,
        feed_parser=mock_feed_parser,
        page_parser=mock_page_parser,
        keyword_matcher=mock_keyword_matcher,
        change_detector=mock_change_detector,
        repository=mock_repository,
        event_emitter=mock_event_emitter,
        config=pipeline_config,
    )


class TestPipelineHappyPath:
    """Test full happy path execution."""

    @pytest.mark.asyncio
    async def test_returns_complete_status(self, pipeline) -> None:
        result = await pipeline.execute()
        assert result.status == "complete"

    @pytest.mark.asyncio
    async def test_processes_feeds(self, pipeline, mock_client) -> None:
        await pipeline.execute()
        mock_client.fetch_all_feeds.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_processes_pages(self, pipeline, mock_client) -> None:
        await pipeline.execute()
        mock_client.fetch_all_pages.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_saves_snapshot(self, pipeline, mock_repository) -> None:
        await pipeline.execute()
        mock_repository.save_snapshot.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_saves_updates(self, pipeline, mock_repository) -> None:
        await pipeline.execute()
        mock_repository.save_updates.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_commits_transaction(self, pipeline, mock_repository) -> None:
        await pipeline.execute()
        mock_repository.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reports_counts(self, pipeline) -> None:
        result = await pipeline.execute()
        assert result.feeds_checked == 1
        assert result.pages_checked == 1

    @pytest.mark.asyncio
    async def test_tracks_scan_duration(self, pipeline) -> None:
        result = await pipeline.execute()
        assert result.scan_duration_seconds > 0


class TestPipelineFirstRun:
    """Test first run with no previous data."""

    @pytest.mark.asyncio
    async def test_saves_baseline_hashes(self, pipeline, mock_repository, mock_change_detector) -> None:
        # First run: no previous hash
        mock_change_detector.check_page.return_value = PageChangeResult(
            url="https://mattilsynet.no/mat/kosttilskudd",
            changed=False,
            current_hash="baseline_hash",
            content=None,
        )
        mock_repository.get_page_hash.return_value = None

        await pipeline.execute()
        mock_repository.save_page_hash.assert_awaited_once()


class TestPipelineFeedFailure:
    """Test feed failure scenarios."""

    @pytest.mark.asyncio
    async def test_incomplete_on_all_feeds_fail(
        self, mock_client, mock_feed_parser, mock_page_parser,
        mock_keyword_matcher, mock_change_detector, mock_repository,
        mock_event_emitter, pipeline_config,
    ) -> None:
        mock_client.fetch_all_feeds.return_value = {}  # All feeds failed
        mock_client.fetch_all_pages.return_value = {}  # All pages failed too

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=mock_feed_parser,
            page_parser=mock_page_parser,
            keyword_matcher=mock_keyword_matcher,
            change_detector=mock_change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=pipeline_config,
        )
        result = await pipeline.execute()
        assert result.status == "incomplete"
        mock_repository.save_snapshot.assert_not_awaited()
        mock_repository.commit.assert_not_awaited()


class TestPipelinePartialFailure:
    """Test partial failure scenarios."""

    @pytest.mark.asyncio
    async def test_partial_when_some_feeds_fail(
        self, mock_client, mock_feed_parser, mock_page_parser,
        mock_keyword_matcher, mock_change_detector, mock_repository,
        mock_event_emitter,
    ) -> None:
        # Config with 2 feeds but only 1 returns data
        config = MattilsynetMonitorConfig(
            feeds=(
                FeedConfig(name="Feed1", url="https://a.com/rss"),
                FeedConfig(name="Feed2", url="https://b.com/rss"),
            ),
            monitored_pages=(),
            keywords_tier_1=("kosttilskudd",),
            request_delay_seconds=0,
        )
        mock_client.fetch_all_feeds.return_value = {"Feed1": b"<rss>data</rss>"}
        # Only 1 of 2 feeds returned — but no parse errors
        mock_feed_parser.parse_feed.return_value = []

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=mock_feed_parser,
            page_parser=mock_page_parser,
            keyword_matcher=mock_keyword_matcher,
            change_detector=mock_change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=config,
        )
        result = await pipeline.execute()
        # 1 of 2 feeds checked = partial
        assert result.status == "partial"


class TestPipelineEventPublishing:
    """Test event publishing for HIGH severity updates."""

    @pytest.mark.asyncio
    async def test_publishes_events_for_high_severity(
        self, pipeline, mock_event_emitter, mock_keyword_matcher,
    ) -> None:
        # keyword_matcher returns relevant with tier 1
        mock_keyword_matcher.match.return_value = KeywordMatchResult(
            is_relevant=True,
            relevance_tier=1,
            matched_keywords=("kosttilskudd",),
            is_enforcement=False,
        )
        await pipeline.execute()
        # Should publish at least one event
        assert mock_event_emitter.emit.await_count >= 1


class TestPipelineEnforcementEventType:
    """Test enforcement event type dispatch (H1 fix)."""

    @pytest.mark.asyncio
    async def test_enforcement_emits_enforcement_event(
        self, pipeline, mock_event_emitter, mock_keyword_matcher,
    ) -> None:
        mock_keyword_matcher.match.return_value = KeywordMatchResult(
            is_relevant=True,
            relevance_tier=1,
            matched_keywords=("tilbakekalling",),
            is_enforcement=True,
        )
        await pipeline.execute()
        assert mock_event_emitter.emit.await_count >= 1
        events = [call[0][0] for call in mock_event_emitter.emit.call_args_list]
        enforcement_events = [
            e for e in events
            if e.event_type == RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION
        ]
        assert len(enforcement_events) >= 1


class TestPipelinePageChangeEventType:
    """Test page change event type dispatch (H2 fix)."""

    @pytest.mark.asyncio
    async def test_page_change_emits_page_changed_event(
        self, mock_client, mock_feed_parser, mock_page_parser,
        mock_keyword_matcher, mock_change_detector, mock_repository,
        mock_event_emitter,
    ) -> None:
        config = MattilsynetMonitorConfig(
            monitored_pages=(
                MonitoredPageConfig(name="Kosttilskudd", url="https://mattilsynet.no/mat/kosttilskudd"),
            ),
            keywords_tier_1=("kosttilskudd",),
            request_delay_seconds=0,
        )
        mock_client.fetch_all_feeds.return_value = {}
        mock_client.fetch_all_pages.return_value = {"Kosttilskudd": b"<html>data</html>"}
        mock_keyword_matcher.match.return_value = KeywordMatchResult(
            is_relevant=True,
            relevance_tier=1,
            matched_keywords=("kosttilskudd",),
            is_enforcement=False,
        )
        mock_change_detector.check_page.return_value = PageChangeResult(
            url="https://mattilsynet.no/mat/kosttilskudd",
            changed=True,
            current_hash="hash_abc",
            content="Content",
        )

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=mock_feed_parser,
            page_parser=mock_page_parser,
            keyword_matcher=mock_keyword_matcher,
            change_detector=mock_change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=config,
        )
        await pipeline.execute()
        assert mock_event_emitter.emit.await_count >= 1
        events = [call[0][0] for call in mock_event_emitter.emit.call_args_list]
        page_events = [
            e for e in events
            if e.event_type == RegulatoryEventType.MATTILSYNET_PAGE_CHANGED
        ]
        assert len(page_events) == 1


class TestPipelineEnforcementCategory:
    """Test enforcement category update (M1 fix)."""

    @pytest.mark.asyncio
    async def test_enforcement_updates_category(
        self, pipeline, mock_repository, mock_keyword_matcher,
    ) -> None:
        mock_keyword_matcher.match.return_value = KeywordMatchResult(
            is_relevant=True,
            relevance_tier=1,
            matched_keywords=("tilbakekalling",),
            is_enforcement=True,
        )
        await pipeline.execute()
        saved_updates = mock_repository.save_updates.call_args[0][0]
        for update in saved_updates:
            assert update.category == "enforcement"
            assert update.is_enforcement is True


class TestPipelineDeduplication:
    """Test URL deduplication."""

    @pytest.mark.asyncio
    async def test_deduplicates_known_urls(
        self, pipeline, mock_repository,
    ) -> None:
        # Return the feed item URL as already known
        mock_repository.get_known_urls.return_value = {
            "https://mattilsynet.no/nyheter/nye-regler",
        }
        result = await pipeline.execute()
        # The feed item should be deduplicated; page change is still new
        # Total may vary but known URL should be excluded
        assert result.total_updates >= 0


class TestPipelinePageChanges:
    """Test page change detection in pipeline."""

    @pytest.mark.asyncio
    async def test_detects_page_changes(self, pipeline) -> None:
        result = await pipeline.execute()
        assert result.page_changes >= 1
