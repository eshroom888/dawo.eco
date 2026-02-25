# EU Health Claims Register - Programmatic Access Research

**Date:** 2026-02-12
**Purpose:** Epic 6 - Regulatory Compliance Monitor (Story 6-1)
**Owner:** eshroom
**Regulation:** EC Regulation 1924/2006 on nutrition and health claims made on foods

---

## 1. Official URLs

| Resource | URL |
|----------|-----|
| **Register (main UI)** | `https://ec.europa.eu/food/safety/labelling_nutrition/claims/register/public/` |
| **Register (newer URL pattern)** | `https://food.ec.europa.eu/safety/labelling-and-nutrition/nutrition-and-health-claims/eu-register-health-claims_en` |
| **EFSA Scientific Opinions** | `https://www.efsa.europa.eu/en/topics/topic/health-claims` |
| **EU Open Data Portal** | `https://data.europa.eu/data/datasets` (search "health claims") |
| **EUR-Lex (Regulation text)** | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32006R1924` |

The register is maintained by **DG SANTE** (Directorate-General for Health and Food Safety) of the European Commission.

---

## 2. API Availability

### 2.1 Official REST API: NONE

As of early 2026, the EU Health Claims Register does **not** provide an official public REST API. The register is a server-rendered web application (Java/JSF-based) with no documented JSON/XML API endpoints.

### 2.2 Undocumented Internal Endpoints

The register's web UI makes internal HTTP requests that can be reverse-engineered:

```
# Search endpoint (form POST, returns HTML)
POST https://ec.europa.eu/food/safety/labelling_nutrition/claims/register/public/
Content-Type: application/x-www-form-urlencoded

# The search form submits parameters like:
#   claimStatus, nutrient, claimType, foodCategory, etc.
```

**Warning:** These are undocumented internal endpoints. They may change without notice and are not guaranteed to remain stable.

### 2.3 EU Open Data Portal (data.europa.eu)

The EU Open Data Portal **does** host a downloadable snapshot of the register:

| Field | Value |
|-------|-------|
| **Dataset URL** | `https://data.europa.eu/data/datasets/eu-register-on-nutrition-and-health-claims` |
| **Publisher** | European Commission, DG SANTE |
| **Format** | **CSV** and **XLSX** |
| **License** | EU Open Data reuse policy (Commission Decision 2011/833/EU) |
| **Update frequency** | Irregular (typically quarterly, sometimes less frequent) |

This is the **recommended primary data source** for programmatic access.

### 2.4 SPARQL Endpoint

The EU Open Data Portal provides a SPARQL endpoint for metadata queries:
```
https://data.europa.eu/sparql
```

However, this queries the *metadata catalog* (DCAT), not the health claims data itself. It is useful for discovering dataset update timestamps but not for querying individual claims.

### 2.5 EFSA Journal / OpenFoodTox

EFSA's scientific opinions that underpin health claim decisions are available through:
- **EFSA Journal API**: `https://efsa.onlinelibrary.wiley.com/` (Wiley API, requires registration)
- **OpenFoodTox**: `https://www.efsa.europa.eu/en/data-report/chemical-hazards-database-openfoodtox` (chemical hazards, tangentially related)

These are supplementary sources, not substitutes for the register itself.

---

## 3. Data Format

### 3.1 CSV/XLSX Download (Primary)

The downloadable dataset from the EU Open Data Portal is available as:

- **CSV** (semicolon-delimited, UTF-8 with BOM)
- **XLSX** (Excel format)

**CSV is recommended** for programmatic parsing. Be aware of:
- Semicolon delimiter (`;`), NOT comma
- Fields containing semicolons are quoted
- UTF-8 encoding with potential BOM marker
- Multi-line values in some claim text fields
- Date format: `DD/MM/YYYY` (European format)

### 3.2 Web Scraping (Fallback)

The web UI returns HTML that can be parsed with BeautifulSoup/lxml. The HTML structure uses `<table>` elements with predictable class names, but the structure may change with site redesigns.

---

## 4. Data Structure

### 4.1 Core Fields in the Register

