"""Mattilsynet monitor pipeline orchestrator.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
Task 10: Pipeline that coordinates all monitoring stages.
"""

import logging
import time
from datetime import datetime, UTC, timedelta

from core.regulatory.events import (
    RegulatoryEvent,
    RegulatoryEventEmitter,
    RegulatoryEventType,
)
from core.regulatory.models import MattilsynetSourceType, MattilsynetCategory
from teams.dawo.scanners.mattilsynet.change_detector import PageChangeDetector
from teams.dawo.scanners.mattilsynet.client import MattilsynetClient, MattilsynetClientError
from teams.dawo.scanners.mattilsynet.config import MattilsynetMonitorConfig
from teams.dawo.scanners.mattilsynet.feed_parser import MattilsynetFeedParser, FeedParseError
from teams.dawo.scanners.mattilsynet.keyword_matcher import NorwegianKeywordMatcher
from teams.dawo.scanners.mattilsynet.page_parser import MattilsynetPageParser, PageParseError
from teams.dawo.scanners.mattilsynet.repository import MattilsynetRepository
from teams.dawo.scanners.mattilsynet.schemas import (
    MattilsynetMonitorResult,
    RegulatoryUpdateRecord,
)

logger = logging.getLogger(__name__)

# Severity mapping: (relevance_tier, is_enforcement) -> severity
SEVERITY_MAP = {
    (1, True): "critical",
    (1, False): "high",
    (2, True): "high",
    (2, False): "medium",
}


