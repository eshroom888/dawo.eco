"""Integration tests for Mattilsynet Regulatory Monitor.

Story 6-3, Task 14: Integration tests.

Tests the full pipeline flow with real component interactions
(mocked HTTP only, real parsing/keyword matching/change detection).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from core.regulatory.events import RegulatoryEventEmitter
from teams.dawo.scanners.mattilsynet.change_detector import PageChangeDetector
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


# ─── Test data ──────────────────────────────────────────────────────────────

RSS_FEED_WITH_RELEVANT_ITEM = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Mattilsynet Nyheter</title>
  <item>
    <title>Nye regler for kosttilskudd</title>
    <link>https://www.mattilsynet.no/nyheter/nye-regler-kosttilskudd</link>
    <pubDate>Thu, 13 Feb 2026 07:00:00 +0100</pubDate>
    <description>Mattilsynet innforer nye krav til merking av kosttilskudd.</description>
    <category>Kosttilskudd</category>
  </item>
  <item>
    <title>Generell nyhet om dyrevelferd</title>
    <link>https://www.mattilsynet.no/nyheter/dyrevelferd</link>
    <pubDate>Wed, 12 Feb 2026 10:00:00 +0100</pubDate>
    <description>En generell nyhet om dyrevelferd uten relevans.</description>
  </item>
</channel>
</rss>"""

ENFORCEMENT_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Mattilsynet Varsler</title>
  <item>
    <title>Tilbakekalling av kosttilskudd med ulovlige helsep\xc3\xa5stander</title>
    <link>https://www.mattilsynet.no/varsler/tilbakekalling-kosttilskudd</link>
    <pubDate>Thu, 13 Feb 2026 09:00:00 +0100</pubDate>
    <description>Mattilsynet har fattet vedtak om tilbakekalling av et soppbasert kosttilskudd.</description>
  </item>
</channel>
</rss>"""

PAGE_HTML = b"""<html><body>
<nav>Navigation content to strip</nav>
<main class="content-area">
  <h1>Kosttilskudd - regelverk</h1>
  <time datetime="2026-02-10">10. februar 2026</time>
  <article class="article-body">
    <p>Oppdatert informasjon om kosttilskudd og helsep\xc3\xa5stander.</p>
    <p>Nye krav til merking trer i kraft 1. mars 2026.</p>
  </article>
</main>
<footer>Footer content to strip</footer>
</body></html>"""

PAGE_HTML_UPDATED = b"""<html><body>
<nav>Navigation content to strip</nav>
<main class="content-area">
  <h1>Kosttilskudd - regelverk</h1>
  <time datetime="2026-02-13">13. februar 2026</time>
  <article class="article-body">
    <p>Oppdatert informasjon om kosttilskudd og helsep\xc3\xa5stander.</p>
    <p>ENDRET: Nye krav til merking trer i kraft 15. april 2026.</p>
    <p>Tilleggskrav for funksjonssopp og adaptogener.</p>
  </article>
