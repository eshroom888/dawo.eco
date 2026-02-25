"""Shared fixtures for Mattilsynet scanner tests.

Epic 6, Story 6-3: Mattilsynet Regulatory Monitor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.scanners.mattilsynet.config import (
    FeedConfig,
    MattilsynetMonitorConfig,
    MonitoredPageConfig,
)


@pytest.fixture
def sample_rss_feed() -> bytes:
    """Sample RSS 2.0 feed for testing."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
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
        <title>Generell nyhet</title>
        <link>https://www.mattilsynet.no/nyheter/generell</link>
        <pubDate>Wed, 12 Feb 2026 10:00:00 +0100</pubDate>
        <description>En generell nyhet uten relevante emner.</description>
      </item>
    </channel>
    </rss>"""


@pytest.fixture
def sample_atom_feed() -> bytes:
    """Sample Atom feed for testing."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Mattilsynet Varsler</title>
      <entry>
        <title>Tilbakekalling: Soppekstrakt med ulovlige helsep\xc3\xa5stander</title>
        <link href="https://www.mattilsynet.no/varsler/tilbakekalling-soppekstrakt"/>
        <updated>2026-02-12T10:00:00+01:00</updated>
        <summary>Mattilsynet har fattet vedtak om tilbakekalling av et kosttilskudd.</summary>
      </entry>
    </feed>"""


@pytest.fixture
def sample_page_html() -> bytes:
    """Sample Mattilsynet article page HTML."""
    return b"""<html><body>
    <nav>Navigation content to strip</nav>
    <main class="content-area">
      <h1>Endringer i kosttilskuddsforskriften</h1>
      <time datetime="2026-02-10">10. februar 2026</time>
      <article class="article-body">
        <p>Mattilsynet informerer om endringer i regelverket for kosttilskudd.</p>
        <p>Nye krav til merking av helsep\xc3\xa5stander trer i kraft 1. mars 2026.</p>
      </article>
    </main>
    <footer>Footer content to strip</footer>
    </body></html>"""


@pytest.fixture
def sample_page_html_fallback() -> bytes:
    """HTML page with only fallback selectors matching."""
    return b"""<html><body>
    <nav>Navigation</nav>
    <main>
      <h1>Fallback Title</h1>
      <p>Content found via main fallback selector.</p>
    </main>
    <footer>Footer</footer>
    </body></html>"""


@pytest.fixture
def sample_page_html_no_selectors() -> bytes:
    """HTML page with no matching content selectors."""
    return b"""<html><body>
    <nav>Navigation only</nav>
    <footer>Footer only</footer>
    </body></html>"""


@pytest.fixture
def malformed_feed() -> bytes:
    """Malformed feed data that cannot be parsed."""
    return b"This is not valid RSS or Atom content at all."


@pytest.fixture
def empty_feed() -> bytes:
    """Valid RSS feed with zero items."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
    <channel>
      <title>Empty Feed</title>
    </channel>
    </rss>"""


@pytest.fixture
def keyword_config() -> MattilsynetMonitorConfig:
    """Config with test keywords."""
    return MattilsynetMonitorConfig(
        feeds=(FeedConfig(name="test", url="https://example.com/rss", is_primary=True),),
        keywords_tier_1=("kosttilskudd", "helsep\u00e5stander", "tilbakekalling"),
        keywords_tier_2=("sopp", "funksjonssopp", "adaptogener"),
        enforcement_keywords=("tilbakekalling", "advarsel", "importnekt", "vedtak"),
    )


@pytest.fixture
def minimal_config() -> MattilsynetMonitorConfig:
    """Minimal valid config for testing."""
    return MattilsynetMonitorConfig(
        feeds=(FeedConfig(name="test", url="https://example.com/rss"),),
        keywords_tier_1=("kosttilskudd",),
    )


@pytest.fixture
def pages_only_config() -> MattilsynetMonitorConfig:
    """Config with pages only (no feeds)."""
    return MattilsynetMonitorConfig(
        monitored_pages=(
            MonitoredPageConfig(name="Test Page", url="https://example.com/page"),
        ),
        keywords_tier_1=("kosttilskudd",),
    )


@pytest.fixture
def full_config() -> MattilsynetMonitorConfig:
    """Full config with feeds and pages."""
    return MattilsynetMonitorConfig(
        feeds=(
            FeedConfig(name="Nyheter", url="https://www.mattilsynet.no/nyheter/rss", is_primary=True),
            FeedConfig(name="Varsler", url="https://www.mattilsynet.no/varsler/rss", is_primary=True),
        ),
        monitored_pages=(
            MonitoredPageConfig(name="Kosttilskudd", url="https://www.mattilsynet.no/mat/kosttilskudd"),
            MonitoredPageConfig(name="Helsep\u00e5stander", url="https://www.mattilsynet.no/mat/merking-av-mat/helsepastander"),
        ),
        keywords_tier_1=("kosttilskudd", "helsep\u00e5stander", "tilbakekalling"),
        keywords_tier_2=("sopp", "funksjonssopp", "adaptogener"),
        enforcement_keywords=("tilbakekalling", "advarsel", "importnekt", "vedtak"),
    )


@pytest.fixture
def mock_retry_result():
    """Create a mock retry result."""
    result = MagicMock()
    result.success = True
    result.response = b"<data>"
    result.last_error = None
    return result


@pytest.fixture
def mock_retry_middleware(mock_retry_result):
    """Create a mock retry middleware."""
    retry = AsyncMock()
    retry.execute_with_retry.return_value = mock_retry_result
    return retry
