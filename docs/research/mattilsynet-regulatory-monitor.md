# Mattilsynet Regulatory Monitor Research

**Date:** 2026-02-12
**Purpose:** Epic 6, Story 6-3 - Mattilsynet Regulatory Monitor
**Status:** Research complete, ready for implementation planning

---

## 1. Website Structure

### Overview

Mattilsynet (Norwegian Food Safety Authority / Mattilsynet.no) is the Norwegian
governmental body responsible for food safety, animal health, plant health, and
cosmetics. For DAWO.ECO, the relevant regulatory domains are:

- **Dietary supplements (kosttilskudd)** - regulations, approvals, enforcement
- **Health claims (helsepastander)** - EU Regulation 1924/2006 enforcement in Norway
- **Novel foods** - EU Novel Food Catalogue implementation in Norwegian context
- **Enforcement actions** - warnings, recalls, import bans

### Key URL Sections

| Section | URL Pattern | Relevance |
|---------|-------------|-----------|
| Mat (Food) | `https://www.mattilsynet.no/mat` | Parent section for all food regulations |
| Kosttilskudd | `https://www.mattilsynet.no/mat/kosttilskudd` | **PRIMARY** - Dietary supplement rules |
| Helsepastander | `https://www.mattilsynet.no/mat/merking-av-mat/helsepastander` | **PRIMARY** - Health claims on food |
| Merking av mat | `https://www.mattilsynet.no/mat/merking-av-mat` | Food labeling requirements |
| Import | `https://www.mattilsynet.no/mat/import-av-mat` | Import requirements for supplements |
| Nyheter (News) | `https://www.mattilsynet.no/nyheter` | News and press releases |
| Tilbakekallinger | `https://www.mattilsynet.no/varsler` | **PRIMARY** - Recalls and warnings |
| Regelverk | `https://www.mattilsynet.no/regelverk` | Legislation and regulation references |

### Site Architecture Notes

- The site was redesigned circa 2023-2024 and migrated to a modern CMS
- Content is primarily in Norwegian (Bokmal/Nynorsk)
- Some pages have English summaries under `/en/` prefix
- The site uses structured URLs with clean paths (no query params for navigation)
- Content types include: articles, news, guides, regulation summaries, warnings

---

## 2. RSS / Atom Feeds

### Feed Availability

Mattilsynet provides RSS feeds for news content. Based on Norwegian government
digital practices and the site's architecture:

| Feed | URL (Verify at Implementation) | Content |
|------|------|---------|
| Nyheter (News) | `https://www.mattilsynet.no/nyheter/rss` or `https://www.mattilsynet.no/rss` | General news feed |
| Varsler (Warnings) | `https://www.mattilsynet.no/varsler/rss` | Recalls, warnings |

### Important Caveats

- **Feed URLs must be verified** at implementation time by checking:
  1. `robots.txt` for sitemap references
  2. Page source for `<link rel="alternate" type="application/rss+xml">` tags
  3. `/rss`, `/feed`, or `/atom` path variations
- Norwegian government sites sometimes use Atom instead of RSS 2.0
- Feed content may be partial (title + summary, not full article text)
- If no dedicated RSS exists, the sitemap.xml can serve as an index of all pages

### Feed Discovery Strategy

```python
# Implementation: Check multiple potential feed locations
FEED_CANDIDATES = [
    "https://www.mattilsynet.no/rss",
    "https://www.mattilsynet.no/rss.xml",
    "https://www.mattilsynet.no/feed",
    "https://www.mattilsynet.no/nyheter/rss",
    "https://www.mattilsynet.no/varsler/rss",
    "https://www.mattilsynet.no/atom.xml",
]

# Also parse HTML <link> tags from homepage
# <link rel="alternate" type="application/rss+xml" href="..." />
```

---

## 3. API Availability

### Public APIs

Mattilsynet does **not** provide a general-purpose public REST API for content.
However, several structured data access points exist:

| Source | Type | URL | Notes |
|--------|------|-----|-------|
| Smilefjesdata (Inspection results) | Open Data / CSV / API | `https://data.mattilsynet.no/` | Inspection grades for food businesses |
| Tilsynsdata | API | `https://data.mattilsynet.no/api/` | Structured inspection data |
| Lovdata (Legislation) | Separate service | `https://lovdata.no/` | Norwegian law database (not Mattilsynet) |

