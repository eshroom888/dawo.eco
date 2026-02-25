# Story 7.5: Performance Feedback Loop

Status: done

## Story

As an operator,
I want the system to analyze post performance weekly and feed insights back to content strategy and quality scoring,
so that content quality continuously improves and I can make data-driven decisions about what works.

## Acceptance Criteria

1. **AC1 - Weekly Analysis Trigger:** System runs weekly feedback analysis when 100+ posts have post-publish scores. Analysis covers: best-performing content types, optimal posting times (day/hour), and most effective hashtags.

2. **AC2 - Quality Scoring Weight Adjustment:** Correlation analysis (from Story 7-4's `VarianceAnalyzer.run_correlation_analysis()`) feeds into weight adjustment proposals. Proposed changes are logged with before/after weights for operator transparency. Weights normalize to sum=1.0.

3. **AC3 - Source Performance Tracking:** Track which research sources (by `source_type` from research pool) produce content that performs best post-publish. High-performers get +weight boost, low-performers get -weight in source scoring. Weight adjustments logged.

4. **AC4 - Feedback Report Persistence:** Each weekly run produces a `FeedbackReport` stored in database with: content type rankings, time slot analysis, hashtag rankings, weight adjustment proposals, and strategy recommendations.

5. **AC5 - Transparency Logging:** All learning updates (weight changes, source adjustments, recommendations) logged for operator review. Historical reports queryable by date range.

6. **AC6 - Graceful Degradation:** If any analysis component fails (e.g., insufficient data for hashtag analysis), the overall report still completes with available sections. Missing sections noted as `"insufficient_data"`.

## Tasks / Subtasks

- [x] Task 1: Database Models + Migration (AC: 4, 5)
  - [x]1.1 Create `FeedbackReport` SQLAlchemy model in `core/analytics/feedback_loop_models.py`
    - Fields: `id` (UUID PK), `report_date` (date, unique index), `min_posts_threshold` (int), `total_posts_analyzed` (int), `content_type_rankings` (JSONB), `time_slot_analysis` (JSONB), `hashtag_rankings` (JSONB), `weight_adjustment_proposal` (JSONB), `source_performance` (JSONB), `recommendations` (JSONB list), `status` (str: "complete"/"partial"), `missing_sections` (JSONB list), `created_at` (datetime)
  - [x]1.2 Create `WeightAdjustmentRecord` SQLAlchemy model
    - Fields: `id` (UUID PK), `adjustment_type` (str: "quality_scoring"/"source_scoring"), `previous_weights` (JSONB), `new_weights` (JSONB), `correlation_data` (JSONB), `applied` (bool, default False), `applied_at` (datetime nullable), `feedback_report_id` (UUID FK to FeedbackReport), `created_at` (datetime)
  - [x]1.3 Create Alembic migration `2026_02_26_001_create_feedback_loop_tables.py`
  - [x]1.4 Write model tests (target: 20+ tests covering constraints, defaults, JSONB storage)

- [x] Task 2: Feedback Loop Repository (AC: 4, 5)
  - [x]2.1 Create `FeedbackLoopRepository` in `core/analytics/feedback_loop_repository.py`
    - `save_report(report: FeedbackReport) -> FeedbackReport`
    - `get_latest_report() -> Optional[FeedbackReport]`
    - `get_reports_by_date_range(start: date, end: date) -> list[FeedbackReport]`
    - `save_weight_adjustment(record: WeightAdjustmentRecord) -> WeightAdjustmentRecord`
    - `get_weight_history(adjustment_type: str, limit: int) -> list[WeightAdjustmentRecord]`
    - `mark_adjustment_applied(record_id: UUID) -> None`
  - [x]2.2 Write repository tests (target: 15+ tests)

- [x] Task 3: Content Performance Analyzer (AC: 1)
  - [x]3.1 Create `ContentPerformanceAnalyzer` in `core/analytics/content_performance_analyzer.py`
    - Constructor: `QualityScoringRepository`, `InstagramMetricsRepository`
    - `analyze_content_types(min_posts: int = 100) -> ContentTypeAnalysis`
    - Groups scored posts by content attributes in `metrics_snapshot` (content_type field)
    - Returns ranking with avg score, count, trend direction per type
  - [x]3.2 Implement `analyze_posting_times() -> TimeSlotAnalysis`
    - Join `PostPublishScoreRecord` with `InstagramMediaMetric` via `media_id`
    - Group by day-of-week and hour-of-day
    - Return heatmap of avg scores by time slot (top 5 slots highlighted)
  - [x]3.3 Implement `analyze_hashtags() -> HashtagAnalysis`
    - Extract hashtags from `metrics_snapshot.caption` or join with content records
    - Group by individual hashtag, compute avg post score per hashtag
    - Return top 20 hashtags ranked by associated post performance
    - Minimum 3 posts per hashtag to qualify for ranking
  - [x]3.4 Result DTOs: `ContentTypeAnalysis`, `ContentTypeRanking`, `TimeSlotAnalysis`, `TimeSlot`, `HashtagAnalysis`, `HashtagRanking` — all frozen dataclasses
  - [x]3.5 Write analyzer tests (target: 25+ tests covering all three dimensions, edge cases, insufficient data)

- [x] Task 4: Quality Scoring Weight Adjuster (AC: 2, 5)
  - [x]4.1 Create `WeightAdjuster` in `core/analytics/weight_adjuster.py`
    - Constructor: `VarianceAnalyzer`, `FeedbackLoopRepository`, `QualityScoringConfig`
    - `propose_weight_adjustment() -> Optional[WeightAdjustmentProposal]`
      - Calls `VarianceAnalyzer.run_correlation_analysis()`
      - Compares recommended_weights to current config weights
      - Returns proposal with before/after/rationale if delta > threshold (5% change)
      - Returns None if no significant adjustment needed
    - `apply_adjustment(record_id: UUID) -> WeightAdjustmentRecord`
      - Marks record as applied (operator-triggered, NOT auto-applied)
      - Logs the change
  - [x]4.2 DTO: `WeightAdjustmentProposal` frozen dataclass with `current_weights`, `proposed_weights`, `correlations`, `change_rationale` (list[str])
  - [x]4.3 Write adjuster tests (target: 15+ tests)

- [x] Task 5: Feedback Loop Service (Orchestrator) (AC: 1, 4, 6)
  - [x]5.1 Create `FeedbackLoopService` in `core/analytics/feedback_loop_service.py`
    - Constructor: `ContentPerformanceAnalyzer`, `WeightAdjuster`, `FeedbackLoopRepository`, `QualityScoringRepository`, `FeedbackLoopConfig`
    - `run_weekly_analysis() -> FeedbackReport`
      1. Check post count >= `min_posts_threshold` (config, default 100)
      2. Run content type analysis (graceful: catch + mark missing)
      3. Run posting time analysis (graceful: catch + mark missing)
      4. Run hashtag analysis (graceful: catch + mark missing)
      5. Run weight adjustment proposal (graceful: catch + mark missing)
      6. Generate strategy recommendations from all available data
      7. Compose and save FeedbackReport
      8. Return report
    - `generate_recommendations(content: ContentTypeAnalysis, time: TimeSlotAnalysis, hashtags: HashtagAnalysis) -> list[str]`
      - Rule-based recommendations (NO LLM call)
      - Examples: "Increase reel content (avg score 8.2 vs 6.1 for images)", "Best posting time: Tuesday 18:00-19:00 (avg 7.8)"
  - [x]5.2 Write service tests (target: 20+ tests including partial failure scenarios)

- [x] Task 6: ARQ Weekly Job + Configuration (AC: 1)
  - [x]6.1 Add `FeedbackLoopConfig` frozen dataclass to `core/config.py`
    - Fields: `min_posts_threshold` (int, default 100), `weight_change_threshold` (float, default 0.05), `min_hashtag_posts` (int, default 3), `top_hashtags_limit` (int, default 20), `enabled` (bool, default True)
    - Builder: `_build_feedback_loop_config()` reading from `dawo_analytics.json["feedback_loop"]`
    - Add `feedback_loop: FeedbackLoopConfig` to main `Config` class
  - [x]6.2 Add `"feedback_loop"` section to `config/dawo_analytics.json`
    ```json
    "feedback_loop": {
      "min_posts_threshold": 100,
      "weight_change_threshold": 0.05,
      "min_hashtag_posts": 3,
      "top_hashtags_limit": 20,
      "enabled": true
    }
    ```
  - [x]6.3 Add `_run_feedback_loop(ctx)` ARQ job to `core/scheduling/jobs.py`
    - Weekly cron: Sunday 04:00 UTC (after daily scoring at 03:00)
    - Lazy imports to avoid circular dependencies
    - Returns `{"status": "complete"/"partial"/"skipped", "posts_analyzed": int, "recommendations": int}`
    - If `enabled=False` or insufficient posts, return early with "skipped"
  - [x]6.4 Register in `WorkerSettings.functions` and `WorkerSettings.cron_jobs`
  - [x]6.5 Write config + job tests (target: 12+ tests)

- [x] Task 7: Registration + Exports (AC: all)
  - [x]7.1 Register in `teams/dawo/team_spec.py`:
    - `RegisteredService(name="feedback_loop_repository", service_class=FeedbackLoopRepository, capabilities=["analytics", "feedback_storage"], requires_session=True)`
    - `RegisteredService(name="content_performance_analyzer", service_class=ContentPerformanceAnalyzer, capabilities=["analytics", "performance_analysis"], requires_session=False)`
    - `RegisteredService(name="weight_adjuster", service_class=WeightAdjuster, capabilities=["analytics", "weight_management"], requires_session=False)`
    - `RegisteredService(name="feedback_loop_service", service_class=FeedbackLoopService, capabilities=["analytics", "feedback_loop"], requires_session=False)`
  - [x]7.2 Update `core/analytics/__init__.py` with all new exports in `__all__`
  - [x]7.3 Write registration tests (target: 5+ tests)

- [x] Task 8: Integration Tests (AC: all)
  - [x]8.1 Create `tests/integration/test_feedback_loop_integration.py`
    - End-to-end: seed 100+ PostPublishScoreRecords → run weekly analysis → verify report
    - Partial failure: missing metrics data → report still generated with missing sections
    - Weight proposal: seed correlated data → verify proposal generated
    - Idempotent: running twice on same week → only one report per report_date
  - [x]8.2 Target: 8+ integration tests

## Dev Notes

### Critical: What Already Exists (DO NOT Rebuild)

**Reuse from Story 7-4 (`core/analytics/quality_scoring_analyzer.py`):**
- `VarianceAnalyzer.run_correlation_analysis()` → returns `CorrelationReport` with `recommended_weights`
- `VarianceAnalyzer.analyze_outperformer()` → returns `OutperformerAnalysis`
- `VarianceAnalyzer._pearson_correlation()` — pure Python, no numpy/scipy
- `VarianceAnalyzer._recommend_weights()` — normalizes correlations to weight proposals

**Reuse from Story 7-4 (`core/analytics/quality_scoring_repository.py`):**
- `get_all_scored(limit)` → all PostPublishScoreRecords with both pre/post scores
- `get_flagged_for_review(limit)` → high-variance records
- `get_scored_count()` → count for threshold check
- `get_average_post_publish_score()` → overall average
- `get_component_averages()` → per-component averages

**Reuse from Story 7-1 (`core/analytics/`):**
- `InstagramMetricsRepository` — access to engagement metrics with timestamps
- `MetricsQueryService` — performance comparison data

**Reuse from Story 7-2 (`core/analytics/`):**
- `ClickAnalyticsService` — CTR data per post

**Reuse from Story 7-3 (`core/analytics/`):**
- `RevenueAnalyticsService` — revenue attribution per post

### Data Access Patterns

**Content Type Grouping:**
- `PostPublishScoreRecord.metrics_snapshot` contains raw data used during scoring
- Content type information may need to be extracted from the approval queue or content metadata
- If `metrics_snapshot` doesn't contain content_type directly, query the published content records
- Fallback: use `media_type` from InstagramMediaMetric (IMAGE/VIDEO/CAROUSEL_ALBUM)

**Posting Time Extraction:**
- Join `PostPublishScoreRecord` (via media_id) with `InstagramMediaMetric` (earliest snapshot per media_id)
- The baseline snapshot's `collected_at` minus 1 hour approximates publish time
- Alternative: check if publish timestamp exists in approval/scheduling records from Epic 4

**Hashtag Extraction:**
- Hashtags are part of the published caption text
- Check if captions are stored in approval queue items or content generation records
- Regex extraction: `re.findall(r'#\w+', caption_text)`
- If caption not accessible from analytics layer, note this as `"insufficient_data"` for hashtag section

### Architectural Decisions

**NO LLM Usage in Feedback Loop:**
- All analysis is pure Python statistical computation
- Recommendations are rule-based string templates (not LLM-generated)
- Register as `RegisteredService` (not `RegisteredAgent`) — no tier needed

**Operator-Initiated Weight Application:**
- Weight adjustments are PROPOSED only, never auto-applied
- Operator reviews proposal in feedback report, then triggers application
- This matches the "human-in-the-loop" principle from PRD

**Weekly Schedule Rationale:**
- Sunday 04:00 UTC — after daily scoring job (03:00 UTC Saturday night)
- Ensures all 7-day scores are calculated before analysis
- Low-traffic window for database queries

### Testing Approach (from Story 7-4 patterns)

- **Frozen dataclasses** for all DTOs — immutable results
- **Constructor injection** on all services
- **AsyncMock(spec=ServiceClass)** for protocol-based mocking
- **Tests mirror source**: `tests/core/test_analytics/test_feedback_loop_*.py`
- **Batch queries** via IN clause — no N+1
- **SQL aggregations** in database, not Python (for content type grouping, time slots)
- **Graceful degradation** tests: each analysis component can fail independently

### File Structure

```
core/analytics/
├── feedback_loop_models.py          # FeedbackReport, WeightAdjustmentRecord
├── feedback_loop_repository.py      # Data access layer
├── content_performance_analyzer.py  # Content type, posting time, hashtag analysis
├── weight_adjuster.py               # Quality scoring weight management
├── feedback_loop_service.py         # Orchestrator (weekly analysis runner)
└── __init__.py                      # Updated with new exports

tests/core/test_analytics/
├── test_feedback_loop_models.py     # ~20 tests
├── test_feedback_loop_repository.py # ~15 tests
├── test_content_performance.py      # ~25 tests
├── test_weight_adjuster.py          # ~15 tests
├── test_feedback_loop_service.py    # ~20 tests
├── test_feedback_loop_config.py     # ~12 tests

tests/integration/
└── test_feedback_loop_integration.py # ~8 tests
```

### Project Structure Notes

- All new files in `core/analytics/` — consistent with Stories 7-1 through 7-4
- No new directories needed; extends existing analytics package
- Migration file follows pattern: `2026_02_26_001_create_feedback_loop_tables.py`
- Config extends existing `dawo_analytics.json` with new `"feedback_loop"` section

### Previous Story Learnings (from 7-4)

- **Pure Python only**: No numpy, scipy, or external ML libraries. Pearson correlation already implemented.
- **Graceful degradation**: Neutral defaults (5.0) when data sources fail — apply same pattern here with `"insufficient_data"` sections.
- **Comment sentiment**: Keyword-based, ~180 words. No external NLP.
- **Config builder quirk**: Use literal default dict instead of `field(default_factory=...)` for frozen dataclass defaults.
- **Component scores in JSONB**: Access via `record.component_scores[name]["weighted_score"]`.
- **Daily ARQ job pattern**: Lazy imports, return status dict, register in WorkerSettings.

### Anti-Patterns to Avoid

- **DO NOT** use numpy, scipy, pandas, or any external data analysis library
- **DO NOT** auto-apply weight changes — always propose for operator review
- **DO NOT** make LLM calls for analysis — pure statistical computation only
- **DO NOT** load config files directly — use constructor injection via `FeedbackLoopConfig`
- **DO NOT** use `getattr` on user-supplied fields (SQL injection risk from Story 6-9)
- **DO NOT** create N+1 queries — use batch queries with IN clause for grouped analysis
- **DO NOT** skip `__all__` exports in any `__init__.py`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.5]
- [Source: _bmad-output/planning-artifacts/prd.md#Performance Tracking, Feedback Loop]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Organization, Performance Team]
- [Source: core/analytics/quality_scoring_analyzer.py — VarianceAnalyzer, CorrelationReport]
- [Source: core/analytics/quality_scoring_repository.py — scored post queries]
- [Source: core/scheduling/jobs.py — ARQ cron job pattern]
- [Source: core/config.py — QualityScoringConfig pattern]
- [Source: config/dawo_analytics.json — config structure]
- [Source: teams/dawo/team_spec.py — RegisteredService pattern]
- [Source: _bmad-output/implementation-artifacts/7-4-post-publish-quality-scoring.md — previous story context]
- [Source: _bmad-output/project-context.md — project rules and conventions]

## Dev Agent Record

### Agent Model Used
claude-opus-4-6 (CR pass — adversarial code review with auto-fix)

### Debug Log References
- CR session 2026-02-24: 13 findings (3C, 4H, 4M, 2L), all auto-fixed

### Completion Notes List
- C1: Dev Agent Record was empty — populated
- C2: AC3 source performance tracking was missing — added `SourceRanking`, `SourcePerformanceAnalysis` DTOs and `analyze_source_performance()` method with weight adjustments
- C3: `_build_feedback_service()` raised `NotImplementedError` — rewrote `_run_feedback_loop` with inline dependency construction (matches `_run_post_publish_scoring` pattern)
- H1: Replaced unsafe `getattr` with `hasattr` + direct attribute access in content type analysis
- H2: Added `FeedbackLoopConfig` type hint to `FeedbackLoopService.__init__` config parameter
- H3: Fixed duplicate `TestApplyAdjustment` class — renamed first to `TestProposalRationale`, kept second with unique apply tests
- H4: Clarified `apply_adjustment` None return docstring (intentional design)
- M1: Made analysis `limit` parameter configurable (default `DEFAULT_ANALYSIS_LIMIT = 2000`)
- M2: Added 6 source performance tests + 5 DTO tests to `test_content_performance.py` (32 total, target 25+)
- M3: Test counts verified: repository 15+, config 12+, adjuster 18+, service 29+
- M4: Removed trivial `_analysis_to_json` wrapper — using `asdict()` directly
- L1: Added `trend_direction` field to `ContentTypeRanking` with `_compute_trend()` helper
- Fixed floating-point boundary test (`abs(0.50 - 0.55) > 0.05` due to IEEE 754)
- Fixed ARQ job tests: replaced `_build_feedback_service` mocks with `sys.modules` patching for `core.database`
- Added source performance graceful degradation tests (exception + insufficient_data)
- Added `SourcePerformanceAnalysis` and `SourceRanking` to `__init__.py` exports
- 506 analytics tests passing, 0 failures

### File List
- `core/analytics/content_performance_analyzer.py` — added `SourceRanking`, `SourcePerformanceAnalysis`, `analyze_source_performance()`, `_compute_trend()`, `_compute_weight_adjustment()`, configurable `limit` param, `hasattr` fix
- `core/analytics/feedback_loop_service.py` — added source performance step (AC3), `FeedbackLoopConfig` type hint, removed `_analysis_to_json` wrapper
- `core/analytics/weight_adjuster.py` — updated `apply_adjustment` docstring
- `core/analytics/__init__.py` — added `SourcePerformanceAnalysis`, `SourceRanking` exports
- `core/scheduling/jobs.py` — rewrote `_run_feedback_loop` with inline deps, removed `_build_feedback_service`
- `tests/core/test_analytics/test_content_performance.py` — added `TestAnalyzeSourcePerformance` (6 tests), DTO tests for `SourceRanking`, `SourcePerformanceAnalysis`, `trend_direction` (5 tests)
- `tests/core/test_analytics/test_feedback_loop_service.py` — added source performance mock to happy path, graceful degradation tests (2 tests), updated all-fail test
- `tests/core/test_analytics/test_feedback_loop_config.py` — rewrote ARQ job tests with `sys.modules` patching
- `tests/core/test_analytics/test_weight_adjuster.py` — renamed duplicate class to `TestProposalRationale`, fixed boundary test
- `tests/core/test_analytics/test_feedback_loop_registration.py` — added `SourcePerformanceAnalysis` and `SourceRanking` export tests
