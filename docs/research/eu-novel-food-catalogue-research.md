# EU Novel Food Catalogue - Programmatic Access Research

**Date:** 2026-02-12
**Purpose:** Epic 6, Story 6-2 - Novel Food Catalogue Monitor
**Owner:** eshroom

---

## 1. Official URL

The EU Novel Food Catalogue is hosted by the European Commission, DG SANTE (Directorate-General for Health and Food Safety):

- **Primary URL:** `https://food.ec.europa.eu/safety/novel-food/novel-food-catalogue_en`
- **Search interface:** `https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search`
- **Legacy URL (redirects):** `https://ec.europa.eu/food/safety/novel-food/catalogue_en`

The catalogue was migrated in 2023-2024 from the legacy `ec.europa.eu/food/` domain to `food.ec.europa.eu/` and the newer Food & Feed Portal. Both URLs may still work, but the Food & Feed Portal is the current canonical interface.

**Important:** The catalogue is part of the broader **Food & Feed Information Portal** which consolidates several EU food databases:
- `https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search`

---

## 2. API Availability

### No Official Public REST API

The EU Novel Food Catalogue does **NOT** provide a documented public REST API. This is consistent with most EU food regulatory databases which are designed for human browsing, not machine consumption.

### What IS Available

| Method | Available | Notes |
|--------|-----------|-------|
| Public REST API | NO | No documented API endpoints |
| GraphQL API | NO | Not available |
| Bulk CSV/JSON download | NO | No official bulk export |
| RSS/Atom feed | NO | No change feeds |
| SPARQL endpoint | PARTIAL | EU Open Data portal has some food law data, but Novel Food Catalogue specifically is not well-represented |
| Web scraping | YES | The search interface returns structured HTML that can be parsed |
| EU Open Data Portal | PARTIAL | `https://data.europa.eu/` - some food safety datasets exist but the Novel Food Catalogue is not available as a standalone dataset |

### Internal API Endpoints (Undocumented)

The Food & Feed Portal search interface uses internal API calls to fetch data. These are **not officially documented or supported**, but they exist:

- The search page at `https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search` uses JavaScript-driven requests to fetch results
- The backend appears to serve JSON responses to the frontend SPA
- Endpoint pattern (observed, subject to change without notice):
  ```
  GET https://ec.europa.eu/food/food-feed-portal/backend/novel-food-catalogue/search
  ```
  With query parameters like `searchText=`, `pageNumber=`, `pageSize=`

**WARNING:** These internal endpoints are:
- Not documented or versioned
- Subject to change without notice
- May have rate limiting or IP blocking
- May require specific headers (CSRF tokens, session cookies)

---

## 3. Data Format

### Web Interface
- **Rendered format:** HTML (server-side rendered SPA with JavaScript hydration)
- **Internal data transport:** JSON (from backend to frontend)
- **Character encoding:** UTF-8
- **Language:** Available in all EU official languages (EN, DE, FR, NL, etc.)

### Data for Each Entry
Each catalogue entry is presented as a detail page with structured text fields. There is no standardized machine-readable format (no JSON-LD, no schema.org markup).

---

## 4. Data Structure

Each Novel Food Catalogue entry contains these fields:

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Common/trade name of the food/ingredient | "Hericium erinaceus (Lion's Mane)" |
| **Category** | General food category | "Fungi / Mushrooms" |
| **Novel Food Status** | Whether it is classified as novel food | "Yes" / "No" / "Not determined" / "Ambiguous" |
| **History of Consumption** | Evidence of significant consumption before May 1997 in EU | Free text description |
| **EU Member State Comments** | Input from individual member states | Free text, often multiple entries |
| **Commission Comments** | Official EC position | Free text |
| **Authorisation Status** | If authorized as novel food under Reg. 2015/2283 | "Authorised" / "Not authorised" / "Application pending" |
| **Conditions of Use** | Restrictions on authorized novel foods | Dosage limits, target population, labeling |
| **Union List Entry** | Reference to the Union List of authorized novel foods | Yes/No + implementing regulation reference |
| **Regulation Reference** | Specific implementing regulation number | e.g., "Commission Implementing Regulation (EU) 2017/2470" |
| **Last Updated** | Date of last modification | Date field |
| **Related Entries** | Cross-references to related substances | Links to other catalogue entries |

### Mushroom-Specific Entries Structure

For our target mushroom species, the catalogue typically lists entries at multiple levels:
- **Species level:** e.g., "Hericium erinaceus"
- **Part/extract level:** e.g., "Hericium erinaceus mycelium extract", "Hericium erinaceus fruiting body"
- **Product form:** e.g., powder, extract, tincture

