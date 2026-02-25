# Story 6.7: EU Violation Detection

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want extracted claims checked against EU regulations,
So that actual violations are flagged for evidence collection.

---

## Acceptance Criteria

1. **Given** a claim is extracted from competitor content (confidence >= 70)
   **When** the violation detector evaluates it
   **Then** it checks against: EU Health Claims Register (approved list from Story 6-1), EC 1924/2006 rules
   **And** it classifies as: `VIOLATION` (prohibited claim), `SUSPECT` (borderline), or `COMPLIANT`

2. **Given** a claim is classified as VIOLATION
   **When** detection completes
   **Then** violation record is created with:
   - Claim text
   - Regulation violated (specific article)
   - Competitor source (name + URL)
   - Detection timestamp
   - Confidence level
   **And** `evidence_status` is set to `pending_collection` (for Story 6-8)

3. **Given** a competitor claims treatment/cure (claim_category="treatment")
   **When** no EU-approved claim exists for the substance
   **Then** it's automatically classified as VIOLATION
   **And** severity is marked HIGH
   **And** regulation_article references "EC 1924/2006 Art. 10" (prohibited medicinal claim)

4. **Given** a claim uses borderline language (claim_category="general_wellness")
   **When** context suggests wellness rather than medical intent
   **Then** it's classified as SUSPECT for operator review
   **And** detection reasoning is documented
   **And** severity is marked LOW

5. **Given** a claim with category "prevention" or "enhancement"
   **When** no authorized EU health claim exists for that substance
   **Then** it's classified as VIOLATION
   **And** severity is HIGH for prevention (Art. 14.1a), MEDIUM for enhancement (Art. 13.1)

6. **Given** the violation detector runs a batch
   **When** processing completes
   **Then** `RegulatoryEvent` is emitted for each VIOLATION (type=`EU_VIOLATION_DETECTED`)
   **And** summary event is emitted with batch statistics
   **And** batch result includes: total_processed, violations_found, suspects_found, compliant_found

7. **Given** a claim has already been evaluated (violation record exists)
   **When** the detector encounters it again
   **Then** it skips the claim (idempotent — no duplicate violations)

---

## Tasks / Subtasks