| Field | Description | Example |
|-------|-------------|---------|
| **Claim ID** | Unique identifier | `ID-2345` |
| **Claim Type** | Category of claim | `Article 13(1)`, `Article 13(5)`, `Article 14` |
| **Nutrient/Substance** | Active substance | `Vitamin D`, `Beta-glucans` |
| **Health Relationship** | The claimed health effect | `Maintenance of normal bones` |
| **Claim Text** | Authorized wording | Full authorized claim text |
| **Conditions of Use** | Required context/dosage | Dosage, target population, warnings |
| **Food Category** | Applicable food types | Broad categories (not mushroom-specific) |
| **Status** | Authorization status | `Authorised`, `Non-Authorised`, `On hold`, `Withdrawn` |
| **EFSA Opinion** | Link to scientific opinion | EFSA Journal reference |
| **Commission Regulation** | Legal basis for decision | EU Regulation number |
| **Date of Entry** | When added to register | `DD/MM/YYYY` |
| **Last Update** | Last modification date | `DD/MM/YYYY` |
| **Restrictions** | Any use restrictions | Population limits, max amounts |

### 4.2 Claim Types (Article References)

| Article | Description |
|---------|-------------|
| **Art. 13(1)** | General function claims (well-established science) |
| **Art. 13(5)** | New function claims (new scientific evidence) |
| **Art. 14(1)(a)** | Disease risk reduction claims |
| **Art. 14(1)(b)** | Claims related to children's development |
| **Art. 10(3)** | Traditional plant claims (on hold / under review) |

### 4.3 Status Values

| Status | Meaning |
|--------|---------|
| `Authorised` | Approved for use on food labeling |
| `Non-Authorised` | Rejected after evaluation |
| `On hold` | Under review (common for botanicals/Art. 10(3)) |
| `Withdrawn` | Previously authorized, now withdrawn |

---

## 5. Filtering for Mushroom/Adaptogen Products

### 5.1 Direct Register Categories

The register does **not** have a specific "mushroom" or "adaptogen" food category. Relevant claims must be found by searching for:

**Substances/nutrients relevant to mushroom products:**
- `Beta-glucans` (from mushrooms: shiitake, maitake, oyster)
- `Vitamin D` / `Vitamin D2` (UV-exposed mushrooms)
- `Ergothioneine` (naturally occurring in mushrooms)
- `Selenium` (accumulated by some mushrooms)
- `Copper` (found in shiitake, oyster mushrooms)
- `B vitamins` (riboflavin, niacin, pantothenic acid in mushrooms)
- `Zinc` (in some mushroom species)
- `Polysaccharides` (general mushroom bioactives)

