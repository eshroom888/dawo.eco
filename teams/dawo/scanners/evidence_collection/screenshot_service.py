"""Screenshot Service (Story 6-8, Task 5).

Protocol + Playwright implementation for capturing webpage screenshots.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from teams.dawo.scanners.evidence_collection.config import EvidenceCollectionConfig
from teams.dawo.scanners.evidence_collection.schemas import CaptureResult

logger = logging.getLogger(__name__)

# Instagram shortcode extraction pattern
INSTAGRAM_POST_PATTERN = re.compile(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)")

# Timestamp banner JavaScript injection
TIMESTAMP_BANNER_JS = """(ts) => {
    const banner = document.createElement('div');
    banner.style.cssText = 'position:fixed; top:0; left:0; right:0; background:rgba(0,0,0,0.88); color:#fff; font-family:monospace; font-size:13px; padding:8px 14px; z-index:2147483647;';
    banner.textContent = 'EVIDENCE CAPTURE: ' + ts + ' | URL: ' + window.location.href;
    document.body.prepend(banner);
}"""


@runtime_checkable
class ScreenshotServiceProtocol(Protocol):
    """Protocol for screenshot capture services.

    Implementations must support async capture and cleanup.
    """

    async def capture(
        self,
        url: str,
        *,
        full_page: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 900,
    ) -> CaptureResult:
        """Capture a screenshot of the given URL.

        Args:
            url: URL to capture.
            full_page: Whether to capture full scrollable page.
            viewport_width: Viewport width in pixels.
            viewport_height: Viewport height in pixels.

        Returns:
            CaptureResult with screenshot bytes and metadata.
        """
        ...

    async def close(self) -> None:
        """Release browser resources."""
        ...


class PlaywrightScreenshotService:
    """Screenshot service using Playwright Chromium.

    Manages a single browser instance with semaphore-bounded
    concurrent page captures.

    Args:
        config: Evidence collection configuration.
    """

    def __init__(self, config: EvidenceCollectionConfig) -> None:
        self._config = config
        self._browser = None
        self._playwright = None
        self._semaphore = None

    async def _ensure_browser(self) -> None:
        """Lazy-initialize browser on first capture."""
        if self._browser is None:
            import asyncio
            from playwright.async_api import async_playwright

            self._semaphore = asyncio.Semaphore(self._config.max_concurrent_captures)
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=self._config.chromium_args,
            )
            logger.info("Playwright browser launched")

    async def capture(
        self,
        url: str,
        *,
        full_page: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 900,
    ) -> CaptureResult:
        """Capture screenshot of URL using Playwright.

        Args:
            url: URL to navigate to and capture.
            full_page: Whether to capture full page or viewport only.
            viewport_width: Browser viewport width.
            viewport_height: Browser viewport height.

        Returns:
            CaptureResult with screenshot bytes and metadata.

        Raises:
            RuntimeError: On timeout or Playwright errors.
        """
        await self._ensure_browser()
        assert self._browser is not None
        assert self._semaphore is not None

        context = None
        page = None
        try:
            async with self._semaphore:
                context = await self._browser.new_context(
                    viewport={"width": viewport_width, "height": viewport_height}
                )
                page = await context.new_page()

                await page.goto(
                    url,
                    wait_until=self._config.wait_until,
                    timeout=self._config.timeout_seconds * 1000,
                )

                captured_at = datetime.now(UTC)

                if self._config.timestamp_banner_enabled:
                    ts_display = captured_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    await page.evaluate(TIMESTAMP_BANNER_JS, ts_display)

                screenshot_bytes = await page.screenshot(
                    full_page=full_page,
                    type=self._config.screenshot_format,
                )

                page_title = await page.title()

                logger.debug("Captured screenshot: url=%s size=%d", url, len(screenshot_bytes))

                return CaptureResult(
                    screenshot_bytes=screenshot_bytes,
                    url=url,
                    captured_at=captured_at,
                    page_title=page_title,
                    metadata={},
                )
        except TimeoutError as e:
            logger.error("Screenshot timeout for %s: %s", url, e)
            raise RuntimeError(f"Screenshot timeout for {url}") from e
        except Exception as e:
            logger.error("Screenshot error for %s: %s", url, e)
            raise RuntimeError(f"Screenshot capture failed for {url}: {e}") from e
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    logger.debug("Error closing context for %s", url)

    async def close(self) -> None:
        """Close browser and Playwright instance."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
            logger.info("Playwright browser closed")
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None


def _build_instagram_embed_url(source_url: str, template: str) -> str:
    """Build Instagram embed URL from a post/reel URL.

    Extracts the shortcode from Instagram post or reel URLs and
    formats it into the embed template.

    Args:
        source_url: Original Instagram URL.
        template: Embed URL template with {shortcode} placeholder.

    Returns:
        Embed URL if Instagram, original URL otherwise.
    """
    match = INSTAGRAM_POST_PATTERN.search(source_url)
    if match:
        shortcode = match.group(1)
        return template.format(shortcode=shortcode)
    return source_url


__all__ = [
    "PlaywrightScreenshotService",
    "ScreenshotServiceProtocol",
]