This means a single mushroom species may have **multiple catalogue entries** with **different novel food statuses** depending on the part/form.

---

## 5. Update Frequency

- **No fixed schedule.** The catalogue is updated on an **ad-hoc basis** when:
  - New novel food applications are submitted
  - Authorisation decisions are made
  - Member states provide updated consultation responses
  - EFSA (European Food Safety Authority) opinions are published
  - Reclassifications occur

- **Practical frequency:** Changes occur approximately **monthly**, sometimes more frequently during active legislative periods.

- **No changelog or version history** is publicly exposed. There is no diff mechanism, RSS feed, or "last modified" header that reliably tracks changes.

- **Implication for monitoring:** We must snapshot the full state and diff locally. Weekly monitoring is appropriate to catch changes without excessive requests.

---

## 6. Filtering - Target Mushroom Species

### Our Monitoring Targets

| Common Name | Latin Name | Known Catalogue Search Terms |
|-------------|-----------|------------------------------|
| Lion's Mane | *Hericium erinaceus* | "Hericium erinaceus", "lion's mane" |
| Chaga | *Inonotus obliquus* | "Inonotus obliquus", "chaga" |
| Reishi | *Ganoderma lucidum* | "Ganoderma lucidum", "reishi", "lingzhi" |
| Cordyceps | *Ophiocordyceps sinensis* / *Cordyceps militaris* | "Cordyceps", "Ophiocordyceps sinensis", "Cordyceps militaris" |
| Shiitake | *Lentinula edodes* | "Lentinula edodes", "shiitake" |
| Maitake | *Grifola frondosa* | "Grifola frondosa", "maitake" |

### Current Known Status (as of early 2026, verify on implementation)

| Species | Fruiting Body | Extract/Concentrate | Mycelium |
|---------|---------------|---------------------|----------|
| Shiitake (*Lentinula edodes*) | Not novel (traditional consumption history in EU) | May be novel depending on extraction method | Variable |
| Reishi (*Ganoderma lucidum*) | Novel food status debated; some forms considered novel | Likely novel | Likely novel |
| Lion's Mane (*Hericium erinaceus*) | Novel food in most forms | Novel food | Novel food |
| Chaga (*Inonotus obliquus*) | Novel food | Novel food | Novel food |
| Cordyceps (*C. militaris*) | Novel food | Novel food | Novel food |
| Cordyceps (*O. sinensis*) | Novel food | Novel food | Novel food |
| Maitake (*Grifola frondosa*) | Novel food status debated | Likely novel | Likely novel |

**IMPORTANT:** These statuses are approximate and the exact determination depends on the specific form, preparation method, and member state interpretation. The actual catalogue entries must be verified during implementation.

### Search Capability

The Food & Feed Portal search interface supports:
- **Free text search** by name (common or Latin)
- **Filtering** by novel food status
- No advanced Boolean operators confirmed
- Search is case-insensitive
- Search matches partial strings

---

## 7. Recommended Access Method for Automated Weekly Monitoring

### Architecture: Hybrid Scraping + Snapshot Diffing

Given the lack of an official API, the recommended approach is:

```
┌─────────────────────────────────────────────────────┐
│                Weekly Monitor Flow                    │
│                                                       │
│  1. For each target species:                          │
│     a. HTTP GET search page with species name         │
│     b. Parse HTML response → extract structured data  │
│     c. Store snapshot in local DB                     │
│                                                       │
│  2. Compare current snapshot vs previous snapshot     │
│     a. Detect field-level changes                     │
│     b. Flag status changes (novel → non-novel, etc.) │
│     c. Flag new entries or removed entries             │
│                                                       │
│  3. If changes detected:                              │
│     a. Create regulatory alert event                  │
│     b. Publish via core/publishing/events.py          │
│     c. Discord notification                           │
│                                                       │
│  4. Store audit log of all checks                     │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### Implementation Strategy

#### Option A: Direct HTML Scraping (Recommended)

```python
# Pseudocode for the monitor
import httpx
from bs4 import BeautifulSoup

SEARCH_URL = "https://ec.europa.eu/food/food-feed-portal/screen/novel-food-catalogue/search"

async def check_species(client: httpx.AsyncClient, species_name: str) -> list[CatalogueEntry]:
    """Fetch and parse Novel Food Catalogue entries for a species."""
    # Step 1: GET the search page with query parameter
    response = await client.get(
        SEARCH_URL,
        params={"searchText": species_name},
        headers={"Accept-Language": "en"},
        timeout=30.0,
    )
    response.raise_for_status()

    # Step 2: Parse HTML or intercept JSON response
    # The actual parsing depends on the page structure at implementation time
    entries = parse_catalogue_response(response.text)
    return entries