**Adaptogen-related substances (mostly Art. 10(3) "on hold"):**
- `Ganoderma lucidum` (Reishi)
- `Lentinula edodes` (Shiitake)
- `Grifola frondosa` (Maitake)
- `Inonotus obliquus` (Chaga)
- `Hericium erinaceus` (Lion's Mane)
- `Cordyceps sinensis` / `Cordyceps militaris`
- `Trametes versicolor` (Turkey Tail)
- `Ashwagandha` (Withania somnifera)
- `Rhodiola rosea`
- `Eleutherococcus senticosus` (Siberian ginseng)
- `Panax ginseng`
- `Astragalus membranaceus`
- `Schisandra chinensis`
- `Bacopa monnieri`
- `Holy basil` (Ocimum tenuiflorum)

### 5.2 Important Note on Botanical Claims

Most mushroom and adaptogen health claims fall under **Article 10(3)** - traditional use botanical claims. These have been **"on hold"** since 2012 pending a Commission decision on how to handle them. This means:

- They remain in the register with status `On hold`
- Member states apply their own national rules in the interim
- Any change in this status would be **highly significant** for the mushroom/adaptogen industry
- The "on hold" list is sometimes called the **"botanical claims list"**

This "on hold" status makes the **change detection** aspect of Story 6-1 particularly important.

---

## 6. Update Frequency

| Source | Frequency | Typical Lag |
|--------|-----------|-------------|
| **Register website** | As decisions are published | Days after Official Journal publication |
| **Open Data Portal CSV** | Irregular / quarterly | Weeks to months behind website |
| **Official Journal (EUR-Lex)** | As regulations are adopted | Real-time |

**Recommendation:** A weekly check is more than sufficient. Most changes happen via new Commission Regulations published in the Official Journal, which trigger updates to the register. Major changes (like resolving the botanical "on hold" list) would be preceded by consultation periods.

---

## 7. Access Methods - Implementation Recommendations

### 7.1 Recommended Architecture (Hybrid Approach)

```
Priority 1: CSV Download (Open Data Portal)
    - Full dataset download, diff against previous version
    - Reliable, structured, officially sanctioned
    - Weakness: may lag behind web register by weeks

Priority 2: Web Scraping (Register UI)
    - Weekly targeted scrape of mushroom/adaptogen substance pages
    - Catches updates before CSV is refreshed
    - Weakness: fragile, may break on redesign

Priority 3: EUR-Lex RSS/Atom Feed
    - Monitor Official Journal for new Reg 1924/2006 amendments
    - Earliest signal of regulatory changes
    - Feed URL: https://eur-lex.europa.eu/EN/display-feed.html
    - Filter for CELEX sector 3 (legislation), keyword "health claims"
```

### 7.2 Python Implementation Plan

```python
# Recommended libraries
# requirements.txt additions:
#   httpx>=0.27.0          # async HTTP client (already in project)
#   beautifulsoup4>=4.12   # HTML parsing for scraping fallback
#   lxml>=5.0              # fast XML/HTML parser
#   pandas>=2.2            # CSV parsing with EU date handling
#   feedparser>=6.0        # EUR-Lex RSS/Atom feed parsing
#   deepdiff>=7.0          # structured diff for change detection

import httpx
import pandas as pd
from io import StringIO

# --- CSV Download Approach ---
EU_OPEN_DATA_CSV_URL = (
    "https://data.europa.eu/data/datasets/"
    "eu-register-on-nutrition-and-health-claims"
)
# Note: The actual download URL must be resolved from the dataset page.
# It typically looks like:
# https://webgate.ec.europa.eu/sante/export/...csv
# or similar DG SANTE export endpoint.

async def fetch_claims_csv(client: httpx.AsyncClient) -> pd.DataFrame:
    """Download and parse the EU Health Claims Register CSV."""
    # Step 1: Resolve actual CSV download URL from Open Data Portal
    # Step 2: Download CSV
    response = await client.get(csv_url, follow_redirects=True)
    response.raise_for_status()

    # Parse with EU conventions
    df = pd.read_csv(
        StringIO(response.text),
        sep=";",               # EU uses semicolons
        encoding="utf-8-sig",  # Handle BOM
        parse_dates=["Date of Entry", "Last Update"],
        dayfirst=True,         # DD/MM/YYYY format
    )
    return df


# --- Substance Filter ---
MUSHROOM_ADAPTOGEN_KEYWORDS = [
    "beta-glucan", "ergothioneine",
    "ganoderma", "reishi", "lentinula", "shiitake",
    "grifola", "maitake", "inonotus", "chaga",
    "hericium", "lion's mane", "cordyceps",
    "trametes", "turkey tail",
    "ashwagandha", "withania", "rhodiola",
    "eleutherococcus", "panax ginseng",
    "astragalus", "schisandra", "bacopa",
    "vitamin d", "selenium", "copper", "zinc",
    "riboflavin", "niacin", "pantothenic",
]

def filter_relevant_claims(df: pd.DataFrame) -> pd.DataFrame:
    """Filter claims relevant to mushroom/adaptogen products."""
    pattern = "|".join(MUSHROOM_ADAPTOGEN_KEYWORDS)
    mask = (
        df["Nutrient/Substance"].str.contains(pattern, case=False, na=False)
        | df["Claim Text"].str.contains(pattern, case=False, na=False)
        | df["Conditions of Use"].str.contains(pattern, case=False, na=False)
    )
    return df[mask]


# --- Change Detection ---
def detect_changes(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> dict:
    """Detect new, modified, and removed claims."""
    prev_ids = set(previous["Claim ID"])
    curr_ids = set(current["Claim ID"])

    return {
        "new": curr_ids - prev_ids,
        "removed": prev_ids - curr_ids,
        "modified": _find_modified(previous, current, prev_ids & curr_ids),
    }
```

### 7.3 EUR-Lex RSS Monitoring

```python
import feedparser

EURLEX_FEED_URL = (
    "https://eur-lex.europa.eu/EN/display-feed.html"
    "?myRssId=LhvOGSBwlbCN99IYVkFIoTbXGqRBIA5ioHUj6qMDTCE%3D"
)
# Note: RSS feed URLs on EUR-Lex are user-configured.
# You need to set up a "My EUR-Lex" alert for:
#   - Sector: Legislation
#   - Keywords: "health claims" OR "1924/2006"
#   - Document types: Regulations, Decisions

async def check_eurlex_feed(client: httpx.AsyncClient) -> list[dict]:
    """Check EUR-Lex for new health claims legislation."""
    resp = await client.get(EURLEX_FEED_URL)
    feed = feedparser.parse(resp.text)

    new_items = []
    for entry in feed.entries:
        if _is_health_claims_related(entry):
            new_items.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "summary": entry.summary,
            })
    return new_items
```

### 7.4 Web Scraping Fallback

```python
from bs4 import BeautifulSoup

REGISTER_URL = (
    "https://ec.europa.eu/food/safety/"
    "labelling_nutrition/claims/register/public/"
)

async def scrape_register_search(
    client: httpx.AsyncClient,
    substance: str,
) -> list[dict]:
    """Scrape the register UI for a specific substance.

    WARNING: This is a fragile fallback. The register UI may change
    structure at any time. Use CSV download as primary source.
    """
    # The register uses a form POST for search
    form_data = {
        "nutrient": substance,
        # Additional form fields may be required
        # (CSRF token, view state, etc. -- inspect with browser DevTools)
    }

    resp = await client.post(
        REGISTER_URL,
        data=form_data,
        headers={"Accept": "text/html"},
        follow_redirects=True,
    )

    soup = BeautifulSoup(resp.text, "lxml")
    # Parse table rows -- structure must be verified against live site
    results = []
    for row in soup.select("table.register-results tr"):
        cells = row.find_all("td")
        if cells:
            results.append({
                "claim_id": cells[0].get_text(strip=True),
                "substance": cells[1].get_text(strip=True),
                "claim_text": cells[2].get_text(strip=True),
                "status": cells[3].get_text(strip=True),
                # ... map remaining columns
            })
    return results
```

---

## 8. Legal Considerations

### 8.1 Open Data Reuse

The EU Open Data Portal datasets are published under **Commission Decision 2011/833/EU** which:
- **Permits** free reuse for commercial and non-commercial purposes
- **Requires** acknowledgment of the source (European Commission)
- **Does not require** prior authorization for reuse
- Applies to machine-readable datasets explicitly

**Recommended attribution:**
> Source: European Commission, EU Register on nutrition and health claims,
> licensed under Commission Decision 2011/833/EU on the reuse of Commission documents.

### 8.2 Web Scraping Considerations

The EC website's `robots.txt` and terms of use should be checked before scraping:
- EC websites generally permit crawling for non-abusive purposes
- Rate limiting is essential (no more than 1 request per 5 seconds recommended)
- Respect `Crawl-delay` directives in `robots.txt`
- The register's terms of use page should be reviewed for specific restrictions
- **Never** scrape at a rate that could degrade service for other users

### 8.3 GDPR

Not applicable -- the register contains no personal data. All data relates to food substances and regulatory decisions.

### 8.4 Caching and Redistribution

- Caching downloaded data locally is explicitly permitted under open data rules
- Redistribution of the data is permitted with attribution
- Derived analyses (e.g., filtered views for mushroom products) are permitted

---

## 9. Known Limitations and Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| CSV on Open Data Portal lags behind live register | Medium | Use web scraping as supplementary source |
| Register UI redesign breaks scraper | Medium | CSV as primary; scraper as optional enhancement |
| CSV format/delimiter changes | Low | Validate format on each download; alert on parse errors |
| "On hold" botanical list resolved en masse | Low probability, high impact | EUR-Lex feed will catch this first |
| Open Data Portal CSV URL changes | Medium | Resolve download URL dynamically from dataset page |
| Rate limiting / IP blocking on EC servers | Low | Respect rate limits; weekly cadence is very conservative |

---

## 10. Implementation Recommendation for Story 6-1

### Architecture

```
EUHealthClaimsMonitor
    |
    +-- CSVDownloader          # Primary: Open Data Portal CSV
    |       downloads full CSV, parses, stores locally
    |
    +-- RegisterScraper        # Secondary: targeted substance searches
    |       scrapes web UI for specific mushroom/adaptogen substances
    |       (optional enhancement, can be deferred)
    |
    +-- EURLexFeedChecker      # Tertiary: legislation monitoring
    |       RSS feed for new regulations mentioning health claims
    |
    +-- ChangeDetector         # Diffs current vs previous dataset
    |       identifies new, modified, removed, status-changed claims
    |
    +-- RelevanceFilter        # Filters for mushroom/adaptogen keywords
    |       configurable keyword list in config/dawo_health_claims.json
    |
    +-- AlertPublisher         # Publishes change events
            uses core/publishing/events.py EventBus
```

### Suggested Config (`config/dawo_health_claims.json`)

```json
{
    "monitor": {
        "schedule_cron": "0 6 * * 1",
        "csv_source_url": "https://data.europa.eu/data/datasets/eu-register-on-nutrition-and-health-claims",
        "eurlex_feed_url": null,
        "scrape_enabled": false,
        "request_delay_seconds": 5,
        "max_retries": 3
    },
    "substances": {
        "mushroom": [
            "beta-glucan", "ergothioneine", "chitin",
            "ganoderma", "reishi", "lentinula", "shiitake",
            "grifola", "maitake", "inonotus", "chaga",
            "hericium", "lion's mane", "cordyceps",
            "trametes", "turkey tail", "pleurotus",
            "agaricus", "tremella", "polyporus"
        ],
        "adaptogen": [
            "ashwagandha", "withania somnifera",
            "rhodiola", "rhodiola rosea",
            "eleutherococcus", "siberian ginseng",
            "panax ginseng", "astragalus",
            "schisandra", "bacopa",
            "holy basil", "ocimum tenuiflorum",
            "maca", "lepidium meyenii",
            "tulsi", "turmeric", "curcumin"
        ],
        "vitamins_minerals": [
            "vitamin d", "vitamin d2", "ergocalciferol",
            "selenium", "copper", "zinc", "iron",
            "riboflavin", "niacin", "pantothenic acid",
            "folate", "vitamin b12", "potassium"
        ]
    },
    "alert_on_status_change": [
        "On hold -> Authorised",
        "On hold -> Non-Authorised",
        "Authorised -> Withdrawn",
        "Non-Authorised -> Authorised"
    ]
}
```

### Minimum Viable Implementation (MVP)

For Story 6-1 MVP, implement only:

1. **CSV download + parse** from EU Open Data Portal
2. **Keyword filter** against configured substance lists
3. **Change detection** via pandas DataFrame diff against last-stored snapshot
4. **Event publishing** through existing `core/publishing/events.py`
5. **SQLAlchemy model** for storing claim snapshots and change history

Defer web scraping and EUR-Lex feed to a later story or enhancement.

### Required New Dependencies

```
# Add to requirements.txt
pandas>=2.2.0
openpyxl>=3.1.0        # for XLSX fallback parsing
deepdiff>=7.0           # structured change detection
feedparser>=6.0.11      # EUR-Lex RSS (can defer)
beautifulsoup4>=4.12.0  # web scraping fallback (can defer)
lxml>=5.0.0             # HTML/XML parser (can defer)
```

---

## 11. Verification Steps

Before implementing Story 6-1, manually verify the following:

- [ ] Visit `https://data.europa.eu/data/datasets` and search "health claims register" to confirm dataset exists and note the exact download URL
- [ ] Download the CSV and inspect delimiter, encoding, and column names
- [ ] Search the register UI for "beta-glucan" and "ganoderma" to confirm relevant results exist
- [ ] Check `robots.txt` at `https://ec.europa.eu/robots.txt` for any crawl restrictions
- [ ] Set up a EUR-Lex alert for "1924/2006" to obtain the RSS feed URL
- [ ] Confirm the CSV column names match the field mapping in this document

---

## Sources

- EC Regulation 1924/2006: `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32006R1924`
- EU Register (web UI): `https://ec.europa.eu/food/safety/labelling_nutrition/claims/register/public/`
- EU Open Data Portal: `https://data.europa.eu/`
- Commission Decision 2011/833/EU (reuse of documents): `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32011D0833`
- EFSA Health Claims topic page: `https://www.efsa.europa.eu/en/topics/topic/health-claims`