class MattilsynetMonitorPipeline:
    """Orchestrates the Mattilsynet regulatory monitoring pipeline.

    Pipeline stages:
        1. Fetch all RSS feeds
        2. Fetch all monitored pages
        3. Parse feed items
        4. Extract and hash page content
        5. Check page changes vs previous hashes
        6. Load known URLs for deduplication
        7. Filter new items only
        8. Match keywords
        9. Save snapshot + updates
        10. Update page hashes
        11. Commit transaction
        12. Publish events for HIGH/CRITICAL updates
    """

    def __init__(
        self,
        client: MattilsynetClient,
        feed_parser: MattilsynetFeedParser,
        page_parser: MattilsynetPageParser,
        keyword_matcher: NorwegianKeywordMatcher,
        change_detector: PageChangeDetector,
        repository: MattilsynetRepository,
        event_emitter: RegulatoryEventEmitter,
        config: MattilsynetMonitorConfig,
    ) -> None:
        """Initialize pipeline with all dependencies.

        Args:
            client: HTTP client for fetching
            feed_parser: RSS/Atom feed parser
            page_parser: HTML page parser
            keyword_matcher: Norwegian keyword matcher
            change_detector: Page change detector
            repository: Data repository
            event_emitter: Event emitter for notifications
            config: Monitor configuration
        """
        self._client = client
        self._feed_parser = feed_parser
        self._page_parser = page_parser
        self._keyword_matcher = keyword_matcher
        self._change_detector = change_detector
        self._repository = repository
        self._event_emitter = event_emitter
        self._config = config

    async def execute(self) -> MattilsynetMonitorResult:
        """Execute the full monitoring pipeline.

        Returns:
            MattilsynetMonitorResult with execution summary
        """
        start_time = time.monotonic()
        errors: list[str] = []
        all_updates: list[RegulatoryUpdateRecord] = []
        page_changes_count = 0
        feeds_checked = 0
        pages_checked = 0

        # Phase 1: Fetch and parse RSS feeds
        feed_updates, feed_errors, feeds_checked = await self._process_feeds()
        all_updates.extend(feed_updates)
        errors.extend(feed_errors)

        # Phase 2: Fetch, parse, and check pages
        page_updates, page_errors, pages_checked, page_changes_count = (
            await self._process_pages()
        )
        all_updates.extend(page_updates)
        errors.extend(page_errors)

        # Phase 3: Deduplication
        dedup_lookback = datetime.now(UTC) - timedelta(days=30)
        known_urls = await self._repository.get_known_urls(since=dedup_lookback)
        new_updates = [u for u in all_updates if u.url not in known_urls]

        logger.info(
            "Deduplication: %d total -> %d new (removed %d known)",
            len(all_updates),
            len(new_updates),
            len(all_updates) - len(new_updates),
        )

        # Phase 4: Keyword matching on new items
        for update in new_updates:
            text = f"{update.title} {update.content_summary}"
            match_result = self._keyword_matcher.match(text)
            update.is_relevant = match_result.is_relevant
            update.relevance_tier = match_result.relevance_tier
            update.keywords_matched = list(match_result.matched_keywords)
            update.is_enforcement = match_result.is_enforcement
            if match_result.is_relevant:
                severity_key = (match_result.relevance_tier, match_result.is_enforcement)
                update.severity = SEVERITY_MAP.get(severity_key, "low")
            if match_result.is_enforcement:
                update.category = MattilsynetCategory.ENFORCEMENT.value

        relevant_updates = [u for u in new_updates if u.is_relevant]

        # Determine status before persisting
        status = self._determine_status(
            feeds_checked, pages_checked, errors
        )

        # Phase 5: Persist (skip on incomplete — no useful data)
        scan_duration = time.monotonic() - start_time

        if status != "incomplete":
            snapshot = await self._repository.save_snapshot(
                total_updates=len(new_updates),
                relevant_updates=len(relevant_updates),
                feeds_checked=feeds_checked,
                pages_checked=pages_checked,
                scan_duration=scan_duration,
            )

            saved_count = await self._repository.save_updates(new_updates, snapshot.id)
            await self._repository.commit()

            logger.info(
                "Saved snapshot %s with %d updates (%d relevant)",
                snapshot.id,
                saved_count,
                len(relevant_updates),
            )

            # Phase 6: Publish events for HIGH/CRITICAL updates
            for update in relevant_updates:
                if update.severity in ("critical", "high"):
                    await self._publish_event(update)

        return MattilsynetMonitorResult(
            status=status,
            total_updates=len(new_updates),
            relevant_updates=len(relevant_updates),
            page_changes=page_changes_count,
            feeds_checked=feeds_checked,
            pages_checked=pages_checked,
            errors=errors,
            scan_duration_seconds=time.monotonic() - start_time,
        )

    async def _process_feeds(
        self,
    ) -> tuple[list[RegulatoryUpdateRecord], list[str], int]:
        """Fetch and parse all configured feeds.

        Returns:
            Tuple of (updates, errors, feeds_checked)
        """
        updates: list[RegulatoryUpdateRecord] = []
        errors: list[str] = []
        feeds = list(self._config.feeds)

        if not feeds:
            logger.info("No feeds configured, skipping feed processing")
            return updates, errors, 0

        feed_data = await self._client.fetch_all_feeds(feeds)
        feeds_checked = len(feed_data)

        for feed_name, data in feed_data.items():
            try:
                items = self._feed_parser.parse_feed(data, feed_name)
                for item in items:
                    source_type = MattilsynetSourceType.RSS_NEWS.value
                    # Check if this is a warnings/varsler feed
                    for feed_cfg in feeds:
                        if feed_cfg.name == feed_name and "varsler" in feed_cfg.url.lower():
                            source_type = MattilsynetSourceType.RSS_WARNING.value
                            break

                    updates.append(
                        RegulatoryUpdateRecord(
                            title=item.title,
                            url=item.url,
                            content_summary=item.summary[:2000] if item.summary else "",
                            published_at=item.published_at,
                            source_type=source_type,
                            category=MattilsynetCategory.NEWS.value,
                            raw_content_hash=item.content_hash,
                        )
                    )
            except FeedParseError as e:
                error_msg = f"Feed parse error for '{feed_name}': {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        return updates, errors, feeds_checked

    async def _process_pages(
        self,
    ) -> tuple[list[RegulatoryUpdateRecord], list[str], int, int]:
        """Fetch, parse, and check all monitored pages.

        Returns:
            Tuple of (updates, errors, pages_checked, page_changes)
        """
        updates: list[RegulatoryUpdateRecord] = []
        errors: list[str] = []
        pages = list(self._config.monitored_pages)
        page_changes = 0

        if not pages:
            logger.info("No pages configured, skipping page processing")
            return updates, errors, 0, 0

        page_data = await self._client.fetch_all_pages(pages)
        pages_checked = len(page_data)

        for page_cfg in pages:
            if page_cfg.name not in page_data:
                continue

            data = page_data[page_cfg.name]
            try:
                content = self._page_parser.extract_main_content(data)
            except PageParseError as e:
                error_msg = f"Page parse error for '{page_cfg.name}': {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue

            # Check against stored hash
            stored = await self._repository.get_page_hash(page_cfg.url)
            previous_hash = stored.content_hash if stored else None

            change_result = self._change_detector.check_page(
                url=page_cfg.url,
                current_content=content,
                previous_hash=previous_hash,
            )

            # Save or update page hash
            if stored is None:
                await self._repository.save_page_hash(
                    url=page_cfg.url,
                    page_name=page_cfg.name,
                    content_hash=change_result.current_hash,
                )
            else:
                await self._repository.update_page_hash(
                    url=page_cfg.url,
                    content_hash=change_result.current_hash,
                    changed=change_result.changed,
                )

            if change_result.changed:
                page_changes += 1
                try:
                    article = self._page_parser.parse_article(data, page_cfg.url)
                    updates.append(
                        RegulatoryUpdateRecord(
                            title=article.title or page_cfg.name,
                            url=page_cfg.url,
                            content_summary=article.body_text[:2000],
                            published_at=article.published_at,
                            source_type=MattilsynetSourceType.PAGE_CHANGE.value,
                            category=MattilsynetCategory.REGULATION.value,
                            raw_content_hash=change_result.current_hash,
                        )
                    )
                except PageParseError as e:
                    error_msg = f"Article parse error for '{page_cfg.name}': {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        return updates, errors, pages_checked, page_changes

    async def _publish_event(self, update: RegulatoryUpdateRecord) -> None:
        """Publish a regulatory event for a high-severity update."""
        if update.source_type == MattilsynetSourceType.PAGE_CHANGE.value:
            event_type = RegulatoryEventType.MATTILSYNET_PAGE_CHANGED
        elif update.is_enforcement:
            event_type = RegulatoryEventType.MATTILSYNET_ENFORCEMENT_ACTION
        else:
            event_type = RegulatoryEventType.MATTILSYNET_REGULATORY_UPDATE

        event = RegulatoryEvent(
            event_type=event_type,
            claim_id="",
            substance="",
            old_status="",
            new_status="",
            severity=update.severity,
            data={
                "title": update.title,
                "url": update.url,
                "category": update.category,
                "keywords_matched": update.keywords_matched,
                "content_summary": update.content_summary[:500],
            },
        )
        await self._event_emitter.emit(event)
        logger.info(
            "Published %s event for '%s' (severity=%s)",
            event_type.value,
            update.title,
            update.severity,
        )

    def _determine_status(
        self,
        feeds_checked: int,
        pages_checked: int,
        errors: list[str],
    ) -> str:
        """Determine pipeline execution status.

        Returns:
            "complete", "partial", or "incomplete"
        """
        total_expected = len(self._config.feeds) + len(self._config.monitored_pages)
        total_checked = feeds_checked + pages_checked

        if total_expected > 0 and total_checked == 0:
            return "incomplete"
        if total_checked < total_expected:
            return "partial"
        return "complete"


__all__ = [
    "MattilsynetMonitorPipeline",
]