```

#### Option B: Headless Browser (Fallback)

If the search page is fully JavaScript-rendered and does not work with plain HTTP requests:

```python
# Use Playwright for JS-rendered content
from playwright.async_api import async_playwright

async def check_species_browser(species_name: str) -> list[CatalogueEntry]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(SEARCH_URL)
        await page.fill('input[type="search"]', species_name)
        await page.click('button[type="submit"]')
        await page.wait_for_selector('.search-results')
        content = await page.content()
        await browser.close()
        return parse_catalogue_html(content)
```

**Note:** Option B adds significant dependency weight (Playwright + Chromium). Option A should be attempted first.

#### Option C: EU Open Data Portal Check (Supplementary)

Check periodically whether the Commission has published a machine-readable dataset:
- `https://data.europa.eu/data/datasets?query=novel+food+catalogue`
- `https://data.europa.eu/api/hub/search/datasets?q=novel+food`

This would be the ideal source if it becomes available.

### Recommended Stack for DAWO.ECO Integration

| Component | Technology | Rationale |
|-----------|------------|-----------|
| HTTP Client | `httpx` (already in project) | Async, connection pooling, timeout control |
| HTML Parser | `beautifulsoup4` + `lxml` | Robust HTML parsing, handles malformed HTML |
| Headless Browser (fallback) | `playwright` | Only if JS rendering required |
| Diff Engine | Custom Python | Compare dataclass snapshots field-by-field |
| Storage | SQLAlchemy model | Store snapshots + change history |
| Scheduling | Existing agent scheduler | Weekly trigger via cron or agent schedule |
| Rate Limiting | `core/config.py` rate limit config | Respect EU servers, 1 req/5sec minimum |

### Recommended Request Patterns

```python
# Rate limiting configuration
NOVEL_FOOD_RATE_LIMITS = {
    "requests_per_minute": 6,        # Conservative: 1 request per 10 seconds
    "retry_after_429": 300,           # Wait 5 min if rate-limited
    "max_retries": 3,
    "backoff_factor": 2.0,
    "timeout_seconds": 30,
    "user_agent": "DAWO-ECO-RegulatoryMonitor/1.0 (+https://dawo.eco; regulatory-compliance)",
}
```

---

## 8. Legal Considerations

### EU Open Data Policy

- The Novel Food Catalogue is **public information** published by the European Commission
- EU institutions' websites generally fall under the **Commission Decision 2011/833/EU** on reuse of Commission documents
- Public data from EU institutions is generally reusable under open terms

### Specific Considerations

| Aspect | Assessment | Notes |
|--------|------------|-------|
| **Data reuse rights** | PERMITTED | EU public sector information is generally reusable under Directive (EU) 2019/1024 (Open Data Directive) |
| **Automated access** | GREY AREA | No explicit robots.txt prohibition observed historically, but no explicit API invitation either |
| **Rate limiting** | REQUIRED | Must be respectful; EU servers are shared infrastructure |
| **robots.txt** | CHECK AT IMPLEMENTATION | Verify `https://ec.europa.eu/robots.txt` and `https://food.ec.europa.eu/robots.txt` |
| **Terms of Service** | CHECK AT IMPLEMENTATION | Review `https://ec.europa.eu/info/legal-notice_en` |
| **Attribution** | REQUIRED | Must attribute "European Commission" as data source |
| **Commercial use** | LIKELY PERMITTED | Open Data Directive generally allows commercial reuse |
| **Data modification** | PERMITTED with attribution | Can process, transform, combine with other data |

### Recommended Legal Safeguards

1. **Respect robots.txt** - Check and comply with any crawl directives
2. **Identify your bot** - Use a descriptive User-Agent string with contact info
3. **Rate limit aggressively** - No more than 6 requests/minute; weekly checks only
4. **Cache responses** - Don't re-fetch data that hasn't changed
5. **Attribution** - Always cite "Source: EU Novel Food Catalogue, European Commission" in any output
6. **No redistribution of raw data** - Use for internal compliance monitoring only
7. **Monitor for cease-and-desist** - If EC requests you stop, comply immediately

### GDPR

- The Novel Food Catalogue contains **no personal data** - it lists food substances, not individuals
- No GDPR concerns for accessing or storing this catalogue data

---

## 9. Alternative / Supplementary Data Sources