</main>
<footer>Footer content to strip</footer>
</body></html>"""

CONFIG = MattilsynetMonitorConfig(
    feeds=(
        FeedConfig(name="Nyheter", url="https://mattilsynet.no/nyheter/rss", is_primary=True),
    ),
    monitored_pages=(
        MonitoredPageConfig(name="Kosttilskudd", url="https://mattilsynet.no/mat/kosttilskudd"),
    ),
    keywords_tier_1=("kosttilskudd", "helsep\u00e5stander", "tilbakekalling"),
    keywords_tier_2=("sopp", "funksjonssopp", "adaptogener"),
    enforcement_keywords=("tilbakekalling", "vedtak"),
    request_delay_seconds=0,
)

CONFIG_TWO_FEEDS = MattilsynetMonitorConfig(
    feeds=(
        FeedConfig(name="Nyheter", url="https://mattilsynet.no/nyheter/rss", is_primary=True),
        FeedConfig(name="Varsler", url="https://mattilsynet.no/varsler/rss"),
    ),
    monitored_pages=(
        MonitoredPageConfig(name="Kosttilskudd", url="https://mattilsynet.no/mat/kosttilskudd"),
    ),
    keywords_tier_1=("kosttilskudd", "helsep\u00e5stander", "tilbakekalling"),
    keywords_tier_2=("sopp", "funksjonssopp"),
    enforcement_keywords=("tilbakekalling", "vedtak"),
    request_delay_seconds=0,
)


# ─── Shared fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def feed_parser():
    return MattilsynetFeedParser()


@pytest.fixture
def page_parser():
    return MattilsynetPageParser()


@pytest.fixture
def keyword_matcher():
    return NorwegianKeywordMatcher(CONFIG)


@pytest.fixture
def change_detector():
    return PageChangeDetector()


@pytest.fixture
def mock_repository():
    repo = AsyncMock(spec=MattilsynetRepository)
    snapshot = MagicMock()
    snapshot.id = uuid4()
    repo.save_snapshot.return_value = snapshot
    repo.save_updates.return_value = 0
    repo.get_known_urls.return_value = set()
    repo.get_page_hash.return_value = None  # First run
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_event_emitter():
    return AsyncMock(spec=RegulatoryEventEmitter)


# ─── Test 14.1: Full pipeline (mock fetch → real parse → real match → persist) ──

class TestFullPipelineIntegration:
    """Test 14.1: Full pipeline with real parsing and keyword matching."""

    @pytest.mark.asyncio
    async def test_first_run_parses_and_saves(
        self, feed_parser, page_parser, keyword_matcher,
        change_detector, mock_repository, mock_event_emitter,
    ):
        """First run: fetch → real parse → real keyword match → save."""
        mock_client = AsyncMock()
        mock_client.fetch_all_feeds.return_value = {"Nyheter": RSS_FEED_WITH_RELEVANT_ITEM}
        mock_client.fetch_all_pages.return_value = {"Kosttilskudd": PAGE_HTML}

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=feed_parser,
            page_parser=page_parser,
            keyword_matcher=keyword_matcher,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=CONFIG,
        )

        result = await pipeline.execute()

        assert result.status == "complete"
        assert result.feeds_checked == 1
        assert result.pages_checked == 1
        # RSS had 2 items parsed by real parser
        assert result.total_updates >= 1
        mock_repository.save_snapshot.assert_awaited_once()
        mock_repository.commit.assert_awaited_once()
        # First page run saves baseline hash
        mock_repository.save_page_hash.assert_awaited_once()


# ─── Test 14.2: Keyword matching (real parse → real match → severity) ────────

class TestKeywordMatchingIntegration:
    """Test 14.2: Real feed parsing → real Norwegian keyword matching."""

    @pytest.mark.asyncio
    async def test_relevant_items_matched_and_scored(
        self, feed_parser, page_parser, keyword_matcher,
        change_detector, mock_repository, mock_event_emitter,
    ):
        """Items containing tier-1 keywords are marked relevant with correct severity."""
        mock_client = AsyncMock()
        mock_client.fetch_all_feeds.return_value = {"Nyheter": RSS_FEED_WITH_RELEVANT_ITEM}
        mock_client.fetch_all_pages.return_value = {}  # No pages

        config = MattilsynetMonitorConfig(
            feeds=(FeedConfig(name="Nyheter", url="https://mattilsynet.no/nyheter/rss"),),
            keywords_tier_1=("kosttilskudd", "helsep\u00e5stander"),
            keywords_tier_2=("dyrevelferd",),
            request_delay_seconds=0,
        )

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=feed_parser,
            page_parser=page_parser,
            keyword_matcher=NorwegianKeywordMatcher(config),
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=config,
        )

        result = await pipeline.execute()

        assert result.status == "complete"
        assert result.relevant_updates >= 1
        # The "kosttilskudd" item should match tier 1
        # The "dyrevelferd" item should match tier 2
        # Both are relevant
        assert result.total_updates == 2


# ─── Test 14.3: Enforcement detection (real parse → enforcement severity) ────

class TestEnforcementDetectionIntegration:
    """Test 14.3: Enforcement keyword matching through full pipeline."""

    @pytest.mark.asyncio
    async def test_enforcement_item_emits_critical_event(
        self, feed_parser, page_parser, change_detector,
        mock_repository, mock_event_emitter,
    ):
        """Feed item with enforcement + tier-1 keyword emits CRITICAL event."""
        mock_client = AsyncMock()
        mock_client.fetch_all_feeds.return_value = {"Varsler": ENFORCEMENT_FEED}
        mock_client.fetch_all_pages.return_value = {}

        config = MattilsynetMonitorConfig(
            feeds=(FeedConfig(name="Varsler", url="https://mattilsynet.no/varsler/rss"),),
            keywords_tier_1=("kosttilskudd", "tilbakekalling"),
            enforcement_keywords=("tilbakekalling", "vedtak"),
            request_delay_seconds=0,
        )

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=feed_parser,
            page_parser=page_parser,
            keyword_matcher=NorwegianKeywordMatcher(config),
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=config,
        )

        result = await pipeline.execute()

        assert result.status == "complete"
        assert result.relevant_updates >= 1
        # Enforcement + tier 1 = CRITICAL → should emit event
        assert mock_event_emitter.emit.await_count >= 1


# ─── Test 14.4: Page change detection (real hash comparison) ─────────────────

class TestPageChangeDetectionIntegration:
    """Test 14.4: Real page content → real hash comparison → change detected."""

    @pytest.mark.asyncio
    async def test_detects_page_content_change(
        self, feed_parser, page_parser, keyword_matcher,
        change_detector, mock_repository, mock_event_emitter,
    ):
        """Second run detects page content change via hash comparison."""
        # Simulate stored hash from first run (hash of PAGE_HTML content)
        first_content = page_parser.extract_main_content(PAGE_HTML)
        first_result = change_detector.check_page(
            url="https://mattilsynet.no/mat/kosttilskudd",
            current_content=first_content,
            previous_hash=None,
        )

        # Set up repository to return the stored hash
        stored_hash = MagicMock()
        stored_hash.content_hash = first_result.current_hash
        mock_repository.get_page_hash.return_value = stored_hash

        # Second run with UPDATED page content
        mock_client = AsyncMock()
        mock_client.fetch_all_feeds.return_value = {}
        mock_client.fetch_all_pages.return_value = {"Kosttilskudd": PAGE_HTML_UPDATED}

        config = MattilsynetMonitorConfig(
            monitored_pages=(
                MonitoredPageConfig(name="Kosttilskudd", url="https://mattilsynet.no/mat/kosttilskudd"),
            ),
            keywords_tier_1=("kosttilskudd",),
            request_delay_seconds=0,
        )

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=feed_parser,
            page_parser=page_parser,
            keyword_matcher=NorwegianKeywordMatcher(config),
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=config,
        )

        result = await pipeline.execute()

        assert result.status == "complete"
        assert result.page_changes == 1
        mock_repository.update_page_hash.assert_awaited_once()


# ─── Test 14.5: Graceful degradation on fetch failure ────────────────────────

class TestGracefulDegradationIntegration:
    """Test 14.5: Pipeline returns incomplete when all sources fail."""

    @pytest.mark.asyncio
    async def test_all_sources_fail_returns_incomplete(
        self, feed_parser, page_parser, keyword_matcher,
        change_detector, mock_repository, mock_event_emitter,
    ):
        """All feeds + pages fail to fetch → incomplete, no snapshot saved."""
        mock_client = AsyncMock()
        mock_client.fetch_all_feeds.return_value = {}  # All failed
        mock_client.fetch_all_pages.return_value = {}  # All failed

        pipeline = MattilsynetMonitorPipeline(
            client=mock_client,
            feed_parser=feed_parser,
            page_parser=page_parser,
            keyword_matcher=keyword_matcher,
            change_detector=change_detector,
            repository=mock_repository,
            event_emitter=mock_event_emitter,
            config=CONFIG,
        )

        result = await pipeline.execute()

        assert result.status == "incomplete"
        # No events should be published
        mock_event_emitter.emit.assert_not_called()
        # No snapshot should be saved on incomplete
        mock_repository.save_snapshot.assert_not_awaited()
        mock_repository.commit.assert_not_awaited()
