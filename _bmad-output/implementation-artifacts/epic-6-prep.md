# Epic 6 Preparation Tasks

**Created:** 2026-02-12
**Epic:** 6 - CleanMarket & Regulatory Intelligence
**Status:** Pre-implementation

---

## Carryover from Epic 5 Retrospective

### Process Improvements (Priority: High)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Update pre-submission checklist with Epic 5 lessons | Dev Team | **Done** | [docs/pre-submission-checklist.md](../../docs/pre-submission-checklist.md) — added exports section, pipeline patterns, Epic 5 issues |
| 2 | Add deprecation linting to CI | Charlie | **Done** | Already configured in Epic 5 prep (ruff DTZ rules) |
| 3 | Document RetryMiddleware "never raises" + auth error detection | Charlie | **Done** | [docs/retry-middleware-patterns.md](../../docs/retry-middleware-patterns.md) — three-layer pattern documented |

### Technical Debt (Priority: Medium)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | WebSocket event wiring review | Dev Team | Pending | Carried from Epic 4 |
| 2 | Increase integration test coverage on Stories 5-4 and 5-5 | QA | Pending | Unit coverage is strong |

---

## Epic 6 Specific Preparation

### Research Tasks (Critical - Before Epic Starts)

| # | Task | Owner | Status | Research Doc |
|---|------|-------|--------|-------------|
| 1 | EU Health Claims Register API/data access | Dev Team | **Done** | [eu-health-claims-register.md](../../docs/research/eu-health-claims-register.md) |
| 2 | Novel Food Catalogue data format | Dev Team | **Done** | [eu-novel-food-catalogue-research.md](../../docs/research/eu-novel-food-catalogue-research.md) |
| 3 | Evaluate headless browser tools (Playwright) | Charlie | **Done** | [playwright-screenshot-evaluation.md](../../docs/research/playwright-screenshot-evaluation.md) |
| 4 | Evaluate PDF generation libraries | Elena | **Done** | [pdf-generation-evaluation.md](../../docs/research/pdf-generation-evaluation.md) |
| 5 | Design immutable evidence storage approach | Charlie | **Done** | [immutable-evidence-storage-design.md](../../docs/research/immutable-evidence-storage-design.md) |

### Research Tasks (Parallel - During Early Stories)

| # | Task | Owner | Status | Research Doc |
|---|------|-------|--------|-------------|
| 6 | Research Mattilsynet.no RSS/scraping approach | Dev Team | **Done** | [mattilsynet-regulatory-monitor.md](../../docs/research/mattilsynet-regulatory-monitor.md) |
| 7 | Evaluate NLP for health claim extraction | Dev Team | **Done** | [nlp-health-claim-extraction.md](../../docs/research/nlp-health-claim-extraction.md) |

---

## Key Technical Decisions

### Decisions Made

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | EU Health Claims data source | CSV from EU Open Data Portal | Only official machine-readable source; semicolon-delimited, quarterly updates |
| 2 | Novel Food Catalogue access | HTTP scraping (httpx + beautifulsoup4) | No API exists; Playwright fallback if JS-rendered |
| 3 | Mattilsynet monitoring | Hybrid RSS + hash-based page change detection | RSS for news (if available), page hashing for regulation sections |
| 4 | Screenshot capture tool | **Playwright Python** | Only async-native headless browser; Microsoft-backed, active maintenance |
| 5 | PDF report generation | **WeasyPrint** (fallback: ReportLab) | HTML/CSS templates via Jinja2; PDF/A archival support; CSS @page for headers/footers |
| 6 | Health claim extraction | **Hybrid regex + LLM** | Existing ComplianceChecker pattern; 65% cost reduction vs pure LLM; no spaCy in Phase 1 |
| 7 | Evidence storage | **PostgreSQL + file system** with immutability guards | DB triggers + app-level guards + read-only file permissions; SHA-256 integrity hashing |

### Decisions Pending (Verify at Story Start)

| # | Decision | Options | When to Decide |
|---|----------|---------|---------------|
| 1 | Novel Food search page rendering | Plain HTTP vs Playwright | Story 6-2 start — test httpx GET first |
| 2 | Mattilsynet RSS availability | RSS exists vs scraping-only | Story 6-3 start — check page source for RSS links |
| 3 | WeasyPrint Windows dev experience | WeasyPrint vs ReportLab fallback | Story 6-10 start — test Windows install |

---

## New Dependencies

### Required (add to requirements.txt)

