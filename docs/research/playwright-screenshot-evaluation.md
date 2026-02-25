# Playwright Screenshot Evaluation

**Date:** 2026-02-12
**Purpose:** Epic 6, Story 6-8 - Evidence Collection & Screenshots
**Decision:** Playwright Python (Recommended)

---

## Decision Summary

**Playwright Python is the recommended tool.** No viable alternative matches its async capabilities.

| Criterion | Playwright | Selenium | Pyppeteer |
|-----------|-----------|----------|-----------|
| Async API | Native `async/await` | None (sync only) | Native but **abandoned** |
| Screenshot API | Full page, element, clip, viewport | Viewport only | Full page, element |
| Maintenance | Active (Microsoft) | Active | **Unmaintained since 2022** |
| Python 3.12+ | Tested in CI | Yes | **Uncertain** |

## Key Capabilities

- **Full page, viewport, element, and clip-region screenshots** — all async
- **Instagram posts** via embed URL: `https://www.instagram.com/p/{shortcode}/embed/` (no auth needed)
- **PDF generation** from pages (Chromium only) — bonus for Story 6-10
- **Concurrent pages** via `asyncio.Semaphore` — recommended max 3 concurrent

## Timestamp Overlay (DOM Injection)

```python
await page.evaluate(f"""() => {{
    const banner = document.createElement('div');
    banner.style.cssText = 'position:fixed; top:0; left:0; right:0; background:rgba(0,0,0,0.88); color:#fff; font-family:monospace; padding:8px 14px; z-index:2147483647;';
    banner.textContent = 'EVIDENCE CAPTURE: {ts_display} | URL: ' + window.location.href;
    document.body.prepend(banner);
}}""")
```

## Integrity Hashing

```python
sha256_hash = hashlib.sha256(png_bytes).hexdigest()  # hash BEFORE writing to disk
```

## Architecture Pattern

```python
@runtime_checkable
class ScreenshotService(Protocol):
    async def capture(self, url: str, *, full_page: bool = True, viewport_width: int = 1280, viewport_height: int = 900) -> CaptureResult: ...
    async def close(self) -> None: ...
```

`PlaywrightScreenshotService` manages a single Chromium instance with bounded concurrency.
`MockScreenshotService` returns minimal valid PNG for testing (zero browser deps).

## Resource Requirements
- Chromium binary: ~280 MB (via `playwright install chromium`)
- Per browser: 150-300 MB RAM
- Per page: 50-80 MB RAM
- Screenshot capture: <300ms

## Dependencies
```
playwright>=1.41.0,<2.0.0
```
Post-install: `playwright install chromium`

---

*Alternatives evaluated: Selenium (no async), Pyppeteer (abandoned), html2image (limited), shot-scraper (CLI only)*
