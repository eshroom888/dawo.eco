"""Competitor Scan Pipeline Orchestrator.

Epic 6, Story 6-5, Task 8: Orchestrates the full competitor content
scanning flow: Instagram + website → parse → dedup → store → events.
"""

import asyncio
import logging
from datetime import datetime, UTC

from core.regulatory.events import RegulatoryEvent, RegulatoryEventType
from teams.dawo.scanners.competitor.config import CompetitorConfig, CompetitorScannerConfig
from teams.dawo.scanners.competitor.schemas import (
    CompetitorScanResult,
    CompetitorScanStatus,
    ParsedContent,
)

logger = logging.getLogger(__name__)


class CompetitorScanPipeline:
    """Pipeline orchestrator for competitor content scanning.

    For each competitor:
    1. Create snapshot record
    2. Fetch Instagram posts (if enabled)
    3. Scrape website pages (if enabled)
    4. Run health language detection
    5. Check duplicates against DB
    6. Save new content
    7. Update snapshot stats
    8. Emit events for health language content

    Args:
        instagram_client: InstagramClient for fetching posts
        website_client: WebsiteScraperClient for scraping pages
        parser: CompetitorContentParser for content extraction
        duplicate_checker: CompetitorDuplicateChecker for dedup
        repository: CompetitorRepository for persistence
        event_emitter: RegulatoryEventEmitter for downstream notifications
        config: CompetitorScannerConfig with competitor list and settings
    """

    def __init__(
        self,
        instagram_client: object,
        website_client: object,
        parser: object,
        duplicate_checker: object,
        repository: object,
        event_emitter: object,
        config: CompetitorScannerConfig,
    ) -> None:
        self._instagram = instagram_client
        self._website = website_client
        self._parser = parser
        self._dup_checker = duplicate_checker
        self._repo = repository
        self._events = event_emitter
        self._config = config

    async def execute(self) -> CompetitorScanResult:
        """Execute the full competitor scan pipeline.

        Returns:
            CompetitorScanResult with aggregate statistics
        """
        total_content = 0
        total_saved = 0
        total_duplicates = 0
        total_health = 0
        errors: list[str] = []
        successful_competitors = 0

        for competitor in self._config.competitors:
            try:
                stats = await self._scan_competitor(competitor)
                total_content += stats["content_found"]
                total_saved += stats["saved"]
                total_duplicates += stats["duplicates"]
                total_health += stats["health_count"]
                successful_competitors += 1
            except Exception as e:
                error_msg = f"Failed to scan {competitor.name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

                # Update snapshot status to failed
                try:
                    snapshot = await self._repo.create_snapshot(
                        competitor.name, "combined"
                    )
                    await self._repo.update_snapshot_stats(
                        snapshot.id, total=0, health_count=0, status="failed"
                    )
                    await self._repo.commit()
                except Exception as repo_err:
                    logger.debug("Failed to record error snapshot: %s", repo_err)

            # Rate limit between competitors
            if self._config.request_delay_seconds > 0:
                await asyncio.sleep(self._config.request_delay_seconds)

        # Determine overall status
        total_competitors = len(self._config.competitors)
        if successful_competitors == total_competitors:
            status = CompetitorScanStatus.COMPLETE
        elif successful_competitors > 0:
            status = CompetitorScanStatus.PARTIAL
        else:
            status = CompetitorScanStatus.FAILED

        result = CompetitorScanResult(
            status=status,
            competitors_scanned=total_competitors,
            total_content_found=total_content,
            new_content_saved=total_saved,
            duplicates_skipped=total_duplicates,
            health_language_detected=total_health,
            errors=errors,
        )

        logger.info(
            "Competitor scan complete: %s — scanned=%d, found=%d, saved=%d, "
            "dupes=%d, health=%d, errors=%d",
            status.value,
            total_competitors,
            total_content,
            total_saved,
            total_duplicates,
            total_health,
            len(errors),
        )

        return result

    async def _scan_competitor(self, competitor: CompetitorConfig) -> dict:
        """Scan a single competitor across all sources.

        Args:
            competitor: Competitor to scan

        Returns:
            Dict with content_found, saved, duplicates, health_count
        """
        all_parsed: list[ParsedContent] = []

        # Stage 1: Create snapshot
        snapshot = await self._repo.create_snapshot(competitor.name, "combined")

        # Stage 2a: Instagram posts
        if (
            self._config.instagram.enabled
            and competitor.instagram_username
        ):
            ig_parsed = await self._fetch_instagram(competitor)
            all_parsed.extend(ig_parsed)
            logger.info(
                "Instagram: %d posts from %s",
                len(ig_parsed), competitor.instagram_username,
            )

        # Stage 2b: Website pages
        if (
            self._config.websites.enabled
            and competitor.website_urls
        ):
            web_parsed = await self._fetch_websites(competitor)
            all_parsed.extend(web_parsed)
            logger.info(
                "Website: %d pages from %s",
                len(web_parsed), competitor.name,
            )

        content_found = len(all_parsed)

        # Stage 3: Health language detection already done in parser
        health_count = sum(1 for p in all_parsed if p.has_health_language)

        # Stage 4: Check duplicates
        new_items = await self._dup_checker.check_duplicates(all_parsed)
        duplicates = content_found - len(new_items)

        # Stage 5: Save new content
        saved = 0
        if new_items:
            saved = await self._repo.save_content_batch(new_items, snapshot.id)

        # Stage 6: Update snapshot stats
        await self._repo.update_snapshot_stats(
            snapshot.id,
            total=content_found,
            health_count=health_count,
            status="completed",
        )
        await self._repo.commit()

        # Stage 7: Emit events for health language content
        health_in_new = [item for item in new_items if item.has_health_language]
        for item in health_in_new:
            await self._emit_health_event(item)

        return {
            "content_found": content_found,
            "saved": saved,
            "duplicates": duplicates,
            "health_count": health_count,
        }

    async def _fetch_instagram(
        self, competitor: CompetitorConfig
    ) -> list[ParsedContent]:
        """Fetch and parse Instagram posts for a competitor.

        Args:
            competitor: Competitor with instagram_username

        Returns:
            List of parsed Instagram content
        """
        posts = await self._instagram.get_user_media(
            username=competitor.instagram_username,
            limit=self._config.instagram.max_posts_per_competitor,
        )

        parsed: list[ParsedContent] = []
        for post in posts:
            content = self._parser.parse_instagram_post(post, competitor)
            parsed.append(content)

        return parsed

    async def _fetch_websites(
        self, competitor: CompetitorConfig
    ) -> list[ParsedContent]:
        """Fetch and parse website pages for a competitor.

        Args:
            competitor: Competitor with website_urls

        Returns:
            List of parsed website content
        """
        pages = await self._website.scrape_competitor_pages(competitor)

        parsed: list[ParsedContent] = []
        for page in pages:
            content = self._parser.parse_website_page(page, competitor)
            parsed.append(content)

        return parsed

    async def _emit_health_event(self, item: ParsedContent) -> None:
        """Emit event for content with health language detected.

        Args:
            item: ParsedContent with health language
        """
        event = RegulatoryEvent(
            event_type=RegulatoryEventType.COMPETITOR_HEALTH_LANGUAGE_DETECTED,
            claim_id="",
            substance="",
            severity="medium",
            data={
                "competitor_name": item.competitor_name,
                "source_type": item.source_type,
                "source_url": item.source_url,
                "keywords_matched": item.health_keywords_matched,
                "content_preview": item.content_text[:200],
            },
        )
        await self._events.emit(event)


__all__ = [
    "CompetitorScanPipeline",
]