```
# Story 6-1: EU Health Claims Monitor
pandas>=2.2.0
deepdiff>=7.0

# Stories 6-1, 6-2, 6-3, 6-5: Web scraping
beautifulsoup4>=4.12.0
lxml>=5.0.0

# Story 6-8: Evidence screenshots
playwright>=1.41.0,<2.0.0

# Story 6-10: PDF reports
weasyprint>=62.0
Jinja2>=3.1
```

### Post-install commands
```bash
playwright install chromium
```

### Docker additions
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libcairo2 fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*
```

---

## Pre-Implementation Verification Checklists

### Story 6-1 (EU Health Claims Register)
- [ ] Visit EU Open Data Portal, confirm CSV download URL
- [ ] Download CSV, verify delimiter (;), encoding (UTF-8 BOM), column names
- [ ] Search register UI for "beta-glucan" and "ganoderma"
- [ ] Check robots.txt at ec.europa.eu

### Story 6-2 (Novel Food Catalogue)
- [ ] Test httpx GET to search URL with `searchText=Hericium` — check if results return in HTML
- [ ] If JS-rendered, prepare Playwright fallback
- [ ] Inspect HTML structure for selectors
- [ ] Check robots.txt at ec.europa.eu and food.ec.europa.eu

### Story 6-3 (Mattilsynet)
- [ ] Check mattilsynet.no/robots.txt
- [ ] Check page source for RSS `<link>` tags
- [ ] Visit mattilsynet.no/sitemap.xml
- [ ] Inspect HTML of /mat/kosttilskudd for CSS selectors
- [ ] Check data.norge.no for "mattilsynet" datasets

---

## Epic 6 Stories Overview

| Story | Title | Key Dependencies | New Tech |
|-------|-------|-----------------|----------|
| 6-1 | EU Health Claims Register Monitor | pandas, deepdiff | CSV parsing, change detection |
| 6-2 | Novel Food Catalogue Monitor | beautifulsoup4, lxml | Web scraping, hash diffing |
| 6-3 | Mattilsynet Regulatory Monitor | feedparser, beautifulsoup4 | RSS/scraping, Norwegian text |
| 6-4 | New Claims Activation Alerts | 6-1 through 6-3 | Discord notifications (existing) |
| 6-5 | Competitor Content Scanner | httpx, beautifulsoup4 | Instagram/website scraping |
| 6-6 | Health Claim Extraction Engine | LLMClientProtocol | Hybrid regex+LLM, Norwegian patterns |
| 6-7 | EU Violation Detection | ComplianceRules | Classification engine |
| 6-8 | Evidence Collection & Screenshots | playwright | Headless browser, SHA-256 hashing |
| 6-9 | Searchable Evidence Database | SQLAlchemy | Immutable storage, full-text search |
| 6-10 | On-Demand Violation Reports | weasyprint, Jinja2 | PDF generation, HTML templates |

---

## Definition of Ready for Epic 6

- [x] All "High" priority carryover tasks completed (pre-submission checklist, RetryMiddleware docs)
- [x] All 5 critical research tasks completed with decision documents
- [x] All 2 parallel research tasks completed
- [x] Key technical decisions documented (7 decided, 3 pending verification)
- [x] New dependency list identified
- [ ] Pre-implementation verification checklists (run at story start)

---

## Pattern Reuse from Previous Epics

| Pattern | Source Epic | Reuse in Epic 6 |
|---------|-----------|-----------------|
| Harvester Framework | Epic 2 | Stories 6-1, 6-2, 6-3, 6-5 (Scanner → Harvester → Transformer → Repository) |
| RetryMiddleware | Epic 1 | All external API calls (EU sites, Mattilsynet, Instagram) |
| Protocol-based DI | Epic 3 | All new services (ScreenshotService, PDFGenerator, EvidenceRepository) |
| ComplianceRules + regex | Epic 1 | Story 6-6 (health claim extraction pre-filter) |
| EUComplianceChecker hybrid | Epic 1 | Story 6-6 (hybrid regex+LLM architecture template) |
| Discord notifications | Epic 4 | Story 6-4 (claims activation alerts) |
| React dashboard | Epic 5 | Story 6-9 (evidence database UI) |

---

## Notes

- Epic 6 is an independent domain from Epic 5 — no direct code dependencies
- Most mushroom/adaptogen health claims are "on hold" (Article 10(3)) since 2012 — detecting any change is the highest-value capability
- For functional mushrooms: NO authorized EU health claims exist — any health claim is unauthorized or prohibited
- Norwegian language support is a critical gap that must be addressed in Story 6-6 (60+ Norwegian patterns for compliance rules)

---

*Created: 2026-02-12*
*Based on: Epic 5 Retrospective action items + Epic 6 preparation research*
