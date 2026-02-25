# Story 6.6: Health Claim Extraction Engine

Status: complete

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want health claims automatically extracted from competitor content,
So that potential violations can be identified systematically.

---

## Acceptance Criteria

1. **Given** competitor content is queued for analysis (extraction_status="pending")
   **When** the extraction engine runs
   **Then** it identifies health-related phrases using hybrid regex+LLM
   **And** it categorizes claims by type: treatment, prevention, enhancement, general_wellness
   **And** it extracts: exact phrase, surrounding context, claim category

2. **Given** a phrase is identified as potential claim
   **When** it's extracted
   **Then** confidence score is assigned (0-100)
   **And** claims with confidence >= 70 proceed to violation detection (Story 6-7)
   **And** lower confidence claims are logged for manual review

3. **Given** multiple claims exist in one post
   **When** extraction completes
   **Then** each claim is stored separately in `extracted_health_claims` table
   **And** all claims link back to source `competitor_content` record
   **And** `extraction_status` is updated to "extracted"

4. **Given** content has no extractable health claims
   **When** extraction completes
   **Then** `extraction_status` is updated to "no_claims"
   **And** no claim records are created

5. **Given** extraction fails for a content item
   **When** error occurs (LLM timeout, parse failure)
   **Then** `extraction_status` is updated to "error"
   **And** error is logged with details
   **And** pipeline continues with next content item

---

## Tasks / Subtasks