- [x] Task 1: Create violation detection config (AC: #1)
  - [x]1.1 Create `config/dawo_violation_detection.json` with:
    - `enabled`: true
    - `batch_size`: 50 (max claims per run)
    - `min_confidence`: 70 (minimum claim confidence for evaluation)
    - `auto_violation_categories`: `["treatment"]` (always VIOLATION regardless of register)
    - `register_check_categories`: `["prevention", "enhancement"]` (check against EU register)
    - `suspect_categories`: `["general_wellness"]` (always SUSPECT for review)
    - `severity_mapping`: `{"treatment": "high", "prevention": "high", "enhancement": "medium", "general_wellness": "low"}`
    - `regulation_mapping`: `{"treatment": "EC 1924/2006 Art. 10", "prevention": "EC 1924/2006 Art. 14.1a", "enhancement": "EC 1924/2006 Art. 13.1", "general_wellness": "EC 1924/2006 Art. 13.1"}`
    - `mushroom_substances`: list of mushroom substance keywords (reishi, lion's mane, chaga, cordyceps, etc.) — for cross-referencing with EU register
  - [x]1.2 Create frozen dataclass `ViolationDetectionConfig` in `teams/dawo/scanners/violation_detection/config.py`
  - [x]1.3 Create `build_violation_detection_config(data: dict) -> ViolationDetectionConfig` builder function
  - [x]1.4 Validate in `__post_init__`: positive batch_size, min_confidence 0-100, non-empty auto_violation_categories, valid severity values ("high"/"medium"/"low"), all categories in severity_mapping + regulation_mapping

- [x] Task 2: Create database model (AC: #2, #3, #4, #5)
  - [x]2.1 Add to `core/regulatory/models.py`:
    - `ViolationStatus` enum: VIOLATION, SUSPECT, COMPLIANT
    - `ViolationSeverity` enum: HIGH, MEDIUM, LOW
    - `EvidenceCollectionStatus` enum: PENDING_COLLECTION, COLLECTED, NOT_REQUIRED
  - [x]2.2 Add `CompetitorViolation` model:
    - `id`: UUID PK (default uuid4)
    - `extracted_claim_id`: UUID FK to `extracted_health_claims.id`, unique (one violation per claim)
    - `violation_status`: String (violation/suspect/compliant)
    - `severity`: String (high/medium/low)
    - `regulation_article`: String (e.g., "EC 1924/2006 Art. 10")
    - `violation_type`: String (e.g., "unauthorized_treatment_claim", "unauthorized_enhancement_claim", "borderline_wellness_claim")
    - `detection_reasoning`: String (why this classification — max 2000 chars)
    - `authorized_claims_checked`: Integer (number of EU register claims checked against)
    - `nearest_authorized_claim`: String nullable (closest matching authorized claim text, if any — max 1000 chars)
    - `competitor_name`: String (denormalized from CompetitorContent for query efficiency)
    - `source_url`: String (denormalized from CompetitorContent for query efficiency)
    - `evidence_status`: String (pending_collection/collected/not_required)
    - `detected_at`: DateTime (when detection ran)
    - `created_at`: DateTime (default `datetime.now(UTC)`)
  - [x]2.3 Add relationship: `ExtractedHealthClaim.violation` -> `CompetitorViolation` (one-to-one)
  - [x]2.4 Add indexes:
    - `idx_violations_claim` on extracted_claim_id (unique)
    - `idx_violations_status` on violation_status
    - `idx_violations_severity` on severity
    - `idx_violations_competitor` on competitor_name
    - `idx_violations_evidence` on evidence_status
  - [x]2.5 Add constants: `MAX_VIOLATION_TYPE_LENGTH = 100`, `MAX_DETECTION_REASONING_LENGTH = 2000`, `MAX_NEAREST_CLAIM_LENGTH = 1000`
  - [x]2.6 Update `__all__` in `core/regulatory/models.py` with all new types

- [x] Task 3: Create Alembic migration (AC: #2)
  - [x]3.1 Create `migrations/versions/2026_02_16_002_create_competitor_violations.py`
  - [x]3.2 Create `competitor_violations` table with all fields and FK to `extracted_health_claims.id`
  - [x]3.3 Create all indexes from Task 2.4
  - [x]3.4 Add unique constraint on `extracted_claim_id` (one violation per claim)
  - [x]3.5 Add downgrade function to drop table

- [x] Task 4: Create schemas/DTOs (AC: #1-#6)
  - [x]4.1 Create `teams/dawo/scanners/violation_detection/schemas.py`
  - [x]4.2 Create `ViolationResult` dataclass: extracted_claim_id (UUID), claim_text (str), claim_category (str), confidence_score (int), violation_status (str), severity (str), regulation_article (str), violation_type (str), detection_reasoning (str), authorized_claims_checked (int), nearest_authorized_claim (str|None), competitor_name (str), source_url (str), evidence_status (str)
  - [x]4.3 Create `DetectionBatchResult` dataclass: total_processed (int), violations_found (int), suspects_found (int), compliant_found (int), skipped_already_evaluated (int), errors (int)
  - [x]4.4 Create `AuthorizedClaimInfo` dataclass: claim_id (str), substance (str), claim_text (str), status (str), food_category (str|None) — represents an EU Register entry for cross-reference

- [x] Task 5: Create violation classifier (AC: #1, #3, #4, #5)
  - [x]5.1 Create `teams/dawo/scanners/violation_detection/classifier.py` with `ViolationClassifier`
  - [x]5.2 Accept deps via constructor: `config: ViolationDetectionConfig`
  - [x]5.3 Implement `classify(claim: ExtractedHealthClaim, authorized_claims: Sequence[HealthClaim], competitor_name: str, source_url: str) -> ViolationResult`:
    - **Auto-violation path** (treatment claims):
      - If `claim.claim_category` in `config.auto_violation_categories` → VIOLATION
      - Severity from `config.severity_mapping[claim.claim_category]`
      - Regulation from `config.regulation_mapping[claim.claim_category]`
      - Reasoning: "Treatment/cure claim '{claim_text}' is prohibited under EC 1924/2006 Art. 10. Functional mushroom products have ZERO authorized health claims."
      - `violation_type`: `f"unauthorized_{claim.claim_category}_claim"`
      - `evidence_status`: "pending_collection"
    - **Register-check path** (prevention/enhancement claims):
      - Search `authorized_claims` for matching substance+claim combinations
      - If NO authorized claim found → VIOLATION
      - Reasoning: "No authorized EU health claim found for substance '{substance}' under {regulation}. Checked {count} authorized claims."
      - `nearest_authorized_claim`: find closest authorized claim by substring match on substance (informational only)
      - `evidence_status`: "pending_collection"
    - **Suspect path** (general_wellness):
      - If `claim.claim_category` in `config.suspect_categories` → SUSPECT
      - Reasoning: "Borderline wellness claim. May be permitted with qualifying language but requires operator review under EC 1924/2006 Art. 13.1."
      - `evidence_status`: "pending_collection" (still collect evidence for operator review)
  - [x]5.4 Implement `_find_nearest_authorized_claim(substance_keywords: list[str], authorized_claims: Sequence[HealthClaim]) -> str | None`:
    - Case-insensitive substring search against authorized claim substances
    - If match found, return `f"{claim.substance}: {claim.claim_text[:200]}"`
    - If no match, return None
  - [x]5.5 Implement `_extract_substance_keywords(claim: ExtractedHealthClaim) -> list[str]`:
    - Extract substance keywords from claim_text and surrounding_context
    - Cross-reference with `config.mushroom_substances` list
    - Return list of matched substance keywords (e.g., ["lion's mane", "hericium erinaceus"])

- [x] Task 6: Create violation repository (AC: #2, #7)
  - [x]6.1 Create `teams/dawo/scanners/violation_detection/repository.py` with `ViolationRepository`
  - [x]6.2 Accept `AsyncSession` via constructor
  - [x]6.3 Implement `save_violation(result: ViolationResult) -> CompetitorViolation` — insert single violation record, return ORM object
  - [x]6.4 Implement `save_violations_batch(results: list[ViolationResult]) -> int` — bulk insert, return count saved
  - [x]6.5 Implement `get_evaluated_claim_ids() -> set[UUID]` — return set of `extracted_claim_id` values that already have violation records (for idempotency check)
  - [x]6.6 Implement `get_violations_by_status(status: str) -> Sequence[CompetitorViolation]` — filter by violation_status
  - [x]6.7 Implement `get_violations_by_competitor(competitor_name: str) -> Sequence[CompetitorViolation]` — filter by competitor_name
  - [x]6.8 Implement `get_pending_evidence_collection() -> Sequence[CompetitorViolation]` — filter by evidence_status="pending_collection" (for Story 6-8)
  - [x]6.9 Implement `commit() -> None` — `await self._session.commit()`

- [x] Task 7: Create violation detector engine (AC: #1-#7)
  - [x]7.1 Create `teams/dawo/scanners/violation_detection/detector.py` with `ViolationDetector`
  - [x]7.2 Accept deps via constructor: `claim_repository: HealthClaimRepository`, `health_claims_repository: HealthClaimsRepository`, `violation_repository: ViolationRepository`, `classifier: ViolationClassifier`, `event_emitter: RegulatoryEventEmitter`, `config: ViolationDetectionConfig`
  - [x]7.3 Implement `execute() -> DetectionBatchResult`:
    - **Stage 1: Fetch claims** — `claim_repository.get_high_confidence_claims(config.min_confidence)` limited to `config.batch_size`
    - **Stage 2: Filter already-evaluated** — `violation_repository.get_evaluated_claim_ids()` and skip claims with existing violations (idempotency)
    - **Stage 3: Load EU register** — `health_claims_repository.get_latest_snapshot()` then `health_claims_repository.get_relevant_claims(snapshot_id)` to get authorized claims
    - **Stage 4: Classify each claim** — `classifier.classify(claim, authorized_claims, competitor_name, source_url)`
      - Fetch `competitor_name` and `source_url` from `claim.competitor_content` relationship (eager load or separate query)
    - **Stage 5: Save violations** — `violation_repository.save_violations_batch(results)` (save ALL classifications including COMPLIANT for audit trail)
    - **Stage 6: Emit events** — for each VIOLATION: emit `EU_VIOLATION_DETECTED` event; for each SUSPECT: emit `SUSPECT_CLAIM_FLAGGED` event
    - **Stage 7: Commit** — `violation_repository.commit()`
    - Return `DetectionBatchResult` with statistics
  - [x]7.4 Handle per-claim errors gracefully — log error, skip claim, continue with next
  - [x]7.5 Log all stages with counts at INFO level
  - [x]7.6 Eagerly load `ExtractedHealthClaim.competitor_content` to avoid N+1 queries — either via the repository query or a separate batch query for all needed CompetitorContent records

- [x] Task 8: Add event types (AC: #6)
  - [x]8.1 Add to `RegulatoryEventType` in `core/regulatory/events.py`:
    - `EU_VIOLATION_DETECTED = "eu_violation_detected"` (Story 6-7)
    - `SUSPECT_CLAIM_FLAGGED = "suspect_claim_flagged"` (Story 6-7)
  - [x]8.2 Update `__all__` in `core/regulatory/events.py`
  - [x]8.3 Update `AlertCategory` enum in `teams/dawo/scanners/claims_alerts/schemas.py` — add `VIOLATION_DETECTION = "violation_detection"`
  - [x]8.4 Update `categorize_event()` in claims_alerts/schemas.py to handle new event types

- [x] Task 9: Create package __init__.py and register in team_spec.py (AC: #1-#7)
  - [x]9.1 Create `teams/dawo/scanners/violation_detection/__init__.py` with complete `__all__`
  - [x]9.2 Export: ViolationDetectionConfig, ViolationClassifier, ViolationDetector, ViolationRepository, ViolationResult, DetectionBatchResult, AuthorizedClaimInfo
  - [x]9.3 Register in team_spec.py:
    - `ViolationDetector` as RegisteredAgent with capabilities `["competitor_monitoring", "violation_detection"]`, tier=TIER_GENERATE, requires_session=True
    - `ViolationClassifier` as RegisteredService with capabilities `["competitor_monitoring", "violation_classification"]`, requires_session=False
    - `ViolationRepository` as RegisteredService with capabilities `["competitor_monitoring", "violation_storage"]`, requires_session=True
  - [x]9.4 Add all new imports to team_spec.py

- [x] Task 10: Create unit tests (AC: #1-#7)
  - [x] 10.1 Create `tests/teams/dawo/test_scanners/test_violation_detection/` with `__init__.py`, `conftest.py`
  - [x] 10.2 `conftest.py` fixtures:
    - `sample_config`: ViolationDetectionConfig with default values
    - `sample_extracted_claim_treatment`: ExtractedHealthClaim mock with category="treatment", confidence=90
    - `sample_extracted_claim_enhancement`: ExtractedHealthClaim mock with category="enhancement", confidence=80
    - `sample_extracted_claim_wellness`: ExtractedHealthClaim mock with category="general_wellness", confidence=75
    - `sample_authorized_claims`: list of HealthClaim mocks with various substances (none for mushrooms)
    - `sample_competitor_content`: CompetitorContent mock with competitor_name and source_url
    - `mock_session`: AsyncSession mock
    - `mock_event_emitter`: RegulatoryEventEmitter mock
  - [x] 10.3 `test_config.py` (~7 tests):
    - Valid config creation
    - Empty auto_violation_categories → ValueError
    - Invalid severity value → ValueError
    - Non-positive batch_size → ValueError
    - Confidence threshold out of range → ValueError
    - Build function from JSON dict
    - Frozen immutability
  - [x] 10.4 `test_classifier.py` (~12 tests):
    - Treatment claim → VIOLATION (auto, HIGH severity, Art. 10)
    - Prevention claim with no authorized claim → VIOLATION (HIGH, Art. 14.1a)
    - Enhancement claim with no authorized claim → VIOLATION (MEDIUM, Art. 13.1)
    - General wellness claim → SUSPECT (LOW, Art. 13.1)
    - Reasoning includes claim text and regulation reference
    - `violation_type` format: "unauthorized_{category}_claim"
    - `evidence_status`: "pending_collection" for VIOLATION and SUSPECT
    - `authorized_claims_checked` count matches input list length
    - `nearest_authorized_claim` populated when substance match found in register
    - `nearest_authorized_claim` is None when no match
    - `_extract_substance_keywords` matches known mushroom substances
    - Competitor name and source_url populated from input
  - [x] 10.5 `test_repository.py` (~8 tests):
    - `save_violation()` inserts record and returns ORM object
    - `save_violations_batch()` inserts all and returns count
    - `save_violations_batch()` with empty list → returns 0
    - `get_evaluated_claim_ids()` returns correct UUID set
    - `get_violations_by_status()` filters correctly
    - `get_violations_by_competitor()` filters correctly
    - `get_pending_evidence_collection()` returns pending_collection only
    - `commit()` calls session.commit()
  - [x] 10.6 `test_detector.py` (~12 tests):
    - Full pipeline: high-confidence claims → classify → save → events emitted
    - Idempotency: already-evaluated claims are skipped
    - Treatment claim → VIOLATION event emitted
    - Enhancement claim → VIOLATION event emitted
    - General wellness claim → SUSPECT event emitted (different event type)
    - No high-confidence claims → empty batch result, no events
    - EU register unavailable (no snapshot) → classify with empty authorized list (still works — all mushroom claims are violations)
    - Per-claim error handling: one claim fails, others continue
    - Batch size limiting: respects config.batch_size
    - `DetectionBatchResult` statistics accurate
    - Competitor name/source_url fetched from claim relationship
    - N+1 prevention: verifies eager loading or batch query pattern
  - [x] 10.7 `test_schemas.py` (~4 tests):
    - ViolationResult creation with all fields
    - DetectionBatchResult creation with defaults
    - AuthorizedClaimInfo creation
    - ViolationResult with None nearest_authorized_claim

- [x] Task 11: Create integration tests (AC: #1-#7)
  - [x] 11.1 Test full pipeline: extracted claims with treatment/enhancement/wellness → violations classified and saved to DB → events emitted
  - [x] 11.2 Test idempotency: run detector twice on same claims → second run skips all (0 new violations)
  - [x] 11.3 Test treatment auto-violation: treatment claim → VIOLATION with HIGH severity, Art. 10 reference
  - [x] 11.4 Test register cross-reference: enhancement claim + empty authorized list → VIOLATION
  - [x] 11.5 Test suspect classification: general_wellness claim → SUSPECT with LOW severity
  - [x] 11.6 Test event emission: VIOLATION → EU_VIOLATION_DETECTED event, SUSPECT → SUSPECT_CLAIM_FLAGGED event
  - [x] 11.7 Test evidence_status handoff: VIOLATION records have evidence_status="pending_collection" (for Story 6-8)

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#DAWO-Team-Structure], [project-context.md#Code-Organization]

This is the **seventh story in Epic 6** (CleanMarket & Regulatory Intelligence). It's the **third story in the CleanMarket evidence chain** (Stories 6-5 through 6-10).

### Epic 6 Evidence Chain Position

```
Story 6-5 (done)      → Scan competitor content → Store in DB (competitor_content table)
Story 6-6 (done)      → Extract health claims → Store claims (extracted_health_claims table)
Story 6-7 (this)      → Detect EU violations from extracted claims → Store violations (competitor_violations table)
Story 6-8             → Capture evidence screenshots for violations (Playwright)
Story 6-9             → Searchable evidence database + UI
Story 6-10            → Generate PDF violation reports
```

**Critical handoff IN:** Story 6-6 stored claims in `extracted_health_claims` table with `confidence_score`, `claim_category`, and `eu_article_reference`. This story reads high-confidence claims and classifies them as violations.

**Critical handoff OUT:** Story 6-8 will read `competitor_violations` with `evidence_status="pending_collection"` to capture screenshots. Provide `ViolationRepository.get_pending_evidence_collection()` for this.

### Key Design Decision: Classification Logic

**Source:** [epics.md#Story-6.7], [epic-6-prep.md]

**For functional mushrooms: ZERO authorized EU health claims exist.** This is the critical domain fact driving the classification logic.

| Claim Category | Classification | Severity | EU Article | Reasoning |
|----------------|---------------|----------|------------|-----------|
| treatment | ALWAYS VIOLATION | HIGH | Art. 10 | Medicinal claims prohibited for food/supplements |
| prevention | VIOLATION (no authorized claim) | HIGH | Art. 14.1a | Disease risk reduction requires authorization |
| enhancement | VIOLATION (no authorized claim) | MEDIUM | Art. 13.1 | Function claims require authorization |
| general_wellness | SUSPECT | LOW | Art. 13.1 | Borderline — may be permitted with qualifying language |

**Three classification paths:**
1. **Auto-violation** — Treatment claims are ALWAYS prohibited (no register check needed)
2. **Register-check** — Prevention/enhancement claims cross-reference EU Health Claims Register (Story 6-1 data)
3. **Suspect** — General wellness claims flagged for operator review

### EU Health Claims Register Cross-Reference

**Source:** [teams/dawo/scanners/health_claims/repository.py], [core/regulatory/models.py]

```python
# Get authorized claims from Story 6-1's HealthClaimsRepository:
snapshot = await health_claims_repository.get_latest_snapshot()
if snapshot:
    authorized_claims = await health_claims_repository.get_relevant_claims(snapshot.id)
else:
    authorized_claims = []  # No register data — still works (all mushroom claims are violations)

# HealthClaim model fields for cross-reference:
# - substance: "Ganoderma lucidum", "Hericium erinaceus", etc.
# - status: ClaimStatus.AUTHORISED / .NON_AUTHORISED / .ON_HOLD / .WITHDRAWN
# - claim_text: "Vitamin D contributes to normal immune function"
# - food_category: functional food category
# - is_relevant: True if matches mushroom/adaptogen keywords
```

**CRITICAL:** Even if the register query returns no results (first run, download failed), the detector MUST still work. Treatment claims are ALWAYS violations. Prevention/enhancement claims with NO authorized claims in the register are also violations.

### Existing Code to REUSE (Not Reinvent)

| Component | Source | What to Use |
|-----------|--------|-------------|
| `HealthClaimRepository` | `teams/dawo/scanners/claim_extraction/repository.py` | `get_high_confidence_claims(min_confidence=70)` |
| `HealthClaimsRepository` | `teams/dawo/scanners/health_claims/repository.py` | `get_latest_snapshot()`, `get_relevant_claims(snapshot_id)` |
| `ExtractedHealthClaim` | `core/regulatory/models.py` | ORM model with `competitor_content` relationship |
| `HealthClaim` | `core/regulatory/models.py` | EU Register claims with substance, status, claim_text |
| `CompetitorContent` | `core/regulatory/models.py` | competitor_name, source_url for denormalization |
| `RegulatoryEventEmitter` | `core/regulatory/events.py` | Event emission for violations |
| `ClaimCategory` enum | `core/regulatory/models.py` | TREATMENT, PREVENTION, ENHANCEMENT, GENERAL_WELLNESS |

**CRITICAL: Do NOT import or depend on EUComplianceChecker.** That validates DAWO's own content. This story classifies violations in COMPETITOR content. Different purpose, different inputs, different outputs.

**CRITICAL: Do NOT create a new repository for reading ExtractedHealthClaim.** Reuse `HealthClaimRepository` from Story 6-6. Only create `ViolationRepository` for writing `CompetitorViolation` records.

### Relationship Chain (N+1 Prevention)

```
ExtractedHealthClaim
  → .competitor_content (FK: competitor_content_id → CompetitorContent)
      → .competitor_name
      → .source_url
  → .violation (one-to-one, NEW in this story)
      → CompetitorViolation
```

**Eager loading strategy:** When fetching claims for evaluation, eagerly load `competitor_content` to get `competitor_name` and `source_url` without N+1 queries.

```python
# In HealthClaimRepository or a custom query in ViolationDetector:
stmt = (
    select(ExtractedHealthClaim)
    .options(selectinload(ExtractedHealthClaim.competitor_content))
    .where(ExtractedHealthClaim.confidence_score >= min_confidence)
    .limit(batch_size)
)
```

**NOTE:** `HealthClaimRepository.get_high_confidence_claims()` may NOT eagerly load `competitor_content`. If not, the ViolationDetector must either:
1. Add an eager-loading variant method
2. Do a separate batch query for CompetitorContent records
3. Use `selectinload` in a custom query within the detector

Option 3 is recommended — add a `_fetch_claims_with_content()` private method in the detector.

### Database Model Pattern (Follow Existing)

**Source:** [core/regulatory/models.py] — ExtractedHealthClaim, CompetitorContent

```python
MAX_VIOLATION_TYPE_LENGTH = 100
MAX_DETECTION_REASONING_LENGTH = 2000
MAX_NEAREST_CLAIM_LENGTH = 1000

class ViolationStatus(str, Enum):
    """Classification of an extracted claim against EU regulations."""
    VIOLATION = "violation"
    SUSPECT = "suspect"
    COMPLIANT = "compliant"

class ViolationSeverity(str, Enum):
    """Severity level of a detected violation."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EvidenceCollectionStatus(str, Enum):
    """Status of evidence collection for a violation."""
    PENDING_COLLECTION = "pending_collection"
    COLLECTED = "collected"
    NOT_REQUIRED = "not_required"

class CompetitorViolation(Base):
    __tablename__ = "competitor_violations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    extracted_claim_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("extracted_health_claims.id"),
        nullable=False, unique=True  # One violation per claim
    )
    violation_status: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False)
    severity: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False)
    regulation_article: Mapped[str] = mapped_column(String(MAX_REGULATION_LENGTH), nullable=False)
    violation_type: Mapped[str] = mapped_column(String(MAX_VIOLATION_TYPE_LENGTH), nullable=False)
    detection_reasoning: Mapped[str] = mapped_column(String(MAX_DETECTION_REASONING_LENGTH), nullable=False)
    authorized_claims_checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nearest_authorized_claim: Mapped[str | None] = mapped_column(String(MAX_NEAREST_CLAIM_LENGTH), nullable=True)
    competitor_name: Mapped[str] = mapped_column(String(MAX_COMPETITOR_NAME_LENGTH), nullable=False)
    source_url: Mapped[str] = mapped_column(String(MAX_COMPETITOR_URL_LENGTH), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False, default="pending_collection")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
```

### Event System (Extend Existing)

**Source:** [core/regulatory/events.py]

```python
# Add to RegulatoryEventType enum:
EU_VIOLATION_DETECTED = "eu_violation_detected"          # Story 6-7
SUSPECT_CLAIM_FLAGGED = "suspect_claim_flagged"          # Story 6-7

# Emit for violations:
await self._event_emitter.emit(RegulatoryEvent(
    event_type=RegulatoryEventType.EU_VIOLATION_DETECTED,
    claim_id=str(violation.extracted_claim_id),
    substance="",  # Could extract from claim context
    severity=violation.severity,
    data={
        "violation_id": str(violation_id),
        "competitor_name": violation.competitor_name,
        "source_url": violation.source_url,
        "claim_text": violation.claim_text,
        "claim_category": violation.claim_category,
        "violation_type": violation.violation_type,
        "regulation_article": violation.regulation_article,
        "confidence_score": violation.confidence_score,
        "evidence_status": violation.evidence_status,
    },
))
```

### Registration Pattern (MUST FOLLOW)

**Source:** [teams/dawo/team_spec.py]

```python
# ViolationDetector is a RegisteredAgent (orchestrates detection pipeline)
RegisteredAgent(
    name="violation_detector",
    agent_class=ViolationDetector,
    capabilities=["competitor_monitoring", "violation_detection"],
    tier=TIER_GENERATE,  # Accuracy critical for regulatory classification
),

# Supporting services
RegisteredService(
    name="violation_classifier",
    service_class=ViolationClassifier,
    capabilities=["competitor_monitoring", "violation_classification"],
    requires_session=False,
),
RegisteredService(
    name="violation_repository",
    service_class=ViolationRepository,
    capabilities=["competitor_monitoring", "violation_storage"],
    requires_session=True,
),
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#DAWO-Team-Structure], Stories 6-1 through 6-6 patterns

```
teams/dawo/scanners/violation_detection/     # NEW — EU violation detection
├── __init__.py                              # Export all public types
├── config.py                                # ViolationDetectionConfig
├── classifier.py                            # ViolationClassifier (classification logic)
├── detector.py                              # ViolationDetector (orchestrator engine)
├── repository.py                            # ViolationRepository (AsyncSession)
└── schemas.py                               # DTOs: ViolationResult, DetectionBatchResult, etc.

config/
└── dawo_violation_detection.json            # NEW — detection config

core/regulatory/
└── models.py                                # ADD: CompetitorViolation + 3 new enums + constants

core/regulatory/
└── events.py                                # ADD: 2 new RegulatoryEventType values

migrations/versions/
└── 2026_02_16_002_create_competitor_violations.py  # NEW

tests/teams/dawo/test_scanners/test_violation_detection/  # NEW
├── __init__.py
├── conftest.py                              # Shared fixtures
├── test_config.py
├── test_classifier.py
├── test_repository.py
├── test_detector.py
└── test_schemas.py

tests/integration/
└── test_violation_detection_integration.py  # NEW
```

### Testing Strategy (TDD Required)

**Mock patterns:**

```python
@pytest.fixture
def sample_treatment_claim():
    """ExtractedHealthClaim with treatment category."""
    claim = MagicMock(spec=ExtractedHealthClaim)
    claim.id = uuid4()
    claim.claim_text = "treats brain fog"
    claim.claim_category = "treatment"
    claim.confidence_score = 92
    claim.language_detected = "en"
    claim.extraction_method = "hybrid"
    claim.eu_article_reference = "prohibited"
    claim.surrounding_context = "Our lion's mane extract treats brain fog naturally!"
    claim.competitor_content_id = uuid4()
    # Mock the relationship
    content = MagicMock(spec=CompetitorContent)
    content.competitor_name = "CompetitorA"
    content.source_url = "https://instagram.com/p/abc123"
    claim.competitor_content = content
    return claim

@pytest.fixture
def sample_enhancement_claim():
    """ExtractedHealthClaim with enhancement category."""
    claim = MagicMock(spec=ExtractedHealthClaim)
    claim.id = uuid4()
    claim.claim_text = "boosts cognitive function"
    claim.claim_category = "enhancement"
    claim.confidence_score = 85
    claim.language_detected = "en"
    claim.extraction_method = "hybrid"
    claim.eu_article_reference = "13.1"
    claim.surrounding_context = "Lion's mane boosts cognitive function for better focus"
    claim.competitor_content_id = uuid4()
    content = MagicMock(spec=CompetitorContent)
    content.competitor_name = "CompetitorB"
    content.source_url = "https://competitor-b.com/products/lions-mane"
    claim.competitor_content = content
    return claim

@pytest.fixture
def sample_wellness_claim():
    """ExtractedHealthClaim with general_wellness category."""
    claim = MagicMock(spec=ExtractedHealthClaim)
    claim.id = uuid4()
    claim.claim_text = "supports overall wellbeing"
    claim.claim_category = "general_wellness"
    claim.confidence_score = 72
    claim.language_detected = "en"
    claim.extraction_method = "regex"
    claim.eu_article_reference = "13.1"
    claim.surrounding_context = "Reishi mushroom supports overall wellbeing and balance"
    claim.competitor_content_id = uuid4()
    content = MagicMock(spec=CompetitorContent)
    content.competitor_name = "CompetitorC"
    content.source_url = "https://competitor-c.com/blog/reishi"
    claim.competitor_content = content
    return claim

@pytest.fixture
def sample_authorized_claims():
    """HealthClaim records from EU Register (none for mushrooms)."""
    # Vitamin D has authorized claims — mushrooms do not
    vitamin_d = MagicMock(spec=HealthClaim)
    vitamin_d.claim_id = "EU-2012-001"
    vitamin_d.substance = "Vitamin D"
    vitamin_d.status = ClaimStatus.AUTHORISED
    vitamin_d.claim_text = "Vitamin D contributes to the normal function of the immune system"
    vitamin_d.food_category = "Vitamin D containing foods"
    vitamin_d.is_relevant = True
    return [vitamin_d]

@pytest.fixture
def mock_claim_repository():
    """Mock HealthClaimRepository."""
    repo = AsyncMock()
    repo.get_high_confidence_claims = AsyncMock(return_value=[])
    return repo

@pytest.fixture
def mock_health_claims_repository():
    """Mock HealthClaimsRepository (Story 6-1)."""
    repo = AsyncMock()
    snapshot = MagicMock()
    snapshot.id = uuid4()
    repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
    repo.get_relevant_claims = AsyncMock(return_value=[])
    return repo
```

**Target: ~43 unit tests + ~7 integration tests**

### Previous Story Learnings (CRITICAL — Apply All)

**Source:** [6-6-health-claim-extraction-engine.md#Completion-Notes], [docs/pre-submission-checklist.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Every `__init__.py` lists ALL public classes, enums, functions |
| Config injection pattern | All components accept deps via constructor, NEVER load files |
| `datetime.now(UTC)` not `datetime.utcnow()` | Use everywhere in timestamps |
| `result.scalars().all()` vs `result.all()` | Use correct SQLAlchemy result extraction |
| Pre-initialize variables before try blocks | Avoid UnboundLocalError |
| `logger.debug()` for swallowed exceptions | Don't silently eat exceptions |
| `session.add` is sync in SQLAlchemy | Use `MagicMock()` not `AsyncMock()` for `session.add` in tests |
| No N+1 queries | Eager load `competitor_content` relationship; batch all DB queries |
| Database filtering in SQL, not Python | Filter by violation_status, evidence_status, competitor_name in SQL |
| Activity logging in one place | Detector logs stage transitions, classifier/repository log details |
| Handle list values in event data | All event data values must be JSON-serializable |
| Review status computed correctly | Story 6-6 H1 fix — don't copy-paste bugs; verify classifier output |
| RegisteredAgent vs RegisteredService | Story 6-6 H2 fix — ViolationDetector is RegisteredAgent, not RegisteredService |
| Word boundaries in pattern matching | Story 6-6 M1 fix — if any pattern matching needed, use `\b` |

### New Dependencies

**None.** All dependencies already exist:
- `uuid4` — UUID generation (Python stdlib)
- `datetime` — Timestamps (Python stdlib)
- `HealthClaimRepository` — Story 6-6 (existing)
- `HealthClaimsRepository` — Story 6-1 (existing)
- `RegulatoryEventEmitter` — Story 6-1 (existing)
- `ExtractedHealthClaim`, `HealthClaim`, `CompetitorContent` — models (existing)

No changes to `requirements.txt` needed.

### Anti-Patterns to AVOID (CRITICAL)

1. **NEVER import or depend on EUComplianceChecker** — That validates DAWO's own content; this classifies competitor violations
2. **NEVER load config directly** — Accept via injection (`ViolationDetectionConfig`)
3. **NEVER hardcode model names** — Use `tier="generate"`, never `model="claude-3-sonnet"`
4. **NEVER swallow exceptions without logging**
5. **NEVER use `datetime.utcnow()`** — Use `datetime.now(UTC)`
6. **NEVER create a new HealthClaimRepository** — Reuse from Story 6-6 via DI
7. **NEVER do N+1 queries** — Eager load relationships; batch DB operations
8. **NEVER create duplicate violation records** — Enforce unique constraint on extracted_claim_id; check `get_evaluated_claim_ids()` before classifying
9. **NEVER auto-classify treatment claims as anything other than VIOLATION** — Treatment = prohibited, always
10. **NEVER skip saving COMPLIANT classifications** — Store for audit trail (Story 6-9 needs complete records)

### Project Structure Notes

- Detector placed in `teams/dawo/scanners/violation_detection/` following the CleanMarket evidence chain pattern (6-5 competitor, 6-6 claim_extraction, 6-7 violation_detection)
- Config in `config/dawo_violation_detection.json` following project naming convention
- Tests mirror source: `tests/teams/dawo/test_scanners/test_violation_detection/`
- Reuses `HealthClaimRepository` from Story 6-6 and `HealthClaimsRepository` from Story 6-1 via DI
- Extends `RegulatoryEventType` in `core/regulatory/events.py` with 2 new values
- Extends `core/regulatory/models.py` with 1 new model + 3 new enums + 3 new constants
- Extends `AlertCategory` in claims_alerts/schemas.py for notification integration
- No conflicts with Stories 6-1 through 6-6 code (purely additive)
- New Alembic migration for competitor_violations table

### References

- [Source: epics.md#Story-6.7] — Original story requirements
- [Source: architecture.md#DAWO-Team-Structure] — Directory structure, registration pattern
- [Source: project-context.md] — Critical implementation rules and anti-patterns
- [Source: epic-6-prep.md] — Evidence storage decisions, Playwright for screenshots (Story 6-8)
- [Source: core/regulatory/models.py] — ExtractedHealthClaim, CompetitorContent, HealthClaim models
- [Source: core/regulatory/events.py] — RegulatoryEventEmitter, RegulatoryEventType
- [Source: teams/dawo/scanners/claim_extraction/repository.py] — HealthClaimRepository.get_high_confidence_claims()
- [Source: teams/dawo/scanners/health_claims/repository.py] — HealthClaimsRepository.get_latest_snapshot(), get_relevant_claims()
- [Source: teams/dawo/validators/eu_compliance/agent.py] — EUComplianceChecker hybrid pattern (REFERENCE ONLY, don't import)
- [Source: teams/dawo/validators/eu_compliance/rules.py] — ComplianceRules pattern structure (REFERENCE ONLY)
- [Source: config/dawo_compliance_rules.json] — Prohibited/borderline/permitted patterns (REFERENCE for understanding)
- [Source: config/dawo_health_claim_extraction.json] — Claim categories, EU article mapping
- [Source: teams/dawo/scanners/claims_alerts/schemas.py] — AlertCategory
- [Source: teams/dawo/team_spec.py] — Registration patterns (RegisteredAgent, RegisteredService)
- [Source: 6-6-health-claim-extraction-engine.md] — Previous story learnings and code review fixes
- [Source: docs/pre-submission-checklist.md] — Quality checklist

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — all tests passed on first GREEN attempt for every task.

### Completion Notes List

- All 11 tasks implemented with TDD (red-green-refactor)
- 45 unit tests + 7 integration tests = 52 tests total (exceeds target of ~50)
- Three classification paths: auto-violation (treatment), register-check (prevention/enhancement), suspect (general_wellness)
- EU Health Claims Register cross-reference via Story 6-1 HealthClaimsRepository
- Idempotency via unique constraint on extracted_claim_id + evaluated IDs check
- Evidence status handoff: all violations have evidence_status="pending_collection" for Story 6-8
- Two new event types: EU_VIOLATION_DETECTED, SUSPECT_CLAIM_FLAGGED
- AlertCategory extended with VIOLATION_DETECTION for notification integration
- No new dependencies — all from stdlib and existing project modules

### File List

**New files:**
- `config/dawo_violation_detection.json` — Detection config (Task 1)
- `teams/dawo/scanners/violation_detection/__init__.py` — Package with complete `__all__` (Task 9)
- `teams/dawo/scanners/violation_detection/config.py` — ViolationDetectionConfig frozen dataclass (Task 1)
- `teams/dawo/scanners/violation_detection/schemas.py` — ViolationResult, DetectionBatchResult, AuthorizedClaimInfo (Task 4)
- `teams/dawo/scanners/violation_detection/classifier.py` — ViolationClassifier with 3 paths (Task 5)
- `teams/dawo/scanners/violation_detection/repository.py` — ViolationRepository CRUD (Task 6)
- `teams/dawo/scanners/violation_detection/detector.py` — ViolationDetector 7-stage pipeline (Task 7)
- `migrations/versions/2026_02_16_002_create_competitor_violations.py` — Alembic migration (Task 3)
- `tests/teams/dawo/test_scanners/test_violation_detection/__init__.py` — Test package
- `tests/teams/dawo/test_scanners/test_violation_detection/conftest.py` — Shared fixtures
- `tests/teams/dawo/test_scanners/test_violation_detection/test_config.py` — 9 tests
- `tests/teams/dawo/test_scanners/test_violation_detection/test_schemas.py` — 5 tests
- `tests/teams/dawo/test_scanners/test_violation_detection/test_classifier.py` — 12 tests
- `tests/teams/dawo/test_scanners/test_violation_detection/test_repository.py` — 8 tests
- `tests/teams/dawo/test_scanners/test_violation_detection/test_detector.py` — 11 tests
- `tests/integration/test_violation_detection_integration.py` — 7 integration tests

**Modified files:**
- `core/regulatory/models.py` — Added CompetitorViolation model, 3 enums, 3 constants, relationship (Task 2)
- `core/regulatory/events.py` — Added EU_VIOLATION_DETECTED, SUSPECT_CLAIM_FLAGGED event types (Task 8)
- `teams/dawo/scanners/claims_alerts/schemas.py` — Added VIOLATION_DETECTION to AlertCategory (Task 8)
- `teams/dawo/team_spec.py` — Registered ViolationDetector (agent), ViolationClassifier, ViolationRepository (services) (Task 9)

### Code Review Fixes Applied

**Reviewer:** Claude Opus 4.6 (adversarial code review)

| ID | Severity | Fix |
|----|----------|-----|
| H1 | HIGH | Added `selectinload(ExtractedHealthClaim.competitor_content)` to `HealthClaimRepository.get_high_confidence_claims()` — prevents N+1 / MissingGreenlet |
| H2 | HIGH | Added SQL `LIMIT` to `get_high_confidence_claims()` — prevents unbounded SELECT; detector passes `batch_size * 3` |
| M1 | MEDIUM | Fixed `team_spec.py` capabilities to match story spec (`violation_classification`, `violation_storage`) |
| M2 | MEDIUM | Made `_auto_violation` reasoning dynamic: `f"{category.replace('_', ' ').title()} claim"` instead of hardcoded "Treatment/cure" |
| M3 | MEDIUM | Rewrote `test_batch_size_limiting` — provides 5 claims with batch_size=2, asserts only 2 processed |
| L1 | LOW | Refactored `save_violations_batch` to call `save_violation` in loop (DRY, no duplicated ORM construction) |

**Files modified in review:**
- `teams/dawo/scanners/claim_extraction/repository.py` — H1 + H2 (eager loading + limit param)
- `teams/dawo/scanners/violation_detection/detector.py` — H2 (passes limit=batch_size*3)
- `teams/dawo/scanners/violation_detection/classifier.py` — M2 (dynamic reasoning)
- `teams/dawo/scanners/violation_detection/repository.py` — L1 (DRY batch save)
- `teams/dawo/team_spec.py` — M1 (capabilities fix)
- `tests/teams/dawo/test_scanners/test_violation_detection/test_detector.py` — M3 (real batch test)

All 52 tests pass after review fixes (45 unit + 7 integration).
