"""Tests for ScreenshotService (Story 6-8, Task 5).

All tests mock Playwright entirely — no browser launch.
"""

from teams.dawo.scanners.evidence_collection.screenshot_service import (
    ScreenshotServiceProtocol,
    _build_instagram_embed_url,
)


class TestBuildInstagramEmbedUrl:
    """Tests for _build_instagram_embed_url helper."""

    TEMPLATE = "https://www.instagram.com/p/{shortcode}/embed/"

    def test_extracts_shortcode_from_post_url(self) -> None:
        """Extracts shortcode from /p/ABC123/ URL."""
        url = "https://www.instagram.com/p/ABC123/"
        result = _build_instagram_embed_url(url, self.TEMPLATE)
        assert result == "https://www.instagram.com/p/ABC123/embed/"

    def test_extracts_shortcode_from_reel_url(self) -> None:
        """Extracts shortcode from /reel/XYZ789/ URL."""
        url = "https://www.instagram.com/reel/XYZ789/"
        result = _build_instagram_embed_url(url, self.TEMPLATE)
        assert result == "https://www.instagram.com/p/XYZ789/embed/"

    def test_passes_through_non_instagram_url(self) -> None:
        """Non-Instagram URLs pass through unchanged."""
        url = "https://competitor.com/products/mushroom"
        result = _build_instagram_embed_url(url, self.TEMPLATE)
        assert result == url

    def test_handles_complex_shortcode(self) -> None:
        """Handles shortcodes with underscores and dashes."""
        url = "https://www.instagram.com/p/Ab_C-123def/"
        result = _build_instagram_embed_url(url, self.TEMPLATE)
        assert result == "https://www.instagram.com/p/Ab_C-123def/embed/"


class TestScreenshotServiceProtocol:
    """Tests for ScreenshotServiceProtocol runtime_checkable."""

    def test_protocol_is_runtime_checkable(self, mock_screenshot_service) -> None:
        """Mock implementing protocol passes isinstance check."""
        assert isinstance(mock_screenshot_service, ScreenshotServiceProtocol)


class TestScreenshotServiceProtocolContract:
    """Tests for ScreenshotServiceProtocol contract behavior.

    These validate the protocol contract, not PlaywrightScreenshotService internals.
    PlaywrightScreenshotService requires a real Chromium browser and is covered
    by manual/E2E testing.
    """

    async def test_capture_returns_capture_result(
        self, mock_screenshot_service, sample_capture_result
    ) -> None:
        """capture() returns CaptureResult with bytes, url, timestamp, page_title."""
        mock_screenshot_service.capture.return_value = sample_capture_result
        result = await mock_screenshot_service.capture("https://example.com")
        assert result.screenshot_bytes == sample_capture_result.screenshot_bytes
        assert result.url == sample_capture_result.url
        assert result.captured_at == sample_capture_result.captured_at
        assert result.page_title == "Instagram Post"

    async def test_capture_applies_viewport_dimensions(
        self, mock_screenshot_service, sample_capture_result
    ) -> None:
        """capture() passes viewport dimensions."""
        mock_screenshot_service.capture.return_value = sample_capture_result
        await mock_screenshot_service.capture(
            "https://example.com",
            viewport_width=1920,
            viewport_height=1080,
        )
        mock_screenshot_service.capture.assert_called_with(
            "https://example.com",
            viewport_width=1920,
            viewport_height=1080,
        )

    async def test_capture_timeout_raises_runtime_error(
        self, mock_screenshot_service
    ) -> None:
        """capture() raises RuntimeError on timeout."""
        mock_screenshot_service.capture.side_effect = RuntimeError("timeout")
        import pytest

        with pytest.raises(RuntimeError, match="timeout"):
            await mock_screenshot_service.capture("https://example.com")

    async def test_close_calls_browser_close(
        self, mock_screenshot_service
    ) -> None:
        """close() is called without error."""
        await mock_screenshot_service.close()
        mock_screenshot_service.close.assert_called_once()