| Source | URL | Format | Content |
|--------|-----|--------|---------|
| **EU Union List** (Reg. 2017/2470) | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R2470` | HTML/PDF | Authorized novel foods with conditions |
| **EFSA Novel Food Opinions** | `https://www.efsa.europa.eu/en/topics/topic/novel-food` | HTML | Scientific assessments |
| **EFSA OpenFoodTox** | `https://www.efsa.europa.eu/en/data-report/chemical-hazards-database-openfoodtox` | CSV/Excel | Chemical hazard data (tangential) |
| **EU Open Data Portal** | `https://data.europa.eu/` | Various | Check periodically for novel food datasets |
| **EUR-Lex API** | `https://eur-lex.europa.eu/content/help/data-reuse/webservice.html` | SOAP/REST | Legal texts (implementing regulations for novel food authorizations) |

### EUR-Lex as Supplementary Monitor

The **EUR-Lex CELLAR/SPARQL endpoint** is a proper, documented API that can detect new implementing regulations for novel food authorizations:

```
SPARQL Endpoint: https://publications.europa.eu/webapi/rdf/sparql
```

Query example (conceptual):
```sparql
SELECT ?title ?date ?celex WHERE {
  ?doc cdm:resource_legal_is_about_concept_directory_code "07.30" .
  ?doc cdm:work_date_document ?date .
  ?doc cdm:resource_legal_id_celex ?celex .
  ?doc cdm:expression_title ?title .
  FILTER (?date > "2026-01-01"^^xsd:date)
  FILTER (LANG(?title) = "en")
}
ORDER BY DESC(?date)
```

This can detect new regulations amending the Union List (Reg. 2017/2470), which would indicate authorization changes.

---

## 10. Implementation Recommendations for Story 6-2

### Data Model

```python
@dataclass(frozen=True)
class NovelFoodEntry:
    species_latin: str               # "Hericium erinaceus"
    species_common: str              # "Lion's Mane"
    entry_name: str                  # Full catalogue entry name
    novel_food_status: str           # "novel" | "not_novel" | "not_determined" | "ambiguous"
    authorization_status: str | None # "authorised" | "pending" | "not_authorised" | None
    conditions_of_use: str | None    # Free text
    member_state_comments: str | None
    commission_comments: str | None
    regulation_reference: str | None # e.g., "(EU) 2017/2470"
    last_checked: datetime
    source_url: str
    raw_html_hash: str               # SHA256 of raw response for change detection
```

### Change Detection Strategy

```python
@dataclass(frozen=True)
class CatalogueChange:
    species: str
    entry_name: str
    field_name: str
    old_value: str | None
    new_value: str | None
    detected_at: datetime
    severity: str  # "critical" | "warning" | "info"
```

Severity mapping:
- **CRITICAL:** `novel_food_status` changes, `authorization_status` changes
- **WARNING:** `conditions_of_use` changes, new entries added, entries removed
- **INFO:** `member_state_comments` changes, `commission_comments` changes

### Testing Strategy

- Mock HTTP responses with saved HTML snapshots of actual catalogue pages
- Test change detection with known before/after snapshots
- Integration test with real HTTP request (marked `@pytest.mark.integration`)
- Test all 6 target species parsing

### Dependencies to Add

```
# requirements.txt additions for Story 6-2
beautifulsoup4>=4.12.0
lxml>=5.0.0
# playwright only if JS rendering is required (defer decision)
```

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| EC changes page structure | Medium | High | Hash-based change detection; alert on parse failures |
| EC blocks automated access | Low | High | Respect rate limits; fallback to manual check alert |
| Catalogue migrates to new URL | Medium | Medium | Follow redirects; periodic URL validation |
| JS-only rendering | Medium | Medium | Option B (Playwright) as fallback |
| Data becomes available via API | Low | Positive | Monitor EU Open Data portal; simplify implementation if API appears |
| Catalogue data is ambiguous | High | Medium | Store raw text; let compliance team interpret edge cases |

---

## 12. Summary

**Bottom line:** The EU Novel Food Catalogue has no official API. The recommended approach for Story 6-2 is:

1. **HTTP scraping** with `httpx` + `beautifulsoup4` as the primary method
2. **Weekly schedule** checking all 6 target mushroom species (12 search queries accounting for Latin + common names)
3. **Snapshot diffing** to detect changes, with severity-based alerting
4. **Conservative rate limiting** (1 request per 10 seconds, weekly only)
5. **Supplementary EUR-Lex SPARQL monitoring** for new implementing regulations
6. **Playwright as fallback** only if the search page requires JavaScript rendering

Total requests per weekly check: approximately 12 (6 species x 2 name variants), taking about 2 minutes with rate limiting. This is minimal load on EU infrastructure and well within reasonable use.