### Smilefjesdata API Details

- Provides inspection results for food establishments
- Available as open data (JSON/CSV)
- Less relevant for supplement regulation monitoring
- More relevant for enforcement/compliance trend analysis

### No Content API

For news, regulations, and enforcement actions, there is **no public API**.
The implementation must use one of:
1. RSS feeds (if available)
2. HTML scraping with structured selectors
3. Sitemap-based change detection

---

## 4. Norwegian Keywords for Monitoring

### Primary Keywords (Tier 1 - High Priority)

These directly relate to DAWO.ECO's supplement business:

```python
MATTILSYNET_KEYWORDS_TIER_1 = [
    # Dietary supplements
    "kosttilskudd",                    # dietary supplements
    "kosttilskuddsforskriften",        # dietary supplements regulation
    "naeringsstoffer",                 # nutrients (use ae for æ in search)

    # Health claims
    "helsepastander",                  # health claims (use a for å in search)
    "helsepaastand",                   # health claim (singular)
    "ernaeringspaastand",              # nutrition claim
    "EC 1924/2006",                    # EU health claims regulation
    "paastandsforordningen",           # the claims regulation

    # Enforcement
    "tilbakekalling",                  # recall
    "advarsel",                        # warning
    "importnekt",                      # import refusal
    "vedtak",                          # decision/ruling
    "overtredelsesgebyr",              # infringement fine
    "tilsyn",                          # inspection/supervision

    # Novel food
    "ny mat",                          # novel food
    "novel food",                      # also used in Norwegian context
    "ny mat-forordningen",             # novel food regulation
]
```

### Secondary Keywords (Tier 2 - Product-Specific)

```python
MATTILSYNET_KEYWORDS_TIER_2 = [
    # Mushroom products (DAWO core products)
    "sopp",                            # mushrooms
    "soppekstrakt",                    # mushroom extract
    "funksjonssopp",                   # functional mushrooms
    "adaptogener",                     # adaptogens
    "lions mane",                      # lion's mane (used in Norwegian too)
    "chaga",                           # chaga
    "reishi",                          # reishi
    "cordyceps",                       # cordyceps

    # Regulatory bodies
    "EFSA",                            # European Food Safety Authority
    "Mattilsynet",                     # self-reference in content
    "EOS",                             # EEA/EFTA context

    # Compliance terms
    "merking",                         # labeling
    "grenseverdier",                   # threshold values / limits
    "maksimumsgrenser",                # maximum limits
    "godkjent",                        # approved
    "ikke godkjent",                   # not approved
    "EU-harmonisert",                  # EU-harmonized
]
```

### Character Encoding Notes

Norwegian uses special characters that must be handled correctly:

| Character | Unicode | ASCII Fallback | Example |
|-----------|---------|----------------|---------|
| ae (æ) | U+00E6 | ae | næringsstoffer |
| oe (ø) | U+00F8 | oe | kosttilskudd (no ø, but common in other words) |
| aa (å) | U+00E5 | aa | helsepåstander, påstand |

**Implementation requirement**: Search with BOTH the Unicode character and the
ASCII fallback, since URLs and some content may use either form. The site
primarily uses UTF-8 encoded Norwegian.

```python
def normalize_norwegian(text: str) -> str:
    """Normalize Norwegian special characters for matching."""
    replacements = {
        "æ": "ae", "Æ": "AE",
        "ø": "oe", "Ø": "OE",
        "å": "aa", "Å": "AA",
    }
    normalized = text
    for char, replacement in replacements.items():
        normalized = normalized.replace(char, replacement)
    return normalized.lower()

def matches_keyword(text: str, keyword: str) -> bool:
    """Match keyword against text with Norwegian normalization."""
    text_lower = text.lower()
    text_normalized = normalize_norwegian(text)
    keyword_lower = keyword.lower()
    keyword_normalized = normalize_norwegian(keyword)

    return (
        keyword_lower in text_lower
        or keyword_normalized in text_normalized
    )
```

---

## 5. Update Frequency

