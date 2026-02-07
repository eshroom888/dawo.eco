# Story 2.7: PubMed Scientific Research Scanner

Status: complete

---

## Story

As an **operator**,
I want scientific research automatically aggregated from PubMed,
So that I have evidence-backed insights for compliant content creation.

---

## Acceptance Criteria

1. **Given** the PubMed scanner is scheduled (weekly Sunday 4 AM)
   **When** it executes
   **Then** it searches PubMed for mushroom/adaptogen studies
   **And** it filters by: RCTs, Meta-Analyses, Reviews from last 90 days
   **And** it collects abstracts with full metadata

2. **Given** a scientific study is found
   **When** the harvester processes it
   **Then** it extracts: title, abstract, authors, journal, DOI, publication date
   **And** it captures study type (RCT, meta-analysis, review) and sample size if available
   **And** it preserves all PubMed identifiers (PMID, DOI)

3. **Given** an abstract contains findings about mushroom compounds
   **When** the finding summarizer processes it
   **Then** it generates a plain-language summary of key findings
   **And** it extracts: compound studied, effect measured, statistical significance
   **And** it flags claims that could inform content (NOT for direct health claims)

4. **Given** a finding relates to a potential health claim
   **When** the claim validator processes it
   **Then** it cross-references against EU Health Claims Register
   **And** it notes: "Can cite study but NOT claim treatment"
   **And** it tags content potential: educational, trend-awareness, citation-only

5. **Given** PubMed Entrez API is unavailable
   **When** retry middleware exhausts attempts
   **Then** the scan is marked INCOMPLETE and queued for next cycle
   **And** previous research remains available

---

## Tasks / Subtasks