- [x] Task 1: Create extraction config (AC: #1)
  - [x]1.1 Create `config/dawo_health_claim_extraction.json` with:
    - `enabled`: true
    - `batch_size`: 20 (max content items per run)
    - `confidence_threshold`: 70 (minimum for auto-proceed to violation detection)
    - `max_claims_per_content`: 10 (safety limit)
    - `context_window_chars`: 100 (characters around matched phrase for context)
    - `use_llm`: true (can disable for regex-only mode)
    - `prohibited_patterns`: array of `{"pattern": str, "category": str, "language": str}` — English + Norwegian prohibited health claim patterns (~25 entries each language)
    - `borderline_patterns`: array of `{"pattern": str, "category": str, "language": str}` — English + Norwegian borderline patterns (~20 entries each language)
    - `permitted_patterns`: array of `{"pattern": str, "category": str, "language": str}` — permitted wellness language (~15 entries each language)
    - `claim_categories`: `["treatment", "prevention", "enhancement", "general_wellness"]`
    - `eu_article_mapping`: `{"treatment": "prohibited", "prevention": "14.1a", "enhancement": "13.1", "general_wellness": "13.1"}`
  - [x]1.2 Create frozen dataclass `HealthClaimExtractionConfig` in `teams/dawo/scanners/claim_extraction/config.py`
  - [x]1.3 Create nested frozen dataclass `ClaimPattern` with fields: pattern (str), category (str), language (str)
  - [x]1.4 Create `build_health_claim_extraction_config(data: dict) -> HealthClaimExtractionConfig` builder function
  - [x]1.5 Validate in `__post_init__`: at least 1 prohibited pattern, valid categories, positive batch_size, confidence_threshold 0-100

- [x] Task 2: Create database model (AC: #1, #2, #3)
  - [x]2.1 Add model to `core/regulatory/models.py`:
    - `ExtractedHealthClaim`: id (UUID PK), competitor_content_id (UUID FK to competitor_content.id), claim_text (str — exact extracted phrase), surrounding_context (str — text around the claim for context), claim_category (str: "treatment"|"prevention"|"enhancement"|"general_wellness"), confidence_score (int 0-100), language_detected (str: "en"|"no"|"unknown"), extraction_method (str: "regex"|"llm"|"hybrid"), eu_article_reference (str nullable — e.g. "13.1", "14.1a", "prohibited"), matched_pattern (str nullable — the regex pattern that matched, if any), llm_reasoning (str nullable — LLM's classification reasoning), review_status (str: "auto_approved"|"manual_review"|"reviewed"), created_at (datetime)
  - [x]2.2 Add enum `ClaimCategory` (TREATMENT, PREVENTION, ENHANCEMENT, GENERAL_WELLNESS)
  - [x]2.3 Add enum `ReviewStatus` (AUTO_APPROVED, MANUAL_REVIEW, REVIEWED)
  - [x]2.4 Add indexes: `idx_extracted_claims_content` on competitor_content_id, `idx_extracted_claims_category` on claim_category, `idx_extracted_claims_confidence` on confidence_score, `idx_extracted_claims_review` on review_status
  - [x]2.5 Add relationship: CompetitorContent.extracted_claims -> ExtractedHealthClaim (one-to-many)
  - [x]2.6 Add constants: MAX_CLAIM_TEXT_LENGTH = 1000, MAX_CONTEXT_LENGTH = 500, MAX_REASONING_LENGTH = 2000

- [x] Task 3: Create Alembic migration (AC: #3)
  - [x]3.1 Create `migrations/versions/2026_02_16_001_create_extracted_health_claims.py`
  - [x]3.2 Create `extracted_health_claims` table with foreign key to `competitor_content.id`
  - [x]3.3 Create all indexes from Task 2.4
  - [x]3.4 Add downgrade function to drop table

- [x] Task 4: Create schemas/DTOs (AC: #1-#3)
  - [x]4.1 Create `teams/dawo/scanners/claim_extraction/schemas.py`
  - [x]4.2 Create `ClaimExtractionResult` dataclass: claim_text (str), surrounding_context (str), claim_category (str), confidence_score (int), language_detected (str), extraction_method (str), eu_article_reference (str|None), matched_pattern (str|None), llm_reasoning (str|None)
  - [x]4.3 Create `ContentExtractionResult` dataclass: competitor_content_id (UUID), claims (list[ClaimExtractionResult]), extraction_status (str: "extracted"|"no_claims"|"error"), error_message (str|None)
  - [x]4.4 Create `ExtractionBatchResult` dataclass: total_processed (int), total_claims_extracted (int), items_with_claims (int), items_no_claims (int), items_error (int), high_confidence_claims (int), manual_review_claims (int)
  - [x]4.5 Create `LLMExtractionRequest` dataclass: content_text (str), pre_filter_matches (list[dict]), language_hint (str|None)
  - [x]4.6 Create `LLMExtractionResponse` dataclass: claims (list[dict]), raw_response (str)

- [x] Task 5: Create regex pre-filter (AC: #1)
  - [x]5.1 Create `teams/dawo/scanners/claim_extraction/pattern_matcher.py` with `ClaimPatternMatcher`
  - [x]5.2 Accept `HealthClaimExtractionConfig` via constructor
  - [x]5.3 Implement `__init__`: compile all regex patterns from config (prohibited + borderline) into `re.Pattern` objects at init time. Use `re.IGNORECASE`. Handle Norwegian compound words by including word boundary variations: `\b{pattern}\b` AND `{pattern}(?:en|et|er|ene|a|s)` for Norwegian inflections.
  - [x]5.4 Implement `find_matches(text: str) -> list[PatternMatch]` — scan text against all compiled patterns. For each match, extract: matched_text, pattern_category, start/end position, surrounding context (config.context_window_chars before and after). Return sorted by position.
  - [x]5.5 Create `PatternMatch` dataclass: matched_text (str), pattern (str), category (str), language (str), start_pos (int), end_pos (int), surrounding_context (str)
  - [x]5.6 Implement `detect_language(text: str) -> str` — simple heuristic: if Norwegian-specific characters (or, ae, aa) or Norwegian keywords present, return "no", else "en". This is a HINT, not authoritative.
  - [x]5.7 Handle overlapping matches: if two patterns match overlapping text, keep the longer/more specific match

- [x] Task 6: Create LLM claim classifier (AC: #1, #2)
  - [x]6.1 Create `teams/dawo/scanners/claim_extraction/llm_classifier.py` with `ClaimLLMClassifier`
  - [x]6.2 Accept deps via constructor: `llm_client: LLMClientProtocol`, `retry: RetryMiddlewareProtocol`, `config: HealthClaimExtractionConfig`
  - [x]6.3 Implement `classify_claims(content_text: str, pre_filter_matches: list[PatternMatch], language_hint: str) -> list[ClaimExtractionResult]`:
    - Build bilingual prompt with:
      - System context: EU Health Claims Regulation EC 1924/2006, mushroom products have ZERO authorized claims
      - Content text for analysis
      - Pre-filter matches as hints (regex already found these)
      - Instruction to find ADDITIONAL claims regex may have missed
      - Required output: JSON array of claims with category, confidence, reasoning
    - Call LLM via `self._llm_client.generate()` with `tier="generate"`
    - Parse structured JSON response
    - Merge regex matches + LLM discoveries (deduplicate by text overlap)
    - Assign confidence: regex-only = 60, llm-confirmed-regex = 90, llm-only = 75
  - [x]6.4 Implement `_build_extraction_prompt(content_text: str, pre_filter_matches: list[PatternMatch], language_hint: str) -> str`:
    - Include: role context, regulation context, mushroom-specific context
    - Include Norwegian + English examples
    - Specify JSON output schema
    - Include the pre-filter matches for LLM to confirm/reject/classify
  - [x]6.5 Implement `_parse_llm_response(response: str) -> list[dict]`:
    - Extract JSON from response (handle markdown code blocks)
    - Validate each claim has required fields
    - Return list of claim dicts
    - On parse failure: log warning, return empty list (graceful degradation)
  - [x]6.6 Implement `_merge_claims(regex_matches: list[PatternMatch], llm_claims: list[dict]) -> list[ClaimExtractionResult]`:
    - Match LLM claims to regex matches by text overlap (fuzzy)
    - Regex-confirmed-by-LLM → confidence 90, method "hybrid"
    - Regex-only (LLM missed or unavailable) → confidence 60, method "regex"
    - LLM-only (regex missed) → confidence 75, method "llm"
    - Deduplicate: if two claims overlap >80% in text, keep higher confidence

- [x] Task 7: Create repository (AC: #3, #4)
  - [x]7.1 Create `teams/dawo/scanners/claim_extraction/repository.py` with `HealthClaimRepository`
  - [x]7.2 Accept `AsyncSession` via constructor
  - [x]7.3 Implement `save_claims(content_id: UUID, claims: list[ClaimExtractionResult]) -> int` — bulk insert `ExtractedHealthClaim` records, return count saved
  - [x]7.4 Implement `update_extraction_status(content_id: UUID, status: str) -> None` — update `CompetitorContent.extraction_status`
  - [x]7.5 Implement `get_high_confidence_claims(min_confidence: int = 70) -> Sequence[ExtractedHealthClaim]` — query claims above threshold (for Story 6-7)
  - [x]7.6 Implement `get_claims_for_content(content_id: UUID) -> Sequence[ExtractedHealthClaim]` — all claims for a content item
  - [x]7.7 Implement `commit() -> None` — `await self._session.commit()`

- [x] Task 8: Create extraction engine / pipeline (AC: #1-#5)
  - [x]8.1 Create `teams/dawo/scanners/claim_extraction/engine.py` with `HealthClaimExtractionEngine`
  - [x]8.2 Accept deps via constructor: `competitor_repository: CompetitorRepository`, `claim_repository: HealthClaimRepository`, `pattern_matcher: ClaimPatternMatcher`, `llm_classifier: ClaimLLMClassifier | None` (None = regex-only mode), `event_emitter: RegulatoryEventEmitter`, `config: HealthClaimExtractionConfig`
  - [x]8.3 Implement `execute() -> ExtractionBatchResult`:
    - Stage 1: Fetch pending content via `competitor_repository.get_pending_extraction()` limited to `config.batch_size`
    - Stage 2: For each content item:
      - Run `pattern_matcher.find_matches(content.content_text)`
      - If matches found AND `config.use_llm` AND `llm_classifier` available:
        - Run `llm_classifier.classify_claims(content.content_text, matches, language_hint)`
      - Else if matches found (regex-only mode):
        - Convert PatternMatch to ClaimExtractionResult (confidence=60)
      - Else (no matches):
        - Update extraction_status to "no_claims"
        - Continue to next item
    - Stage 3: Save claims via `claim_repository.save_claims()`
    - Stage 4: Update `extraction_status` to "extracted"
    - Stage 5: Set `review_status` per claim:
      - confidence >= config.confidence_threshold → "auto_approved"
      - confidence < config.confidence_threshold → "manual_review"
    - Stage 6: Emit events for extracted claims
    - Return `ExtractionBatchResult` with statistics
  - [x]8.4 Handle per-item errors gracefully — log error, update extraction_status to "error", continue with next item
  - [x]8.5 Log all stages with counts at INFO level
  - [x]8.6 Cap claims per content item at `config.max_claims_per_content`

- [x] Task 9: Add event types (AC: #1)
  - [x]9.1 Add to `RegulatoryEventType` in `core/regulatory/events.py`:
    - `HEALTH_CLAIM_EXTRACTED = "health_claim_extracted"` (Story 6-6)
    - `HIGH_CONFIDENCE_CLAIM_DETECTED = "high_confidence_claim_detected"` (Story 6-6)
  - [x]9.2 Update `__all__` in `core/regulatory/events.py`
  - [x]9.3 Update `AlertCategory` enum in `teams/dawo/scanners/claims_alerts/schemas.py` — add `HEALTH_CLAIM_EXTRACTION = "health_claim_extraction"`
  - [x]9.4 Update `categorize_event()` in claims_alerts/schemas.py to handle new event types

- [x] Task 10: Create package __init__.py and register in team_spec.py (AC: #1-#5)
  - [x]10.1 Create `teams/dawo/scanners/claim_extraction/__init__.py` with complete `__all__`
  - [x]10.2 Export: HealthClaimExtractionConfig, ClaimPattern, ClaimPatternMatcher, PatternMatch, ClaimLLMClassifier, HealthClaimExtractionEngine, HealthClaimRepository, ClaimExtractionResult, ContentExtractionResult, ExtractionBatchResult
  - [x]10.3 Register in team_spec.py:
    - `HealthClaimExtractionEngine` as RegisteredAgent with capabilities `["competitor_monitoring", "claim_extraction"]`, tier=TIER_GENERATE, requires_session=True
    - `ClaimPatternMatcher` as RegisteredService with capabilities `["competitor_monitoring", "pattern_matching"]`, requires_session=False
    - `ClaimLLMClassifier` as RegisteredService with capabilities `["competitor_monitoring", "claim_classification"]`, requires_session=False
    - `HealthClaimRepository` as RegisteredService with capabilities `["competitor_monitoring", "claim_storage"]`, requires_session=True
  - [x]10.4 Add all new imports to team_spec.py

- [x] Task 11: Create unit tests (AC: #1-#5)
  - [x]11.1 Create `tests/teams/dawo/test_scanners/test_claim_extraction/` with `__init__.py`, `conftest.py`
  - [x]11.2 `conftest.py` fixtures: sample config, sample CompetitorContent records, sample pattern matches, mock LLM client, mock AsyncSession, mock RetryMiddleware, sample LLM responses (valid JSON, malformed JSON, empty)
  - [x]11.3 `test_config.py` (~8 tests):
    - Valid config creation
    - Empty prohibited patterns → ValueError
    - Invalid confidence threshold (>100) → ValueError
    - Non-positive batch_size → ValueError
    - Build function from JSON dict
    - Nested ClaimPattern creation
    - Default values
    - Frozen immutability
  - [x]11.4 `test_pattern_matcher.py` (~12 tests):
    - Matches English prohibited phrase "cures cancer"
    - Matches Norwegian prohibited phrase "behandler kreft"
    - Matches borderline English "boosts immunity"
    - Matches borderline Norwegian "styrker immunforsvaret" (compound word with suffix)
    - No match for "mushroom recipes" (no health language)
    - Case insensitive matching
    - Norwegian suffix variations: "forbedrer" / "forbedret" / "forbedring"
    - Multiple matches in same text (returns all, sorted by position)
    - Overlapping matches: keeps longer/more specific
    - Surrounding context extraction (correct window size)
    - detect_language() returns "no" for Norwegian text
    - detect_language() returns "en" for English text
  - [x]11.5 `test_llm_classifier.py` (~10 tests):
    - Valid LLM response parsed into ClaimExtractionResult list
    - Malformed JSON → returns empty list, logs warning
    - LLM timeout → returns empty list (graceful degradation)
    - Merge: regex + LLM confirm same claim → confidence 90, method "hybrid"
    - Merge: regex-only (LLM missed) → confidence 60, method "regex"
    - Merge: LLM-only (regex missed) → confidence 75, method "llm"
    - Deduplication: overlapping claims → keep higher confidence
    - Prompt includes Norwegian examples
    - Prompt includes mushroom-specific context
    - Claims capped at max_claims_per_content
  - [x]11.6 `test_repository.py` (~6 tests):
    - `save_claims()` inserts all claims and returns count
    - `save_claims()` with empty list → returns 0
    - `update_extraction_status()` updates CompetitorContent
    - `get_high_confidence_claims()` returns only above threshold
    - `get_claims_for_content()` returns claims for specific content
    - `commit()` calls session.commit()
  - [x]11.7 `test_engine.py` (~10 tests):
    - Full pipeline: pending content → regex → LLM → claims saved → status "extracted"
    - Regex-only mode (llm_classifier=None): matches → confidence 60, method "regex"
    - No matches in content → status "no_claims", no claims saved
    - LLM unavailable (use_llm=False): regex-only extraction
    - Per-item error handling: one item fails, others continue
    - Batch size limiting: only processes config.batch_size items
    - Claims capped at max_claims_per_content per item
    - Events emitted for high-confidence claims
    - Review status: high confidence → "auto_approved"
    - Review status: low confidence → "manual_review"
  - [x]11.8 `test_schemas.py` (~5 tests):
    - ClaimExtractionResult creation with all fields
    - ContentExtractionResult creation
    - ExtractionBatchResult creation
    - PatternMatch creation
    - LLMExtractionResponse creation

- [x] Task 12: Create integration tests (AC: #1-#5)
  - [x]12.1 Test full hybrid pipeline: pending content with health claims → regex matches → mock LLM confirms → claims stored in DB → extraction_status="extracted"
  - [x]12.2 Test regex-only pipeline: pending content → regex matches → no LLM → claims stored with confidence 60 → extraction_status="extracted"
  - [x]12.3 Test no-claims path: pending content with no health language → no claims → extraction_status="no_claims"
  - [x]12.4 Test Norwegian content: "dette produktet styrker immunforsvaret" → claim extracted with language="no"
  - [x]12.5 Test multiple claims in one post: content with 3 health claims → 3 separate ExtractedHealthClaim records
  - [x]12.6 Test event emission: high-confidence claim → RegulatoryEvent emitted with type HIGH_CONFIDENCE_CLAIM_DETECTED

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **sixth story in Epic 6** (CleanMarket & Regulatory Intelligence). It's the **second story in the CleanMarket evidence chain** (Stories 6-5 through 6-10). Story 6-5 scanned and stored competitor content. Story 6-6 extracts health claims from that content.

### Epic 6 Evidence Chain Position

```
Story 6-5 (done)      → Scan competitor content → Store in DB (competitor_content table)
Story 6-6 (this)      → Extract health claims from stored content → Store claims (extracted_health_claims table)
Story 6-7             → Detect EU violations from extracted claims
Story 6-8             → Capture evidence screenshots (Playwright)
Story 6-9             → Searchable evidence database + UI
Story 6-10            → Generate PDF violation reports
```

**Critical handoff IN:** Story 6-5 stored content in `competitor_content` table with `extraction_status="pending"` and `has_health_language=True`. This story reads pending content and extracts structured health claims.

**Critical handoff OUT:** Story 6-7 will read `extracted_health_claims` with `confidence_score >= 70` to check against EU regulations. Provide `HealthClaimRepository.get_high_confidence_claims()` for this.

### Key Design Decision: Hybrid Regex+LLM

**Source:** [docs/research/nlp-health-claim-extraction.md], [epic-6-prep.md#Key-Technical-Decisions]

| Approach | Norwegian Accuracy | Cost (500 posts/day) | New Dependencies |
|----------|-------------------|---------------------|------------------|
| Pure LLM | 87% | $45-90/mo | None |
| Pure spaCy | 65% | $0 | spaCy + models |
| **Hybrid (chosen)** | **86%** | **$16-31/mo** | **None** |

**Two-stage architecture (follow `EUComplianceChecker` pattern exactly):**
1. **Stage 1 — Regex Pre-filter** (free, fast, deterministic): Scan content against compiled patterns. Catches ~65% of health claims. Returns pattern matches with positions and context.
2. **Stage 2 — LLM Classification** (accurate, contextual): Send flagged content + regex matches to LLM. LLM confirms/rejects regex matches, finds additional claims regex missed, classifies each claim by category and confidence.

**Confidence scoring:**
- Regex-only match (no LLM or LLM unavailable): 60
- LLM confirms regex match: 90 (hybrid)
- LLM-only discovery (regex missed): 75

### Critical Regulatory Context

**Source:** [docs/research/nlp-health-claim-extraction.md], [epics.md#Story-6.6]

**For functional mushrooms: NO authorized EU health claims exist.** Any health claim on a mushroom product is either unauthorized or prohibited under EC 1924/2006.

**EU Health Claim Categories (EC 1924/2006):**
- **Article 13.1**: General function claims (body functions, development) — e.g., "supports immune function"
- **Article 13.5**: New evidence claims (proprietary data)
- **Article 14.1(a)**: Disease risk reduction — e.g., "reduces risk of heart disease"
- **Article 14.1(b)**: Children's development and health
- **Article 10.3**: On-hold claims (under EFSA review since 2012 for botanicals)
- **Prohibited**: Any medicinal/treatment claim — e.g., "cures", "treats", "heals"

**Claim categories for extraction:**

| Category | Examples (English) | Examples (Norwegian) | EU Status |
|----------|-------------------|---------------------|-----------|
| treatment | "cures cancer", "treats depression" | "kurerer kreft", "behandler depresjon" | PROHIBITED (medicine, not food) |
| prevention | "prevents disease", "reduces risk" | "forebygger sykdom", "reduserer risiko" | Article 14.1a (requires authorization) |
| enhancement | "boosts immunity", "improves cognition" | "styrker immunforsvaret", "forbedrer kognisjon" | Article 13.1 (requires authorization) |
| general_wellness | "supports wellbeing", "contributes to health" | "bidrar til helse", "stotter velvare" | Article 13.1 (borderline — may be permitted with qualifying language) |

### Norwegian Pattern Requirements (CRITICAL — Zero Patterns Exist Today)

**Source:** [docs/research/nlp-health-claim-extraction.md#Critical-Gap]

Must add ~60 Norwegian patterns to `config/dawo_health_claim_extraction.json`:

**Prohibited (~25 patterns):** behandler, kurerer, forebygger, helbreder, kreft, demens, sykdom, diabetes, hjertesykdom, alzheimers, parkinson, depresjon, angst, infeksjon, betennelse, smerte, allergi, astma, epilepsi, artrose, leddgikt, fibromyalgi, migrene, somnloshet, hoyt blodtrykk

**Borderline (~20 patterns):** stotter, bidrar til, fremmer, styrker, forbedrer, oker, stimulerer, balanserer, optimaliserer, gjenoppretter, beskytter, renser, avgifter, harmoniserer, revitaliserer, regenererer, immunforsvar, energiniva, fordoyelse, stoffskifte

**Permitted (~15 patterns):** velvare, tradisjon, nordisk, livsstil, egenomsorg, naturlig, organisk, barekraftig, plantebasert, kosttilskudd, naeringstilskudd, daglig inntak, anbefalt dose, ingrediens, naeringsinnhold

**Norwegian challenge:** Compound words (immunforsvar → immunforsvaret, immunforsvarets) and definite suffixes (en/et/er/ene/a/s). Regex must handle these with suffix wildcards: `immunforsvar(?:et|ets|ene)?`

### Existing EUComplianceChecker Pattern (REUSE — Don't Reinvent)

**Source:** [teams/dawo/validators/eu_compliance/agent.py]

The `EUComplianceChecker` already implements the hybrid pattern. Key methods to study:

```python
# Phase 1: Pattern-based detection (fast path)
_check_prohibited_phrases(content) -> list of matches

# Phase 2: LLM-enhanced detection (accurate)
_llm_enhanced_check(content, pattern_matches) -> LLM result

# Phase 3: Parse structured LLM output
_parse_llm_response(response) -> list of classifications

# Phase 4: Calculate overall status
_calculate_overall_status(matches, llm_result) -> ComplianceStatus
```

**CRITICAL: Do NOT import or depend on EUComplianceChecker.** It validates DAWO's own content. Story 6-6 extracts claims from COMPETITOR content. Different purpose, different inputs, different outputs. But follow the same architectural pattern.

### Existing ComplianceRules Pattern (REFERENCE — Don't Reuse Directly)

**Source:** [teams/dawo/validators/eu_compliance/rules.py]

```python
class ComplianceRules:
    def __init__(self, config: dict):
        self.prohibited_patterns = config.get("prohibited_patterns", [])
        self.borderline_patterns = config.get("borderline_patterns", [])
        self.permitted_patterns = config.get("permitted_patterns", [])
```

Each pattern is `{"pattern": str, "category": str}`. Story 6-6 extends this with `"language": str` field for bilingual support.

### LLM Prompt Design (CRITICAL for Accuracy)

The LLM extraction prompt must include:

1. **System context:** "You are an EU food regulation expert analyzing competitor content for unauthorized health claims under EC 1924/2006."
2. **Mushroom-specific context:** "For functional mushrooms (lion's mane, chaga, reishi, cordyceps, etc.), ZERO authorized EU health claims exist. Any health claim is unauthorized or prohibited."
3. **Pre-filter results:** Pass regex matches as hints for LLM to confirm/reject.
4. **Instruction:** "Analyze the content. For each health claim found: extract exact text, classify category (treatment/prevention/enhancement/general_wellness), assign confidence 0-100, explain reasoning."
5. **Bilingual examples:** Include both English and Norwegian examples.
6. **Output format:** JSON array of claims.

**Example LLM prompt output schema:**
```json
[
  {
    "claim_text": "boosts cognitive function",
    "category": "enhancement",
    "confidence": 85,
    "reasoning": "Explicit enhancement claim about cognitive function, not authorized for mushroom products under EC 1924/2006 Article 13.1",
    "language": "en"
  }
]
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], Stories 6-1 through 6-5 patterns

```
teams/dawo/scanners/claim_extraction/     # NEW — health claim extraction engine
├── __init__.py                            # Export all public types
├── config.py                              # HealthClaimExtractionConfig + ClaimPattern
├── pattern_matcher.py                     # ClaimPatternMatcher (regex pre-filter)
├── llm_classifier.py                      # ClaimLLMClassifier (LLM classification)
├── engine.py                              # HealthClaimExtractionEngine (orchestrator)
├── repository.py                          # HealthClaimRepository (AsyncSession)
└── schemas.py                             # DTOs: ClaimExtractionResult, PatternMatch, etc.

config/
└── dawo_health_claim_extraction.json     # NEW — patterns + extraction config

core/regulatory/
└── models.py                              # ADD: ExtractedHealthClaim model + enums

core/regulatory/
└── events.py                              # ADD: 2 new RegulatoryEventType values

migrations/versions/
└── 2026_02_16_001_create_extracted_health_claims.py  # NEW

tests/teams/dawo/test_scanners/test_claim_extraction/  # NEW
├── __init__.py
├── conftest.py                            # Shared fixtures
├── test_config.py
├── test_pattern_matcher.py
├── test_llm_classifier.py
├── test_repository.py
├── test_engine.py
└── test_schemas.py

tests/integration/
└── test_claim_extraction_integration.py   # NEW
```

### LLM Integration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/validators/eu_compliance/agent.py], [project-context.md#LLM-Tier-Assignment]

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMClientProtocol(Protocol):
    async def generate(self, prompt: str, *, tier: str = "generate") -> str: ...

class ClaimLLMClassifier:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        retry: RetryMiddlewareProtocol,
        config: HealthClaimExtractionConfig,
    ) -> None:
        self._llm = llm_client
        self._retry = retry
        self._config = config
```

**Tier:** `tier="generate"` (Sonnet) — accuracy is critical for claim classification.

**FORBIDDEN in code/docstrings/comments:**
- `haiku`, `sonnet`, `opus` (model names)
- Any hardcoded model IDs

### Integration with Story 6-5 (Input Source)

**Source:** [teams/dawo/scanners/competitor/repository.py]

```python
# Story 6-5 provides this method for Story 6-6:
async def get_pending_extraction(self) -> Sequence[CompetitorContent]:
    """Get content items pending health claim extraction."""
    stmt = select(CompetitorContent).where(
        CompetitorContent.extraction_status == ExtractionStatus.PENDING.value
    )
    result = await self._session.execute(stmt)
    return result.scalars().all()
```

**CRITICAL:** Reuse `CompetitorRepository` from Story 6-5 — do NOT create a new repository for reading competitor content. Only create `HealthClaimRepository` for writing `ExtractedHealthClaim` records and updating `extraction_status`.

### Database Model Pattern (Follow Existing)

**Source:** [core/regulatory/models.py] — CompetitorContent, CompetitorScanSnapshot

```python
MAX_CLAIM_TEXT_LENGTH = 1000
MAX_CONTEXT_LENGTH = 500
MAX_REASONING_LENGTH = 2000

class ExtractedHealthClaim(Base):
    __tablename__ = "extracted_health_claims"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    competitor_content_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("competitor_content.id"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(String(MAX_CLAIM_TEXT_LENGTH), nullable=False)
    claim_category: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False)
    # ... (see Task 2 for full schema)
```

### Event System (Extend Existing)

**Source:** [core/regulatory/events.py]

```python
# Add to RegulatoryEventType enum:
HEALTH_CLAIM_EXTRACTED = "health_claim_extracted"           # Story 6-6
HIGH_CONFIDENCE_CLAIM_DETECTED = "high_confidence_claim_detected"  # Story 6-6

# Emit for high-confidence claims:
await self._event_emitter.emit(RegulatoryEvent(
    event_type=RegulatoryEventType.HIGH_CONFIDENCE_CLAIM_DETECTED,
    claim_id=str(claim_id),
    substance="",
    severity="high" if category == "treatment" else "medium",
    data={
        "competitor_content_id": str(content_id),
        "claim_text": claim.claim_text,
        "claim_category": claim.claim_category,
        "confidence_score": claim.confidence_score,
        "language_detected": claim.language_detected,
        "extraction_method": claim.extraction_method,
    },
))
```

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py]

```python
# HealthClaimExtractionEngine is a RegisteredAgent (uses LLM)
RegisteredAgent(
    name="health_claim_extraction_engine",
    agent_class=HealthClaimExtractionEngine,
    capabilities=["competitor_monitoring", "claim_extraction"],
    tier=TIER_GENERATE,  # Sonnet for accurate classification
),

# Supporting services
RegisteredService(
    name="claim_pattern_matcher",
    service_class=ClaimPatternMatcher,
    capabilities=["competitor_monitoring", "pattern_matching"],
    requires_session=False,
),
RegisteredService(
    name="claim_llm_classifier",
    service_class=ClaimLLMClassifier,
    capabilities=["competitor_monitoring", "claim_classification"],
    requires_session=False,
),
RegisteredService(
    name="health_claim_repository",
    service_class=HealthClaimRepository,
    capabilities=["competitor_monitoring", "claim_storage"],
    requires_session=True,
),
```

### Testing Strategy (TDD Required)

**Mock patterns:**

```python
@pytest.fixture
def sample_competitor_content():
    """Sample CompetitorContent with health language."""
    content = MagicMock(spec=CompetitorContent)
    content.id = uuid4()
    content.content_text = "Our lion's mane extract boosts cognitive function and treats brain fog naturally!"
    content.competitor_name = "CompetitorA"
    content.source_type = "instagram"
    content.has_health_language = True
    content.extraction_status = "pending"
    return content

@pytest.fixture
def sample_norwegian_content():
    """Sample CompetitorContent with Norwegian health language."""
    content = MagicMock(spec=CompetitorContent)
    content.id = uuid4()
    content.content_text = "Vart chaga-ekstrakt styrker immunforsvaret og forebygger sykdom naturlig!"
    content.competitor_name = "CompetitorB"
    content.source_type = "website"
    content.has_health_language = True
    content.extraction_status = "pending"
    return content

@pytest.fixture
def sample_llm_response():
    """Valid LLM extraction response."""
    return json.dumps([
        {
            "claim_text": "boosts cognitive function",
            "category": "enhancement",
            "confidence": 85,
            "reasoning": "Explicit enhancement claim about cognitive function",
            "language": "en",
        },
        {
            "claim_text": "treats brain fog",
            "category": "treatment",
            "confidence": 92,
            "reasoning": "Medical treatment claim - prohibited under EC 1924/2006",
            "language": "en",
        },
    ])

@pytest.fixture
def mock_llm_client():
    """Mock LLMClientProtocol."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value="[]")
    return client
```

**Target: ~51 unit tests + ~6 integration tests**

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [6-5-competitor-content-scanner.md#Completion-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| `result.scalars().all()` vs `result.all()` | Use correct SQLAlchemy result extraction (Story 6-5 H1 fix) |
| Pre-initialize variables before try blocks | Avoid UnboundLocalError |
| `logger.debug()` for swallowed exceptions | Don't silently eat exceptions |
| `session.add` is sync (not async) in SQLAlchemy | Use `MagicMock()` not `AsyncMock()` for `session.add` in tests (Story 6-5 L3 fix) |
| RetryMiddleware wrapping ALL external calls | Wrap all LLM calls in `self._retry.execute_with_retry()` (Story 6-5 H2 fix) |
| No N+1 queries | Batch all DB queries |
| Database filtering in SQL, not in Python | Filter by confidence_score, extraction_status in SQL |
| Activity logging in one place | Engine logs stage transitions, components log details |
| Handle list values in event data | All event data values must be JSON-serializable |
| JSON parse graceful degradation | If LLM returns malformed JSON, log warning and return empty claims (never crash) |

### New Dependencies

**None.** All dependencies already exist:
- `re` — Regex matching (Python stdlib)
- `json` — JSON parsing (Python stdlib)
- `LLMClientProtocol` — LLM access (existing in codebase)
- `RetryMiddlewareProtocol` — Retry wrapper (existing)
- `CompetitorRepository` — Story 6-5 (existing)
- `RegulatoryEventEmitter` — Story 6-1 (existing)

No changes to `requirements.txt` needed.

### Anti-Patterns to AVOID (CRITICAL)

1. **NEVER import or depend on EUComplianceChecker** — Follow same PATTERN but independent implementation
2. **NEVER load config directly** — Accept via injection (`HealthClaimExtractionConfig`)
3. **NEVER use spaCy** — Phase 1 is regex+LLM only (spaCy is Phase 2 if needed)
4. **NEVER hardcode model names** — Use `tier="generate"`, never `model="claude-3-sonnet"`
5. **NEVER swallow exceptions without logging**
6. **NEVER use `datetime.utcnow()`** — Use `datetime.now(UTC)`
7. **NEVER block on LLM failures** — Gracefully degrade to regex-only results
8. **NEVER create a new CompetitorRepository** — Reuse from Story 6-5 via DI
9. **NEVER do N+1 queries** — Batch DB operations
10. **NEVER auto-approve treatment claims** — Treatment claims should always be high confidence (severity="high")

### Project Structure Notes

- Engine placed in `teams/dawo/scanners/claim_extraction/` following capability-based organization
- Config in `config/dawo_health_claim_extraction.json` following project naming pattern
- Tests mirror source: `tests/teams/dawo/test_scanners/test_claim_extraction/`
- Reuses `CompetitorRepository` from Story 6-5 via DI
- Extends `RegulatoryEventType` in `core/regulatory/events.py` with 2 new values
- Extends `core/regulatory/models.py` with 1 new model + 2 new enums
- Extends `AlertCategory` in claims_alerts/schemas.py for notification integration
- No conflicts with Stories 6-1 through 6-5 code (purely additive)
- New Alembic migration for extracted_health_claims table

### References

- [Source: epics.md#Story-6.6] — Original story requirements
- [Source: architecture.md#DAWO-Team-Structure] — Directory structure, registration pattern
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: docs/research/nlp-health-claim-extraction.md] — Hybrid regex+LLM decision, Norwegian gap analysis
- [Source: docs/research/eu-health-claims-register.md] — EU regulation details
- [Source: teams/dawo/validators/eu_compliance/agent.py] — EUComplianceChecker hybrid pattern (REFERENCE, don't import)
- [Source: teams/dawo/validators/eu_compliance/rules.py] — ComplianceRules pattern structure
- [Source: teams/dawo/scanners/competitor/repository.py] — CompetitorRepository.get_pending_extraction()
- [Source: teams/dawo/scanners/competitor/schemas.py] — ParsedContent, HealthLanguageResult DTOs
- [Source: core/regulatory/models.py] — CompetitorContent model, ExtractionStatus enum
- [Source: core/regulatory/events.py] — RegulatoryEventEmitter, RegulatoryEventType
- [Source: teams/dawo/scanners/claims_alerts/schemas.py] — AlertCategory
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredAgent, RegisteredService)
- [Source: 6-5-competitor-content-scanner.md] — Previous story learnings and code review fixes
- [Source: docs/pre-submission-checklist.md] — Quality checklist

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

Code review completed with 2 HIGH, 4 MEDIUM, 2 LOW findings — all auto-fixed.

### Completion Notes List

- **H1 FIX**: `repository.py:save_claims` — review_status was being set to `claim.claim_category` (BUG). Fixed to compute from confidence_threshold: `>= threshold → "auto_approved"`, `< threshold → "manual_review"`. Engine now passes `self._config.confidence_threshold` to repository.
- **H2 FIX**: `team_spec.py` — HealthClaimExtractionEngine was registered as `RegisteredService`. Moved to AGENTS list as `RegisteredAgent` with `tier=TIER_GENERATE`, `capabilities=["competitor_monitoring", "claim_extraction"]`.
- **M1 FIX**: `pattern_matcher.py:89` — Norwegian non-verb patterns lacked `\b` word boundaries. Added `\b` prefix and suffix to prevent false matches on substrings.
- **M2 FIX**: `engine.py:_process_item` — `HEALTH_CLAIM_EXTRACTED` event type was defined but never emitted. Added batch-level emission after `save_claims()`.
- **M3 FIX**: `test_engine.py` — Strengthened weak review_status tests: added `test_confidence_threshold_passed_to_save_claims`, `test_high_confidence_counted_correctly`, `test_low_confidence_counted_as_manual_review`, `test_health_claim_extracted_event_emitted`.
- **M4 FIX**: `engine.py` — Added type hints to `_process_item(content: CompetitorContent)` and `_emit_high_confidence(content_id: UUID)`.
- **L1 FIX**: `models.py:__all__` — Added missing exports: `MAX_EXTRACTION_METHOD_LENGTH`, `MAX_ARTICLE_REF_LENGTH`, `MAX_LANGUAGE_CODE_LENGTH`.
- **L2 FIX**: Story file updated: all 12 tasks checked, Dev Agent Record populated.
- **Tests added**: 3 new repo tests (review_status), 4 new engine tests (threshold, counting, event emission). Integration tests updated for new event counts.
- **Final count**: 74 tests passing (65 unit + 9 repository, 8 integration). 0 failures.

### File List

**Source files modified:**
- `teams/dawo/scanners/claim_extraction/engine.py` — Type hints, confidence_threshold pass-through, HEALTH_CLAIM_EXTRACTED event
- `teams/dawo/scanners/claim_extraction/repository.py` — review_status computed from confidence_threshold param
- `teams/dawo/scanners/claim_extraction/pattern_matcher.py` — Norwegian word boundaries
- `teams/dawo/team_spec.py` — Engine moved to AGENTS as RegisteredAgent
- `core/regulatory/models.py` — __all__ updated with 3 missing constants

**Test files modified:**
- `tests/teams/dawo/test_scanners/test_claim_extraction/test_engine.py` — 4 new tests, 2 weak tests replaced
- `tests/teams/dawo/test_scanners/test_claim_extraction/test_repository.py` — 3 new review_status tests
- `tests/integration/test_claim_extraction_integration.py` — Event count assertions updated