### Content Publishing Patterns

| Content Type | Typical Frequency | Notes |
|--------------|-------------------|-------|
| News articles | 2-5 per week | Irregular, higher during regulatory changes |
| Warnings/recalls | 1-3 per week | Varies; clustered around enforcement campaigns |
| Regulation updates | Monthly to quarterly | Tied to EU regulation transposition cycles |
| Guidance updates | Quarterly | When new EU directives are implemented |
| Inspection reports | Continuous | Smilefjesdata updated regularly |

### Recommended Polling Frequency

- **Daily scan**: Sufficient for news and warnings (check at 06:00 CET / 05:00 UTC)
- **Weekly deep scan**: Full page comparison for regulation section changes
- **Immediate alerts**: Not possible without RSS/webhook; daily is the practical minimum

### Seasonal Patterns

- **January-March**: EU regulation transposition often finalized
- **September-October**: Enforcement campaigns before holiday sales season
- **Before/after EFSA opinions**: Spikes in health claim-related content

---

## 6. Scraping Approach

### Strategy Priority (Best to Worst)

1. **RSS/Atom feeds** (if available) - Use existing `NewsFeedClient` pattern
2. **Sitemap.xml change detection** - Parse sitemap, detect new/changed URLs
3. **HTML scraping** - Direct page parsing for specific sections
4. **Hybrid approach** - RSS for news + scraping for regulation pages (RECOMMENDED)

### Recommended Hybrid Architecture

```
Mattilsynet Monitor
├── FeedHarvester (if RSS exists)
│   ├── News feed -> new articles
│   └── Warnings feed -> new recalls
├── SitemapWatcher
│   ├── Parse sitemap.xml daily
│   ├── Detect new URLs since last scan
│   └── Fetch and parse new pages
└── PageWatcher (for key regulation pages)
    ├── Hash-based change detection
    ├── Monitor /mat/kosttilskudd
    ├── Monitor /mat/merking-av-mat/helsepastander
    └── Diff extraction on changes
```

### robots.txt Expectations

Norwegian government sites typically allow crawling with reasonable rate limits.
Expected `robots.txt` rules:

```
User-agent: *
Crawl-delay: 10          # Possible; respect if present
Disallow: /admin/         # CMS admin pages
Disallow: /search         # Search result pages
Sitemap: https://www.mattilsynet.no/sitemap.xml
```

**Implementation requirements:**
- Always check and respect `robots.txt` before crawling
- Implement a minimum 5-second delay between requests
- Set a descriptive User-Agent header identifying the bot
- Do not crawl during Norwegian business hours peak (09:00-11:00 CET) if possible

### HTML Parsing Strategy

For pages that need scraping (regulation sections):

```python
# Expected page structure (verify at implementation)
SELECTORS = {
    # Article content area
    "article_body": "article.article-body, main .content-area, .article-content",
    # Article title
    "title": "h1, .article-title",
    # Publication date
    "pub_date": "time[datetime], .article-date, .published-date",
    # Warning/recall specifics
    "warning_product": ".product-name, .recall-product",
    "warning_reason": ".recall-reason, .warning-details",
}
```

### Change Detection Implementation

```python
from hashlib import sha256

class PageChangeDetector:
    """Detect changes to monitored Mattilsynet pages."""

    async def check_page(self, url: str, previous_hash: str) -> ChangeResult:
        """Check if page content has changed since last scan."""
        content = await self._fetch_page(url)
        # Extract main content area (ignore nav, footer, etc.)
        main_content = self._extract_main_content(content)
        current_hash = sha256(main_content.encode()).hexdigest()

        return ChangeResult(
            url=url,
            changed=(current_hash != previous_hash),
            current_hash=current_hash,
            content=main_content if current_hash != previous_hash else None,
        )
```

---

## 7. Legal Considerations

### Norwegian Government Content Reuse

Norwegian government information is generally subject to **offentlighetsloven**
(Freedom of Information Act) and **åndsverkloven** (Copyright Act):

- **Government publications** are generally in the public domain or available
  under open licenses
- **Norwegian Open Government Data License (NLOD)** applies to most government
  data published on data.norge.no