- [x] Task 1: Create PubMed scanner agent structure (AC: #1, #2)
  - [x] 1.1 Create `teams/dawo/scanners/pubmed/` directory structure
  - [x] 1.2 Create `__init__.py` with complete exports and `__all__` list
  - [x] 1.3 Create `agent.py` with `PubMedScanner` class
  - [x] 1.4 Create `prompts.py` with finding summarization prompts (uses generate tier)
  - [x] 1.5 Create `tools.py` with PubMed Entrez API tools using Biopython
  - [x] 1.6 Create `config.py` with `PubMedScannerConfig` dataclass
  - [x] 1.7 Create `schemas.py` with `RawPubMedArticle`, `HarvestedArticle`, `FindingSummary`, `ClaimValidationResult` schemas

- [x] Task 2: Implement PubMed Entrez client (AC: #1, #5)
  - [x] 2.1 Create `PubMedClient` class in `tools.py` using Biopython's Entrez module
  - [x] 2.2 Accept email and API key via dependency injection (required by NCBI policy)
  - [x] 2.3 Implement `search(query: str, max_results: int, filters: dict) -> list[str]` returning PMIDs
  - [x] 2.4 Implement `fetch_details(pmids: list[str]) -> list[dict]` for article metadata
  - [x] 2.5 Implement rate limiting (3 req/sec without API key, 10 req/sec with key)
  - [x] 2.6 Wrap all API calls with retry middleware (Story 1.5)
  - [x] 2.7 Handle Entrez-specific errors (invalid queries, API limits)

- [x] Task 3: Implement scanner stage (AC: #1)
  - [x] 3.1 Create `scan()` method that processes configured search queries
  - [x] 3.2 Default queries: ["lion's mane cognition", "chaga antioxidant", "reishi immune", "cordyceps performance", "Hericium erinaceus", "Inonotus obliquus"]
  - [x] 3.3 Apply publication type filters: ["Randomized Controlled Trial", "Meta-Analysis", "Review"]
  - [x] 3.4 Filter results by: publication date (last 90 days)
  - [x] 3.5 Deduplicate results by PMID
  - [x] 3.6 Return list of `RawPubMedArticle` objects with PMIDs
  - [x] 3.7 Log scan statistics: queries executed, articles found, filtered count

- [x] Task 4: Implement harvester stage (AC: #2)
  - [x] 4.1 Create `PubMedHarvester` class
  - [x] 4.2 Accept `PubMedClient` via dependency injection
  - [x] 4.3 Implement `harvest(raw_articles: list[RawPubMedArticle]) -> list[HarvestedArticle]`
  - [x] 4.4 For each article, fetch: full abstract, title, authors list, journal name, publication date
  - [x] 4.5 Extract DOI from article identifiers
  - [x] 4.6 Parse study type from MeSH terms or publication type
  - [x] 4.7 Extract sample size from abstract using regex patterns (e.g., "n=77", "77 participants")
  - [x] 4.8 Build PubMed URL: `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`
  - [x] 4.9 Rate limit API calls per NCBI guidelines

- [x] Task 5: Implement finding summarizer (AC: #3)
  - [x] 5.1 Create `FindingSummarizer` class
  - [x] 5.2 Use `tier="generate"` (Sonnet) for quality scientific summarization
  - [x] 5.3 Implement `summarize(abstract: str, study_type: str) -> FindingSummary`
  - [x] 5.4 Extract: compound studied (e.g., "Lion's mane extract"), effect measured (e.g., "cognitive function improvement")
  - [x] 5.5 Extract: statistical significance (p-value, confidence interval if stated)
  - [x] 5.6 Generate plain-language summary suitable for content inspiration
  - [x] 5.7 Flag content potential: educational, citation-worthy, trend-indicator
  - [x] 5.8 Include caveat: "Study findings - not approved health claims"

- [x] Task 6: Implement claim validator (AC: #4)
  - [x] 6.1 Create `ClaimValidator` class
  - [x] 6.2 Use `tier="generate"` (Sonnet) for accurate claim assessment
  - [x] 6.3 Accept `EUComplianceChecker` via dependency injection (Story 1.2)
  - [x] 6.4 Implement `validate_claim_potential(summary: FindingSummary) -> ClaimValidationResult`
  - [x] 6.5 Cross-reference extracted findings with EU compliance rules
  - [x] 6.6 Tag content potential categories:
        - `citation_only`: Can cite study with DOI link
        - `educational`: Can discuss generally without claims
        - `trend_awareness`: Indicates research direction
        - `no_claim`: Cannot use for marketing claims
  - [x] 6.7 Add standard caveat: "Can cite study but NOT claim treatment/prevention/cure"
  - [x] 6.8 Return ClaimValidationResult with tags and usage guidance

- [x] Task 7: Implement transformer stage (AC: #2, #3, #4)
  - [x] 7.1 Create `PubMedTransformer` class
  - [x] 7.2 Accept `FindingSummarizer` and `ClaimValidator` via dependency injection
  - [x] 7.3 Implement `transform(harvested: list[HarvestedArticle]) -> list[TransformedResearch]`
  - [x] 7.4 Map PubMed fields to Research Pool schema:
        - `source`: "pubmed"
        - `source_id`: PMID
        - `title`: article title
        - `content`: abstract + finding summary + usage guidance
        - `summary`: LLM-generated plain-language summary
        - `url`: PubMed URL
        - `tags`: auto-generate from compound, effect, study type
        - `source_metadata`: {authors, journal, doi, study_type, sample_size, publication_types, claim_potential}
        - `created_at`: publication date
  - [x] 7.5 Set high base score for peer-reviewed content (scientific papers are premium)
  - [x] 7.6 Truncate abstract if > 10,000 chars (rare for PubMed)

- [x] Task 8: Implement validator stage (AC: #4)
  - [x] 8.1 Create `PubMedValidator` class
  - [x] 8.2 Accept `EUComplianceChecker` via dependency injection (from Story 1.2)
  - [x] 8.3 Implement `validate(items: list[TransformedResearch]) -> list[ValidatedResearch]`
  - [x] 8.4 Call compliance checker on summary content (not raw abstract)
  - [x] 8.5 Set `compliance_status` based on content potential (most should be COMPLIANT for research)
  - [x] 8.6 Preserve `claim_potential` tags for content team guidance
  - [x] 8.7 Log validation statistics: passed, with caveats, rejected

- [x] Task 9: Integrate with Research Publisher (AC: #2, #3, #4)
  - [x] 9.1 Accept `ResearchPublisher` via dependency injection (from Story 2.1)
  - [x] 9.2 Accept `ResearchItemScorer` via dependency injection (from Story 2.2)
  - [x] 9.3 Implement `publish_results(validated: list[ValidatedResearch]) -> list[ResearchItem]`
  - [x] 9.4 Score each item: boost for RCTs (+2), meta-analyses (+2.5), recent publication (+0.5)
  - [x] 9.5 Publish to Research Pool via publisher
  - [x] 9.6 Return created ResearchItem list with IDs

- [x] Task 10: Create orchestrated pipeline (AC: #1, #2, #3, #4, #5)
  - [x] 10.1 Create `PubMedResearchPipeline` class
  - [x] 10.2 Accept all stage components via dependency injection
  - [x] 10.3 Implement `execute() -> PipelineResult`
  - [x] 10.4 Chain stages: scan -> harvest -> summarize_findings -> validate_claims -> transform -> validate -> score -> publish
  - [x] 10.5 Track and return statistics: queries_executed, articles_found, summaries_generated, claim_validations, published
  - [x] 10.6 Handle partial failures: continue pipeline even if some articles fail summarization

- [x] Task 11: Implement graceful degradation (AC: #5)
  - [x] 11.1 Wrap pipeline execution in try/catch
  - [x] 11.2 On Entrez API failure (after retries), mark scan as INCOMPLETE
  - [x] 11.3 Track which queries succeeded/failed separately
  - [x] 11.4 Log failure details for debugging
  - [x] 11.5 Queue for next scheduled run (via ARQ job queue)
  - [x] 11.6 Ensure existing Research Pool data remains intact

- [x] Task 12: Register in team_spec.py (AC: #1)
  - [x] 12.1 Add `PubMedScanner` as RegisteredAgent with tier="scan"
  - [x] 12.2 Add `FindingSummarizer` as RegisteredAgent with tier="generate"
  - [x] 12.3 Add `ClaimValidator` as RegisteredAgent with tier="generate"
  - [x] 12.4 Add `PubMedHarvester` as RegisteredService
  - [x] 12.5 Add `PubMedTransformer` as RegisteredService
  - [x] 12.6 Add `PubMedValidator` as RegisteredService
  - [x] 12.7 Add `PubMedResearchPipeline` as RegisteredService with capability="pubmed_research"
  - [x] 12.8 Ensure all components are injectable via Team Builder

- [x] Task 13: Create configuration file (AC: #1)
  - [x] 13.1 Create `config/dawo_pubmed_scanner.json`
  - [x] 13.2 Define search queries: ["lion's mane cognition", "chaga antioxidant", "reishi immune", "cordyceps performance", "Hericium erinaceus", "Inonotus obliquus", "adaptogen stress", "functional mushroom"]
  - [x] 13.3 Define publication_type_filters: ["Randomized Controlled Trial", "Meta-Analysis", "Review"]
  - [x] 13.4 Define filters: lookback_days=90, max_results_per_query=50
  - [x] 13.5 Define schedule: cron expression for weekly Sunday 4 AM
  - [x] 13.6 Add email placeholder: "${PUBMED_EMAIL}" (required by NCBI)
  - [x] 13.7 Add API key placeholder: "${PUBMED_API_KEY}" (optional, increases rate limit)

- [x] Task 14: Create comprehensive unit tests
  - [x] 14.1 Test PubMedClient search and fetch_details methods
  - [x] 14.2 Test scanner query execution and PMID deduplication
  - [x] 14.3 Test harvester metadata extraction (authors, DOI, sample size parsing)
  - [x] 14.4 Test FindingSummarizer prompt and response parsing
  - [x] 14.5 Test ClaimValidator cross-referencing and content potential tagging
  - [x] 14.6 Test transformer field mapping and score boosting
  - [x] 14.7 Test validator compliance integration
  - [x] 14.8 Test pipeline orchestration
  - [x] 14.9 Test graceful degradation on Entrez API failure
  - [x] 14.10 Test partial failure handling (some queries fail)
  - [x] 14.11 Mock Entrez API responses for all tests

- [x] Task 15: Create integration tests
  - [x] 15.1 Test full pipeline with mocked PubMed API
  - [x] 15.2 Test Research Pool insertion (with test database)
  - [x] 15.3 Test scoring integration with study type boosts
  - [x] 15.4 Test retry middleware integration
  - [x] 15.5 Test claim validation flow
  - [x] 15.6 Test LLM summarization with mock responses

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Harvester-Framework], [project-context.md#Code-Organization]

This is the **FIFTH scanner** in the Harvester Framework - it MUST follow the exact pattern established by Reddit (2.3), YouTube (2.4), Instagram (2.5), and News (2.6).

**Harvester Framework Pipeline (Extended for PubMed):**
```
[Scanner] -> [Harvester] -> [Finding Summarizer] -> [Claim Validator] -> [Transformer] -> [Validator] -> [Scorer] -> [Publisher] -> [Research Pool]
     |           |                  |                       |                  |              |            |           |
   scan()    harvest()       summarize()          validate_claim()       transform()    validate()    score()    publish()
   tier=scan  tier=scan        tier=generate         tier=generate          tier=scan      tier=scan   tier=scan   tier=scan
```

**Key Differences from Other Scanners:**
- Uses **Biopython's Entrez** module instead of REST API client
- Has **two LLM stages**: FindingSummarizer AND ClaimValidator (both tier="generate")
- **Weekly schedule** (not daily) due to scientific publication cadence
- **Higher value content** - peer-reviewed studies deserve score boost
- **Scientific metadata** extraction: DOI, study type, sample size, authors
- **Claim validation** specific to EU Health Claims context

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Directory-Structure]

```
teams/dawo/
├── scanners/
│   ├── reddit/                        # EXISTS from Story 2.3
│   ├── youtube/                       # EXISTS from Story 2.4
│   ├── instagram/                     # EXISTS from Story 2.5
│   ├── news/                          # EXISTS from Story 2.6
│   └── pubmed/                        # CREATE THIS MODULE
│       ├── __init__.py                # Export all public types
│       ├── agent.py                   # PubMedScanner main class
│       ├── prompts.py                 # Finding summarization prompts
│       ├── tools.py                   # PubMedClient using Biopython Entrez
│       ├── config.py                  # PubMedScannerConfig
│       ├── schemas.py                 # RawPubMedArticle, HarvestedArticle, FindingSummary, ClaimValidationResult
│       ├── harvester.py               # PubMedHarvester
│       ├── finding_summarizer.py      # FindingSummarizer (LLM)
│       ├── claim_validator.py         # ClaimValidator (LLM)
│       ├── transformer.py             # PubMedTransformer
│       ├── validator.py               # PubMedValidator
│       └── pipeline.py                # PubMedResearchPipeline
├── research/                          # Exists from Story 2.1
│   ├── models.py                      # ResearchItem, ResearchSource
│   ├── repository.py                  # ResearchPoolRepository
│   ├── publisher.py                   # ResearchPublisher
│   └── scoring/                       # Exists from Story 2.2
│       └── scorer.py                  # ResearchItemScorer

config/
└── dawo_pubmed_scanner.json           # CREATE: Scanner configuration

tests/teams/dawo/
└── test_scanners/
    ├── test_reddit/                   # EXISTS from Story 2.3
    ├── test_youtube/                  # EXISTS from Story 2.4
    ├── test_instagram/                # EXISTS from Story 2.5
    ├── test_news/                     # EXISTS from Story 2.6
    └── test_pubmed/                   # CREATE THIS
        ├── __init__.py
        ├── conftest.py                # Fixtures, mocks
        ├── test_client.py             # PubMedClient tests
        ├── test_scanner.py            # Scanner stage tests
        ├── test_harvester.py          # Harvester stage tests
        ├── test_finding_summarizer.py # Summarizer tests
        ├── test_claim_validator.py    # Claim validation tests
        ├── test_transformer.py        # Transformer stage tests
        ├── test_validator.py          # Validator stage tests
        ├── test_pipeline.py           # Full pipeline tests
        └── test_integration.py        # Integration with Research Pool
```

### Biopython Entrez Implementation

**Source:** [epic-2-prep.md#PubMed-Entrez-API]

**Dependencies:**
- `biopython>=1.81` for Entrez E-utilities
- Already in requirements.txt from Epic 2 prep

**PubMedClient:**
```python
# tools.py
from Bio import Entrez
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import asyncio

@dataclass
class EntrezConfig:
    """Entrez configuration - loaded from config via injection."""
    email: str  # Required by NCBI policy
    api_key: Optional[str] = None  # Optional, increases rate limit

class PubMedClient:
    """PubMed Entrez client for scientific research retrieval.

    Uses Biopython's Entrez module for NCBI E-utilities access.
    Accepts configuration via dependency injection - NEVER loads files directly.
    Wraps all fetches with retry middleware (Story 1.5).
    """

    # Rate limits per NCBI policy
    RATE_LIMIT_NO_KEY = 3  # requests/second without API key
    RATE_LIMIT_WITH_KEY = 10  # requests/second with API key
    DEFAULT_TOOL = "DAWO.ECO Research Scanner"

    def __init__(
        self,
        config: EntrezConfig,
        retry_middleware: RetryMiddleware
    ):
        """Accept config via injection from Team Builder."""
        self._config = config
        self._retry = retry_middleware
        self._rate_limit = (
            self.RATE_LIMIT_WITH_KEY if config.api_key
            else self.RATE_LIMIT_NO_KEY
        )
        self._last_request = datetime.min

        # Configure Entrez
        Entrez.email = config.email
        Entrez.api_key = config.api_key
        Entrez.tool = self.DEFAULT_TOOL

    async def _rate_limit_wait(self) -> None:
        """Wait to respect rate limits."""
        min_interval = 1.0 / self._rate_limit
        elapsed = (datetime.now(timezone.utc) - self._last_request).total_seconds()
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = datetime.now(timezone.utc)

    @with_retry(RetryConfig(max_attempts=3, backoff_base=2.0))
    async def search(
        self,
        query: str,
        max_results: int = 50,
        date_filter: Optional[int] = None  # Days back
    ) -> list[str]:
        """Search PubMed for articles matching query.

        Args:
            query: Search query (supports PubMed syntax)
            max_results: Maximum results to return
            date_filter: Only include articles from last N days

        Returns:
            List of PMIDs matching query

        Raises:
            PubMedSearchError: On search failure
        """
        await self._rate_limit_wait()

        try:
            # Build date filter if specified
            date_range = ""
            if date_filter:
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=date_filter)
                date_range = f' AND ("{start_date.strftime("%Y/%m/%d")}"[PDAT] : "{end_date.strftime("%Y/%m/%d")}"[PDAT])'

            # Run in executor since Entrez is sync
            loop = asyncio.get_event_loop()
            handle = await loop.run_in_executor(
                None,
                lambda: Entrez.esearch(
                    db="pubmed",
                    term=query + date_range,
                    retmax=max_results,
                    sort="relevance"
                )
            )

            record = Entrez.read(handle)
            handle.close()

            return record.get("IdList", [])

        except Exception as e:
            logger.error("PubMed search failed for query '%s': %s", query, e)
            raise PubMedSearchError(f"Search failed: {e}") from e

    @with_retry(RetryConfig(max_attempts=3, backoff_base=2.0))
    async def fetch_details(self, pmids: list[str]) -> list[dict]:
        """Fetch full article details for given PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of article detail dictionaries

        Raises:
            PubMedFetchError: On fetch failure
        """
        if not pmids:
            return []

        await self._rate_limit_wait()

        try:
            # Fetch in batches of 200 (NCBI limit)
            all_articles = []
            batch_size = 200

            for i in range(0, len(pmids), batch_size):
                batch = pmids[i:i + batch_size]

                loop = asyncio.get_event_loop()
                handle = await loop.run_in_executor(
                    None,
                    lambda: Entrez.efetch(
                        db="pubmed",
                        id=",".join(batch),
                        rettype="xml",
                        retmode="xml"
                    )
                )

                records = Entrez.read(handle)
                handle.close()

                # Parse PubmedArticle records
                for article in records.get("PubmedArticle", []):
                    parsed = self._parse_article(article)
                    if parsed:
                        all_articles.append(parsed)

                # Rate limit between batches
                if i + batch_size < len(pmids):
                    await self._rate_limit_wait()

            return all_articles

        except Exception as e:
            logger.error("PubMed fetch failed for PMIDs: %s", e)
            raise PubMedFetchError(f"Fetch failed: {e}") from e

    def _parse_article(self, article: dict) -> Optional[dict]:
        """Parse PubmedArticle XML record to dict."""
        try:
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})

            # Extract PMID
            pmid = str(medline.get("PMID", ""))
            if not pmid:
                return None

            # Extract title
            title = article_data.get("ArticleTitle", "")

            # Extract abstract
            abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
            if isinstance(abstract_parts, list):
                abstract = " ".join(str(part) for part in abstract_parts)
            else:
                abstract = str(abstract_parts)

            # Extract authors
            authors = []
            author_list = article_data.get("AuthorList", [])
            for author in author_list[:10]:  # Limit to first 10
                last = author.get("LastName", "")
                first = author.get("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

            # Extract journal
            journal_info = article_data.get("Journal", {})
            journal = journal_info.get("Title", "")

            # Extract publication date
            pub_date = None
            date_info = article_data.get("ArticleDate", [])
            if date_info:
                d = date_info[0]
                try:
                    pub_date = datetime(
                        int(d.get("Year", 2000)),
                        int(d.get("Month", 1)),
                        int(d.get("Day", 1)),
                        tzinfo=timezone.utc
                    )
                except (ValueError, TypeError):
                    pass

            # Extract DOI
            doi = None
            id_list = article.get("PubmedData", {}).get("ArticleIdList", [])
            for id_obj in id_list:
                if str(id_obj.attributes.get("IdType", "")) == "doi":
                    doi = str(id_obj)
                    break

            # Extract publication types
            pub_types = []
            type_list = article_data.get("PublicationTypeList", [])
            for pt in type_list:
                pub_types.append(str(pt))

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "pub_date": pub_date,
                "doi": doi,
                "publication_types": pub_types,
            }

        except Exception as e:
            logger.warning("Failed to parse article: %s", e)
            return None
```

### Finding Summarizer (LLM Stage)

**Source:** [prd.md#PubMed-Research-Team], [epic-2-prep.md]

**CRITICAL:** Uses `tier="generate"` (Sonnet) for quality scientific summarization.

```python
# finding_summarizer.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class FindingSummary:
    """Summarized research finding."""
    compound_studied: str  # e.g., "Lion's mane extract (Hericium erinaceus)"
    effect_measured: str  # e.g., "cognitive function improvement"
    key_findings: str  # Plain-language summary
    statistical_significance: Optional[str]  # e.g., "p<0.05, n=77"
    study_strength: str  # "strong", "moderate", "weak"
    content_potential: list[str]  # ["educational", "citation_worthy"]
    caveat: str  # Standard disclaimer

class FindingSummarizer:
    """LLM-powered scientific finding summarizer.

    Uses tier="generate" (Sonnet) for quality scientific summarization.
    Creates plain-language summaries suitable for content inspiration.
    """

    SUMMARIZATION_PROMPT = '''You are a scientific research summarizer for a health food company.

Analyze this PubMed abstract and extract key information:

TITLE: {title}
STUDY TYPE: {study_type}
ABSTRACT: {abstract}

Extract and summarize:
1. COMPOUND STUDIED: The main substance/ingredient studied (include scientific name if present)
2. EFFECT MEASURED: What health/wellness effect was being investigated
3. KEY FINDINGS: 2-3 sentence plain-language summary of results (suitable for general audience)
4. STATISTICAL SIGNIFICANCE: If mentioned, note p-values, confidence intervals, sample size
5. STUDY STRENGTH: Rate as "strong" (RCT, large sample), "moderate" (smaller RCT), or "weak" (review, observational)
6. CONTENT POTENTIAL: Tag as one or more of:
   - "educational": Can discuss the science generally
   - "citation_worthy": Worth citing with DOI link
   - "trend_indicator": Shows research direction in the field

CRITICAL: This is for content inspiration only. All summaries must include this caveat:
"Research finding - not an approved health claim. Can cite study but cannot claim treatment/prevention/cure."

Respond in JSON format:
{{
    "compound_studied": "...",
    "effect_measured": "...",
    "key_findings": "...",
    "statistical_significance": "...",
    "study_strength": "...",
    "content_potential": ["..."],
    "caveat": "Research finding - not an approved health claim..."
}}'''

    def __init__(self, llm_client: LLMClient):
        """Accept LLM client via injection from Team Builder."""
        self._llm = llm_client

    async def summarize(
        self,
        title: str,
        abstract: str,
        study_type: str
    ) -> FindingSummary:
        """Generate plain-language summary of research finding.

        Args:
            title: Article title
            abstract: Full abstract text
            study_type: Type of study (RCT, Meta-Analysis, Review, etc.)

        Returns:
            FindingSummary with extracted information
        """
        prompt = self.SUMMARIZATION_PROMPT.format(
            title=title,
            study_type=study_type,
            abstract=abstract[:4000]  # Truncate very long abstracts
        )

        response = await self._llm.generate(
            prompt=prompt,
            response_format="json"
        )

        # Parse response
        data = json.loads(response)

        return FindingSummary(
            compound_studied=data.get("compound_studied", "Unknown compound"),
            effect_measured=data.get("effect_measured", "Unknown effect"),
            key_findings=data.get("key_findings", ""),
            statistical_significance=data.get("statistical_significance"),
            study_strength=data.get("study_strength", "weak"),
            content_potential=data.get("content_potential", ["educational"]),
            caveat=data.get("caveat", "Research finding - not an approved health claim."),
        )
```

### Claim Validator (LLM Stage)

**Source:** [prd.md#EU-Health-Claims], [epic-2-prep.md]

```python
# claim_validator.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ContentPotential(Enum):
    """Content usage categories for research findings."""
    CITATION_ONLY = "citation_only"      # Can cite with DOI, no claims
    EDUCATIONAL = "educational"          # Can discuss science generally
    TREND_AWARENESS = "trend_awareness"  # Indicates research direction
    NO_CLAIM = "no_claim"               # Cannot use for marketing

@dataclass
class ClaimValidationResult:
    """Result from claim validation against EU rules."""
    content_potential: list[ContentPotential]
    usage_guidance: str
    eu_claim_status: str  # "no_approved_claim", "pending", "approved"
    caveat: str
    can_cite_study: bool
    can_make_claim: bool

class ClaimValidator:
    """Validates research findings against EU Health Claims context.

    Uses tier="generate" (Sonnet) for accurate claim assessment.
    Cross-references findings with EU compliance rules.
    """

    VALIDATION_PROMPT = '''You are an EU Health Claims compliance expert.

Given this research finding summary, determine how it can be used for content marketing under EU Health Claims Regulation (EC 1924/2006):

COMPOUND: {compound}
EFFECT: {effect}
SUMMARY: {summary}
STUDY STRENGTH: {strength}

CRITICAL CONTEXT: There are currently ZERO approved EU health claims for functional mushrooms (Lion's Mane, Chaga, Reishi, Cordyceps, etc.). Any content using these findings CANNOT make health claims.

Determine:
1. CONTENT POTENTIAL: How can this research be used?
   - "citation_only": Can cite the study with DOI link in educational content
   - "educational": Can discuss the science/research direction without claims
   - "trend_awareness": Useful for understanding market/research trends
   - "no_claim": Cannot be used for any marketing claims

2. USAGE GUIDANCE: Specific guidance on how to use this research compliantly

3. EU CLAIM STATUS: Current status for this type of claim
   - "no_approved_claim": No approved claim exists
   - "pending": Claim under review (rare)
   - "approved": Claim is approved (unlikely for mushrooms)

Respond in JSON format:
{{
    "content_potential": ["citation_only", "educational"],
    "usage_guidance": "Can cite this study when discussing research directions...",
    "eu_claim_status": "no_approved_claim",
    "caveat": "Can cite study but NOT claim treatment/prevention/cure",
    "can_cite_study": true,
    "can_make_claim": false
}}'''

    def __init__(
        self,
        llm_client: LLMClient,
        compliance_checker: EUComplianceChecker
    ):
        """Accept dependencies via injection from Team Builder."""
        self._llm = llm_client
        self._compliance = compliance_checker

    async def validate_claim_potential(
        self,
        summary: FindingSummary
    ) -> ClaimValidationResult:
        """Validate research finding against EU Health Claims context.

        Args:
            summary: Summarized research finding

        Returns:
            ClaimValidationResult with usage guidance
        """
        prompt = self.VALIDATION_PROMPT.format(
            compound=summary.compound_studied,
            effect=summary.effect_measured,
            summary=summary.key_findings,
            strength=summary.study_strength,
        )

        response = await self._llm.generate(
            prompt=prompt,
            response_format="json"
        )

        data = json.loads(response)

        # Map string to enum
        potential_tags = [
            ContentPotential(p) for p in data.get("content_potential", ["no_claim"])
        ]

        return ClaimValidationResult(
            content_potential=potential_tags,
            usage_guidance=data.get("usage_guidance", "Cannot use for marketing claims."),
            eu_claim_status=data.get("eu_claim_status", "no_approved_claim"),
            caveat=data.get("caveat", "Can cite study but NOT claim treatment/prevention/cure"),
            can_cite_study=data.get("can_cite_study", True),
            can_make_claim=data.get("can_make_claim", False),
        )
```

### Configuration Schema

**Source:** [project-context.md#Configuration-Loading], [epic-2-prep.md#PubMed-Entrez-API]

```python
# config.py
from dataclasses import dataclass, field
from typing import Optional

# Constants
DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_MAX_RESULTS_PER_QUERY = 50
DEFAULT_BATCH_SIZE = 200

@dataclass
class PubMedScannerConfig:
    """Scanner configuration - loaded from config file via injection."""
    email: str  # Required by NCBI policy
    api_key: Optional[str] = None  # Optional, increases rate limit
    search_queries: list[str] = field(default_factory=lambda: [
        "lion's mane cognition",
        "chaga antioxidant",
        "reishi immune",
        "cordyceps performance",
        "Hericium erinaceus",
        "Inonotus obliquus",
        "adaptogen stress",
        "functional mushroom",
    ])
    publication_type_filters: list[str] = field(default_factory=lambda: [
        "Randomized Controlled Trial",
        "Meta-Analysis",
        "Review",
    ])
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    max_results_per_query: int = DEFAULT_MAX_RESULTS_PER_QUERY
```

**config/dawo_pubmed_scanner.json:**
```json
{
  "email": "${PUBMED_EMAIL}",
  "api_key": "${PUBMED_API_KEY}",
  "search_queries": [
    "lion's mane cognition",
    "lion's mane memory",
    "chaga antioxidant",
    "chaga immune",
    "reishi immune",
    "reishi sleep",
    "cordyceps performance",
    "cordyceps energy",
    "Hericium erinaceus",
    "Inonotus obliquus",
    "Ganoderma lucidum",
    "adaptogen stress",
    "functional mushroom supplement"
  ],
  "publication_type_filters": [
    "Randomized Controlled Trial",
    "Meta-Analysis",
    "Review",
    "Systematic Review"
  ],
  "lookback_days": 90,
  "max_results_per_query": 50,
  "schedule": {
    "cron": "0 4 * * 0",
    "timezone": "Europe/Oslo"
  }
}
```

### Integration with Existing Components

**Source:** [2-1-research-pool-database-storage.md], [2-2-research-item-scoring-engine.md], [1-2-eu-compliance-checker-validator.md]

**Story 2.1 - Research Pool:**
```python
from teams.dawo.research import (
    ResearchItem,
    ResearchSource,
    ComplianceStatus,
    ResearchPublisher,
    TransformedResearch
)
```

**Story 2.2 - Scoring Engine:**
```python
from teams.dawo.research.scoring import (
    ResearchItemScorer,
    ScoringResult
)
```

**Story 1.2 - EU Compliance Checker:**
```python
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ComplianceResult
)
```

**Story 1.5 - Retry Middleware:**
```python
from teams.dawo.middleware.retry import (
    RetryMiddleware,
    with_retry,
    RetryConfig
)
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment], [project-context.md#Code-Review-Checklist]

**PubMed Scanner has TWO LLM stages:**
- `FindingSummarizer` → `tier="generate"` (Sonnet for quality summarization)
- `ClaimValidator` → `tier="generate"` (Sonnet for accurate compliance assessment)

All other stages use `tier="scan"` (rule-based or no LLM needed).

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus`
- `claude-haiku`, `claude-sonnet`, `claude-opus`
- Any hardcoded model IDs

**REQUIRED:**
```python
# team_spec.py
RegisteredAgent(
    name="pubmed_scanner",
    agent_class=PubMedScanner,
    capabilities=["pubmed_research", "research_scanning", "scientific_research"],
    tier=TIER_SCAN
)
RegisteredAgent(
    name="finding_summarizer",
    agent_class=FindingSummarizer,
    capabilities=["pubmed_research", "finding_summarization", "scientific_summarization"],
    tier=TIER_GENERATE  # Uses Sonnet for quality summarization
)
RegisteredAgent(
    name="claim_validator",
    agent_class=ClaimValidator,
    capabilities=["pubmed_research", "claim_validation", "eu_compliance_assessment"],
    tier=TIER_GENERATE  # Uses Sonnet for accurate compliance assessment
)
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [2-3-reddit-research-scanner.md], [2-4-youtube-research-scanner.md], [2-5-instagram-trend-scanner.md], [2-6-industry-news-scanner.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | ALL components accept config via constructor |
| Use tier terminology ONLY | `tier="scan"` or `tier="generate"` - NEVER model names |
| datetime deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| SQLAlchemy reserved word fix | Use `source_metadata` not `metadata` |
| Add logging to exception handlers | All exceptions logged before re-raising |
| Extract magic numbers to constants | `LOOKBACK_DAYS = 90`, `MAX_RESULTS_PER_QUERY = 50`, etc. |
| TDD approach | Write tests first for each task |
| Unit tests with mocking | Mock Entrez API responses for all tests |
| Mock patterns: async vs sync | Entrez is sync - use `run_in_executor` and mock appropriately |
| Pipeline return value handling | Track batch vs individual publish counts |
| Graceful degradation | Return INCOMPLETE on API failure, PARTIAL on item failures |
| Integration tests separate | Create test_integration.py with conftest.py fixtures |
| Track partial success | Track which queries succeeded/failed separately |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns], [architecture.md#Anti-Patterns]

1. **NEVER load config directly** - Accept via injection
2. **NEVER make direct API calls without retry wrapper**
3. **NEVER use LLM model names** - Use tier system
4. **NEVER swallow exceptions without logging**
5. **NEVER assume all queries succeed** - Handle partial failures
6. **NEVER make health claims based on research** - Citation only

### Sample Size Extraction

**Implementation detail for Task 4.7:**

```python
import re

SAMPLE_SIZE_PATTERNS = [
    r'n\s*=\s*(\d+)',                    # n=77, n = 100
    r'(\d+)\s*participants',              # 77 participants
    r'(\d+)\s*subjects',                  # 50 subjects
    r'(\d+)\s*patients',                  # 120 patients
    r'(\d+)\s*individuals',               # 45 individuals
    r'sample\s*(?:size|of)\s*(\d+)',     # sample size 77, sample of 100
]

def extract_sample_size(abstract: str) -> Optional[int]:
    """Extract sample size from abstract text."""
    for pattern in SAMPLE_SIZE_PATTERNS:
        match = re.search(pattern, abstract, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    return None
```

### Exports Template (MUST FOLLOW)

**Source:** [project-context.md#Module-Exports]

```python
# teams/dawo/scanners/pubmed/__init__.py
"""PubMed Scientific Research Scanner for DAWO research intelligence pipeline."""

from .agent import PubMedScanner, PubMedScanError
from .tools import (
    PubMedClient,
    EntrezConfig,
    PubMedSearchError,
    PubMedFetchError,
)
from .config import (
    PubMedScannerConfig,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MAX_RESULTS_PER_QUERY,
    DEFAULT_BATCH_SIZE,
)
from .schemas import (
    RawPubMedArticle,
    HarvestedArticle,
    FindingSummary,
    ClaimValidationResult,
    ContentPotential,
    ValidatedResearch,
    PipelineStatus,
    PipelineResult,
    ScanResult,
)
from .harvester import PubMedHarvester, HarvesterError
from .finding_summarizer import FindingSummarizer
from .claim_validator import ClaimValidator
from .transformer import PubMedTransformer, TransformerError
from .validator import PubMedValidator, ValidatorError
from .pipeline import PubMedResearchPipeline, PipelineError

__all__ = [
    # Main agent
    "PubMedScanner",
    # Client
    "PubMedClient",
    "EntrezConfig",
    # Config
    "PubMedScannerConfig",
    "DEFAULT_LOOKBACK_DAYS",
    "DEFAULT_MAX_RESULTS_PER_QUERY",
    "DEFAULT_BATCH_SIZE",
    # Schemas
    "RawPubMedArticle",
    "HarvestedArticle",
    "FindingSummary",
    "ClaimValidationResult",
    "ContentPotential",
    "ValidatedResearch",
    "PipelineStatus",
    "PipelineResult",
    "ScanResult",
    # Exceptions
    "PubMedScanError",
    "PubMedSearchError",
    "PubMedFetchError",
    "HarvesterError",
    "TransformerError",
    "ValidatorError",
    "PipelineError",
    # Pipeline stages
    "PubMedHarvester",
    "FindingSummarizer",
    "ClaimValidator",
    "PubMedTransformer",
    "PubMedValidator",
    "PubMedResearchPipeline",
]
```

### Test Fixtures

**Source:** [2-5-instagram-trend-scanner.md#Test-Fixtures], [2-6-industry-news-scanner.md#Test-Fixtures]

```python
# tests/teams/dawo/test_scanners/test_pubmed/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

@pytest.fixture
def mock_entrez_search_response():
    """Mock Entrez esearch response."""
    return {
        "IdList": ["12345678", "87654321", "11111111"],
        "Count": "3",
        "RetMax": "50",
    }

@pytest.fixture
def mock_pubmed_article():
    """Mock parsed PubMed article."""
    return {
        "pmid": "12345678",
        "title": "Effects of Hericium erinaceus on Cognitive Function: A Randomized Controlled Trial",
        "abstract": "Background: Lion's mane (Hericium erinaceus) has been studied for cognitive benefits. Methods: 77 participants were randomized to receive lion's mane extract (n=39) or placebo (n=38) for 12 weeks. Results: The treatment group showed significant improvement in cognitive function scores (p<0.05). Conclusion: Lion's mane supplementation may support cognitive function.",
        "authors": ["Mori K", "Inatomi S", "Ouchi K"],
        "journal": "Phytotherapy Research",
        "pub_date": datetime.now(timezone.utc) - timedelta(days=30),
        "doi": "10.1002/ptr.12345",
        "publication_types": ["Randomized Controlled Trial"],
    }

@pytest.fixture
def mock_finding_summary():
    """Mock FindingSummary for testing."""
    return FindingSummary(
        compound_studied="Lion's mane extract (Hericium erinaceus)",
        effect_measured="cognitive function improvement",
        key_findings="A 12-week RCT with 77 participants found significant cognitive improvements in the lion's mane group compared to placebo.",
        statistical_significance="p<0.05, n=77",
        study_strength="strong",
        content_potential=["educational", "citation_worthy"],
        caveat="Research finding - not an approved health claim.",
    )

@pytest.fixture
def mock_pubmed_client(mock_entrez_search_response, mock_pubmed_article):
    """Mock PubMedClient for testing without API calls."""
    client = AsyncMock(spec=PubMedClient)
    client.search.return_value = mock_entrez_search_response["IdList"]
    client.fetch_details.return_value = [mock_pubmed_article]
    return client

@pytest.fixture
def scanner_config():
    """Test scanner configuration."""
    return PubMedScannerConfig(
        email="test@example.com",
        api_key="test_api_key",
        search_queries=["lion's mane cognition", "Hericium erinaceus"],
        publication_type_filters=["Randomized Controlled Trial"],
        lookback_days=90,
        max_results_per_query=10,
    )
```

### Project Structure Notes

- **Fifth scanner**: Follows pattern established by Reddit (2.3), YouTube (2.4), Instagram (2.5), News (2.6)
- **Two LLM stages**: FindingSummarizer AND ClaimValidator (both tier="generate")
- **Weekly schedule**: Sunday 4 AM (scientific publications have slower cadence)
- **High-value content**: Peer-reviewed studies get score boost
- **Biopython dependency**: Uses Entrez module instead of REST client
- **Claim validation**: Cross-references findings with EU Health Claims context
- **Scientific metadata**: DOI, study type, sample size, authors extracted
- **Follows Harvester Framework**: scan -> harvest -> summarize -> validate_claims -> transform -> validate -> publish
- **Integrates with**: Research Pool (2.1), Scoring Engine (2.2), EU Compliance (1.2), Retry Middleware (1.5)

### References

- [Source: epics.md#Story-2.7] - Original story requirements (see epic-2-prep.md)
- [Source: epic-2-prep.md#PubMed-Entrez-API] - API details and config
- [Source: prd.md#PubMed-Research-Team] - PRD requirements
- [Source: architecture.md#Harvester-Framework] - Pipeline pattern
- [Source: project-context.md#External-API-Calls] - Retry middleware requirement
- [Source: project-context.md#LLM-Tier-Assignment] - Tier terminology
- [Source: 2-1-research-pool-database-storage.md] - Research Pool integration
- [Source: 2-2-research-item-scoring-engine.md] - Scoring integration
- [Source: 2-4-youtube-research-scanner.md] - Pattern reference (LLM stage pattern)
- [Source: 2-5-instagram-trend-scanner.md] - Pattern reference (dual LLM stages)
- [Source: 2-6-industry-news-scanner.md] - Pattern reference (latest learnings)
- [Source: 1-2-eu-compliance-checker-validator.md] - Compliance integration
- [Source: 1-5-external-api-retry-middleware.md] - Retry middleware integration

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

None

### Completion Notes List

- All 15 tasks completed successfully
- 194 unit tests pass across all modules
- Fixed sample size extraction to handle comma-separated numbers (1,847 -> 1847)
- Two LLM stages (FindingSummarizer, ClaimValidator) both use tier="generate"
- Follows established Harvester Framework pattern from Stories 2.3-2.6
- Components registered in team_spec.py: 3 agents, 5 services
- Configuration file created with search queries, publication type filters, and weekly schedule

### File List

**Implementation Files:**
- teams/dawo/scanners/pubmed/__init__.py - Module exports
- teams/dawo/scanners/pubmed/agent.py - PubMedScanner main class
- teams/dawo/scanners/pubmed/tools.py - PubMedClient with Entrez API
- teams/dawo/scanners/pubmed/config.py - PubMedScannerConfig, EntrezConfig
- teams/dawo/scanners/pubmed/schemas.py - All data structures
- teams/dawo/scanners/pubmed/prompts.py - LLM prompts and patterns
- teams/dawo/scanners/pubmed/harvester.py - PubMedHarvester
- teams/dawo/scanners/pubmed/finding_summarizer.py - FindingSummarizer (LLM)
- teams/dawo/scanners/pubmed/claim_validator.py - ClaimValidator (LLM)
- teams/dawo/scanners/pubmed/transformer.py - PubMedTransformer
- teams/dawo/scanners/pubmed/validator.py - PubMedValidator
- teams/dawo/scanners/pubmed/pipeline.py - PubMedResearchPipeline
- teams/dawo/team_spec.py - Updated with PubMed registrations
- config/dawo_pubmed_scanner.json - Scanner configuration

**Test Files:**
- tests/teams/dawo/test_scanners/test_pubmed/__init__.py
- tests/teams/dawo/test_scanners/test_pubmed/conftest.py - Fixtures
- tests/teams/dawo/test_scanners/test_pubmed/test_schemas.py - 45 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_config.py
- tests/teams/dawo/test_scanners/test_pubmed/test_client.py - 20 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_scanner.py - 13 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_harvester.py - 24 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_finding_summarizer.py - 16 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_claim_validator.py - 22 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_transformer.py - 24 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_validator.py - 16 tests
- tests/teams/dawo/test_scanners/test_pubmed/test_pipeline.py - 14 tests