- Mattilsynet's own content (regulations, news, guidance) is public information
- **Fair use for monitoring**: Automated monitoring for regulatory compliance
  purposes is generally acceptable

### Terms of Use Compliance

1. **Rate limiting**: Respect any crawl-delay in robots.txt; use minimum 5s delay
2. **Identification**: Use a proper User-Agent string:
   ```
   DAWO-ECO-RegMonitor/1.0 (contact@dawo.eco; regulatory-compliance-monitoring)
   ```
3. **No redistribution**: Do not republish full article text; store summaries and links
4. **robots.txt**: Always fetch and obey robots.txt directives
5. **No authentication bypass**: Only access publicly available pages

### GDPR Considerations

- Enforcement actions may name individuals or businesses
- Store only regulatory/business entity information, not personal data
- If personal names appear in enforcement notices, treat as public record
  but do not use for marketing purposes

### Recommendation

Automated monitoring of Mattilsynet for regulatory compliance purposes is
**legally permissible** under Norwegian law, provided we:
- Respect robots.txt and rate limits
- Identify our bot properly
- Store summaries and links, not full reproductions
- Use the data for compliance monitoring (our legitimate business interest)

---

## 8. Alternative Norwegian Data Sources

### Primary Alternatives

| Source | URL | Content | Format | Relevance |
|--------|-----|---------|--------|-----------|
| data.norge.no | `https://data.norge.no/` | Norwegian open data portal | Various (API, CSV, JSON) | Search for Mattilsynet datasets |
| Lovdata | `https://lovdata.no/` | Norwegian law database | HTML, some API | Regulation text (kosttilskuddforskriften) |
| Lovdata API | `https://lovdata.no/api/` | Structured law data | REST API | Regulation changes |
| Helsedirektoratet | `https://www.helsedirektoratet.no/` | Health directorate | HTML, RSS | Health claims guidance |
| EFSA | `https://www.efsa.europa.eu/` | EU food safety opinions | RSS, API | Health claim scientific opinions |
| EU Health Claims Register | `https://ec.europa.eu/food/safety/labelling-and-nutrition/nutrition-and-health-claims/health-claims` | Authorized health claims | Searchable DB | Claim status changes |
| RASFF Portal | `https://webgate.ec.europa.eu/rasff-window/screen/search` | EU rapid alert system | Searchable, API | Food/supplement alerts across EU/EEA |

### data.norge.no Datasets

Search `data.norge.no` for:
- "mattilsynet" - All Mattilsynet published datasets
- "kosttilskudd" - Supplement-specific datasets
- "tilsyn" - Inspection/supervision datasets
- "smilefjes" - Restaurant/food establishment inspection grades

### RASFF (EU Rapid Alert System for Food and Feed)

Particularly relevant for DAWO.ECO:
- Covers all EU/EEA countries including Norway
- Reports on border rejections, alerts, and information notifications
- Includes dietary supplement alerts (unauthorized substances, health claims)
- Has a searchable web interface and notifications API
- **URL**: `https://webgate.ec.europa.eu/rasff-window/screen/search`

### Lovdata for Regulation Text

Key regulations to monitor for changes:
- **Kosttilskuddforskriften** (FOR-2004-05-20-755) - Dietary supplement regulation
- **Forskrift om ernaerings- og helsepastander** - Health claims regulation (1924/2006 implementation)
- **Ny mat-forskriften** - Novel food regulation implementation

---

## 9. Implementation Recommendations

### Architecture (Aligns with Existing Scanner Pattern)

The Mattilsynet monitor should follow the same Harvester Framework pattern used
by `teams/dawo/scanners/news/`:

```
teams/dawo/regulatory/mattilsynet/
├── __init__.py
├── agent.py              # RegisteredAgent, tier="scan"
├── config.py             # MattilsynetMonitorConfig (frozen dataclass)
├── schemas.py            # RegulatoryUpdate, EnforcementAction, etc.
├── tools.py              # MattilsynetClient (HTTP + parsing)
├── harvester.py          # Content cleaning and normalization
├── change_detector.py    # Hash-based page change detection
├── transformer.py        # Convert to ResearchItem for research pool
└── pipeline.py           # Orchestration pipeline
```

### Config Structure

```python
# config/dawo_mattilsynet_monitor.json
{
    "feeds": [
        {"name": "Mattilsynet Nyheter", "url": "TBD_VERIFY", "is_tier_1": true},
        {"name": "Mattilsynet Varsler", "url": "TBD_VERIFY", "is_tier_1": true}
    ],
    "monitored_pages": [
        {"name": "Kosttilskudd", "url": "https://www.mattilsynet.no/mat/kosttilskudd"},
        {"name": "Helsepastander", "url": "https://www.mattilsynet.no/mat/merking-av-mat/helsepastander"},
        {"name": "Import av mat", "url": "https://www.mattilsynet.no/mat/import-av-mat"}
    ],
    "keywords_tier_1": ["kosttilskudd", "helsepastander", "tilbakekalling", "advarsel"],
    "keywords_tier_2": ["sopp", "funksjonssopp", "adaptogener", "EFSA", "novel food"],
    "scan_interval_hours": 24,
    "request_delay_seconds": 5,
    "user_agent": "DAWO-ECO-RegMonitor/1.0 (regulatory-compliance-monitoring)"
}
```

### Registration in team_spec.py

```python
RegisteredAgent(
    name="mattilsynet_regulatory_monitor",
    agent_class=MattilsynetMonitorAgent,
    capabilities=["regulatory_monitoring", "enforcement_alerts", "health_claims"],
    tier="scan",  # High-volume scanning task
)
```

### Pre-Implementation Verification Checklist

Before writing Story 6-3, these items MUST be manually verified (requires
browser access to mattilsynet.no):

- [ ] Check `https://www.mattilsynet.no/robots.txt` - confirm crawling rules
- [ ] Check page source for RSS `<link>` tags - confirm feed URLs
- [ ] Visit `https://www.mattilsynet.no/sitemap.xml` - confirm sitemap structure
- [ ] Inspect HTML structure of `/mat/kosttilskudd` - confirm CSS selectors
- [ ] Inspect HTML structure of `/varsler` - confirm warning page selectors
- [ ] Check `https://data.norge.no` for "mattilsynet" datasets
- [ ] Test RASFF API for Norway-specific supplement alerts
- [ ] Verify Lovdata accessibility for regulation text monitoring

### Dependencies

```
# Already in requirements.txt
aiohttp          # HTTP client (used by news scanner)
feedparser       # RSS/Atom parsing (used by news scanner)
beautifulsoup4   # HTML parsing (used by news scanner)

# May need to add
lxml             # Faster HTML/XML parser for BeautifulSoup
```

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| No RSS feeds available | Fall back to sitemap + page scraping approach |
| Site redesign breaks selectors | Use multiple fallback selectors; detect parse failures |
| Rate limiting / IP blocking | Respect robots.txt; 5s delay; rotate times; descriptive UA |
| Norwegian encoding issues | UTF-8 everywhere; normalize ae/oe/aa variants in keyword matching |
| Content in PDF (regulation docs) | Detect PDF links; defer PDF parsing to separate tool |
| Weekend/holiday content gaps | Adjust expectations; don't alert on "no new content" |

---

## 10. Summary

### What We Know

- Mattilsynet.no is the primary source for Norwegian supplement regulations
- The site has clear URL structure with dedicated sections for supplements, health claims, and warnings
- Norwegian government content is generally open for automated monitoring
- Existing news scanner pattern (`teams/dawo/scanners/news/`) provides a solid implementation template
- Multiple complementary sources exist (RASFF, Lovdata, data.norge.no, EFSA)

### What Needs Verification (Pre-Implementation)

- Exact RSS feed URLs (or confirmation that no feeds exist)
- robots.txt crawl rules and sitemap structure
- HTML page structure and CSS selectors for content extraction
- data.norge.no dataset availability for Mattilsynet

### Recommended Approach

**Hybrid RSS + Page Monitoring**:
1. Use RSS feeds for news and warnings (if available)
2. Use sitemap change detection for regulation page updates
3. Use hash-based page monitoring for key supplement regulation pages
4. Integrate RASFF alerts as a complementary EU-wide data source
5. Follow existing Harvester Framework pattern from news scanner
