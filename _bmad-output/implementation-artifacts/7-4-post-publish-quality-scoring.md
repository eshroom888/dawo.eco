# Story 7.4: Post-Publish Quality Scoring

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want posts scored after publish based on actual performance,
so that I can validate pre-publish quality predictions and improve future content.

## Acceptance Criteria

1. **AC1 - Performance Score Calculation**: Given post metrics are collected at 7 days, When the post-publish scorer runs, Then it calculates an actual performance score (1-10) based on: engagement rate vs average (30%), reach vs average (20%), click-through rate (20%), conversions attributed (15%), comments sentiment positive/negative (15%)
2. **AC2 - Variance Recording**: Given a post-publish score is calculated, When compared to the pre-publish quality score, Then the variance is recorded (predicted vs actual), And large variances (>3 points) are flagged for review
3. **AC3 - Correlation Analysis**: Given variance data accumulates, When 50+ posts have both pre- and post-publish scores, Then correlation analysis runs automatically, And quality scorer weight adjustments are recommended
4. **AC4 - Success Pattern Identification**: Given a post significantly outperforms its prediction, When I review it, Then I see what made it successful (component breakdown), suggested learnings, And similar high-performing content patterns are identified

## Tasks / Subtasks

- [x] Task 1: Database model and migration (AC: #1, #2)
  - [x] 1.1 Create `PostPublishScoreRecord` SQLAlchemy model in `core/analytics/quality_scoring_models.py`
  - [x] 1.2 Create Alembic migration `2026_02_25_001_create_post_publish_scores.py`
  - [x] 1.3 Write model unit tests (26 tests)

- [x] Task 2: Quality Scoring Repository (AC: #1, #2, #3, #4)
  - [x] 2.1-2.9 All repository methods implemented
  - [x] 2.10 Write repository tests (17 tests)

- [x] Task 3: Comment Sentiment Scorer (AC: #1)
  - [x] 3.1 Added `get_comments()` + `InstagramComment` to `integrations/instagram/client.py`
  - [x] 3.2 Created `CommentSentimentScorer` with ~100 positive + ~80 negative Norwegian+English words
  - [x] 3.3 Created `CommentSentimentResult` frozen dataclass
  - [x] 3.4 Wrote sentiment scorer tests (23 tests)

- [x] Task 4: Post-Publish Scoring Service (AC: #1, #2)
  - [x] 4.1-4.6 All service methods, dataclasses, batch scoring, and graceful degradation implemented
  - [x] 4.7 Wrote scoring service tests (18 tests)

- [x] Task 5: Variance Analyzer (AC: #2, #4)
  - [x] 5.1-5.7 All variance analysis methods, dataclasses, and tests implemented

- [x] Task 6: Correlation Analyzer (AC: #3)
  - [x] 6.1-6.5 Pure Python Pearson correlation, CorrelationReport, weight recommendations, tests (14 tests total for Tasks 5+6)

- [x] Task 7: ARQ Job and Configuration (AC: #1, #3)
  - [x] 7.1 Added `quality_scoring` section to `config/dawo_analytics.json`
  - [x] 7.2 Created `QualityScoringConfig`, `CTRScale`, `ConversionScale` frozen dataclasses
  - [x] 7.3 Wired `_build_quality_scoring_config()` into Config + get_config()
  - [x] 7.4 Created `_run_post_publish_scoring` ARQ job (daily at 03:00 UTC)
  - [x] 7.5 Added cron entry to WorkerSettings
  - [x] 7.6 Wrote config + job tests (19 tests)

- [x] Task 8: Registration and exports (AC: all)
  - [x] 8.1 Registered 4 services in `teams/dawo/team_spec.py`
  - [x] 8.2 Updated `core/analytics/__init__.py` with 13 new exports
  - [x] 8.3 Updated `integrations/instagram/__init__.py` with `InstagramComment`

- [x] Task 9: Integration tests (AC: all)
  - [x] 9.1 End-to-end scoring flow (full pipeline)
  - [x] 9.2 Partial data graceful degradation (2 tests)
  - [x] 9.3 Variance flagging (large + small variance)
  - [x] 9.4 Outperformer analysis with component breakdown
  - [x] 9.5 Correlation trigger (50+ records + below threshold)
  - Total: 8 integration tests

## Dev Notes

### Pre-Publish Score Source

The pre-publish quality score comes from `ContentQualityScorer` (Story 3.7, `teams/dawo/generators/content_quality/agent.py`). The `QualityScoreResult.total_score` is the number to compare against post-publish. This score is stored in the approval queue system (Epic 4) when content enters the approval pipeline. The ARQ job must look up the pre-publish score from the approval item's stored quality_score when calculating post-publish scores.

**Pre-publish score weights** (from `content_quality/schemas.py`):
```python
DEFAULT_WEIGHTS = {
    "compliance": 0.25,
    "brand_voice": 0.20,
    "visual_quality": 0.15,
    "platform": 0.15,
    "engagement": 0.15,
    "authenticity": 0.10,
}
```

The correlation analysis (Task 6) compares these pre-publish component weights against actual post-publish performance to recommend weight adjustments.

### Post-Publish Score Component Mapping

| Component | Weight | Data Source | Mapping Logic |
|-----------|--------|-------------|---------------|
| engagement_vs_avg | 0.30 | `MetricsQueryService.get_performance_comparison()` | Map `total_interactions_vs_avg` percentage to 1-10 scale |
| reach_vs_avg | 0.20 | `MetricsQueryService.get_performance_comparison()` | Map `reach_vs_avg` percentage to 1-10 scale |
| click_through_rate | 0.20 | `ClickAnalyticsService.get_post_analytics()` | Map CTR% via configurable scale (5%=10, 0%=1) |
| conversions | 0.15 | `RevenueAnalyticsService.get_post_revenue()` | Map order_count via configurable scale (5+=10, 0=2) |
| comment_sentiment | 0.15 | `CommentSentimentScorer.score_comments()` | Direct 0-10 from keyword-based analysis |

**Percentage-to-score mapping** (for engagement and reach):
```python
def _pct_to_score(pct_vs_avg: float) -> float:
    """Map percentage vs average to 1-10 scale.

    +100% above avg = 10, exactly average (0%) = 5, -100% below = 1.
    Clamped to [1.0, 10.0].
    """
    score = 5.0 + (pct_vs_avg / 100.0) * 5.0
    return max(1.0, min(10.0, round(score, 1)))
```

### Instagram Comments API

**Endpoint**: `GET /{media_id}/comments?fields=id,text,timestamp,username&limit=100`

**Key considerations**:
- Shares the 200 req/hour rate limit budget with metrics collection
- Cursor-based pagination (handle `after` cursor if > 100 comments)
- Must add to existing `integrations/instagram/client.py` following the same pattern as `get_media_insights()`
- `InstagramComment` frozen dataclass goes in `integrations/instagram/client.py` alongside existing DTOs

### Comment Sentiment Approach

**Keyword-based** (NO external dependencies, NO ML libraries):
- Built-in Norwegian + English word lists (~180 total words) as class constants
- Simple word tokenization: `text.lower().split()` + strip punctuation
- Negation handling: "ikke"/"not"/"no" preceding a sentiment word flips polarity
- Score mapping: `sentiment_ratio = positive / (positive + negative)` → scale to 0-10
- If zero comments: return neutral score 5.0

This follows the project's hybrid regex+LLM pattern (Story 6-6) but simpler — keywords only, no LLM needed for basic sentiment classification.

### Graceful Degradation (CRITICAL)

Each data source can fail independently. The scorer MUST NOT fail if one source is unavailable:
- No metrics? → engagement_vs_avg = 5.0, reach_vs_avg = 5.0
- No click data? → click_through_rate = 5.0
- No revenue data? → conversions = 5.0 (neutral, not zero — absence of revenue is different from poor revenue)
- No comments or Instagram unavailable? → comment_sentiment = 5.0
- Log which components used fallback values in `metrics_snapshot`

This matches the project's graceful degradation pattern (Story 1.5, Story 7-10).

### Correlation Analysis (Pure Python)

No numpy or scipy — use pure Python Pearson correlation (Task 6.3). The analysis:
1. Loads all 50+ scored posts with both pre-publish and post-publish scores
2. For each pre-publish component weight, computes correlation with actual post_publish_score
3. High correlation (>0.5) → component is predictive → increase weight
4. Low correlation (<0.2) → component is not predictive → decrease weight
5. Negative correlation → component is anti-predictive → flag for investigation

Output is a `CorrelationReport` with recommended weight adjustments. These are **recommendations only** — the operator must review and apply them manually (or via a future story).

### Project Structure Notes

**New files to create:**
```
core/analytics/
├── quality_scoring_models.py      # PostPublishScoreRecord SQLAlchemy model
├── quality_scoring_repository.py  # QualityScoringRepository (data access)
├── quality_scoring_service.py     # PostPublishScoringService (core scoring logic)
├── quality_scoring_analyzer.py    # VarianceAnalyzer + CorrelationAnalyzer
└── comment_sentiment.py           # CommentSentimentScorer (keyword-based)

migrations/versions/
└── 2026_02_25_001_create_post_publish_scores.py

tests/core/test_analytics/
├── test_quality_scoring_models.py
├── test_quality_scoring_repository.py
├── test_quality_scoring_service.py
├── test_quality_scoring_analyzer.py
└── test_comment_sentiment.py

tests/integration/
└── test_post_publish_scoring_e2e.py
```

**Files to modify:**
```
integrations/instagram/client.py   # Add get_comments() method
core/config.py                     # Add QualityScoringConfig dataclass
config/dawo_analytics.json         # Add quality_scoring section
core/scheduling/jobs.py            # Add _run_post_publish_scoring ARQ job + cron
teams/dawo/team_spec.py            # Register 4 new services
core/analytics/__init__.py         # Update __all__ exports
```

**Alignment**: Follows `core/analytics/` organization (same as 7-1 models/repository/service, 7-2 click analytics, 7-3 revenue analytics). New sentiment scorer is standalone in `core/analytics/` since it's analytics infrastructure, not a scanner/generator.

### Existing Code to Reuse (DO NOT REINVENT)

| Component | Location | Reuse For |
|-----------|----------|-----------|
| `MetricsQueryService` | `core/analytics/metrics_query.py` | Engagement/reach vs average (`.get_performance_comparison()`) |
| `ClickAnalyticsService` | `core/analytics/click_analytics.py` | CTR data (`.get_post_analytics()`) |
| `RevenueAnalyticsService` | `core/analytics/revenue_analytics.py` | Conversion data (`.get_post_revenue()`) |
| `InstagramMetricsRepository` | `core/analytics/repository.py` | Pattern for save/query methods |
| `PerformanceComparison` | `core/analytics/metrics_query.py` | Dataclass with `*_vs_avg` percentage fields |
| `PostAnalyticsSummary` | `core/analytics/revenue_analytics.py` | Combined analytics pattern |
| `CollectionResult` pattern | `core/analytics/metrics_collector.py` | Pattern for `PostPublishScoreResult` |
| `AnalyticsConfig` | `core/config.py` | Pattern for `QualityScoringConfig` frozen dataclass |
| `_run_shopify_attribution_poll` | `core/scheduling/jobs.py` | Pattern for daily cron job |
| `RegisteredService` | `teams/dawo/team_spec.py` | Service registration (no LLM tier) |
| `ContentQualityScorer.DEFAULT_WEIGHTS` | `teams/dawo/generators/content_quality/schemas.py` | Pre-publish weight reference for correlation analysis |
| Batch query pattern | `core/analytics/repository.py:get_by_media_ids()` | IN clause batch queries |
| Partial failure pattern | `core/analytics/metrics_collector.py:collect_batch()` | Batch scoring with per-post error handling |

### Critical Patterns from Stories 7-1, 7-2, 7-3

**From Story 7-1 (88 tests):**
- `MetricsQueryService.get_performance_comparison()` returns `PerformanceComparison` with percentage fields like `impressions_vs_avg`, `reach_vs_avg`, `total_interactions_vs_avg`
- Snapshot-delta pattern: raw values stored, aggregates computed at query time
- `get_average_metrics(days_back=30)` — filters on `snapshot_label == "7d"`

**From Story 7-2 (94 tests):**
- `ClickAnalyticsService.get_post_analytics()` returns `PostClickAnalytics` with `total_clicks`, `ctr`
- CTR formula: `clicks / latest_impressions` (integrates with MetricsQueryService)
- Fire-and-forget pattern, partial failure handling

**From Story 7-3 (102 tests):**
- `RevenueAnalyticsService.get_post_revenue()` returns `PostRevenueResult` with `order_count`, `attributed_revenue`
- `get_combined_analytics()` merges all three stories — post-publish scorer follows same aggregation pattern
- `RegisteredService` registration (no LLM tier)

**Carry forward:**
- All result types are frozen dataclasses
- Constructor injection on everything
- Protocol-based interfaces for testability
- Partial failure handling in batch operations
- Tests mirror source: `tests/core/test_analytics/` matches `core/analytics/`
- Batch queries via IN clause (no N+1)
- SQL aggregations in database, not in-memory Python

### Anti-Patterns to Avoid

- **NO external ML/NLP libraries** for sentiment — pure keyword-based Python only (no nltk, spacy, transformers)
- **NO numpy/scipy** for correlation — pure Python implementation
- **NO direct Instagram API calls** — all go through `integrations/instagram/client.py` which uses retry middleware
- **NO `getattr()` on user-supplied fields** — SQL injection risk (caught in 6-9)
- **NO in-memory filtering** — all aggregations in SQL (repository handles averages, counts)
- **NO N+1 queries** — batch with IN clause (get_by_post_ids pattern)
- **NO hardcoded model names** — this story has no LLM, only RegisteredService
- **NO failing the entire score on one missing data source** — graceful degradation with neutral defaults
- **NO storing raw comment text** — only store sentiment aggregates (GDPR consideration)

### Testing Standards

- TDD: red-green-refactor cycle
- Target: ~90-100 tests across 7 test files
- Mocking: `AsyncMock(spec=MetricsQueryService)`, `AsyncMock(spec=ClickAnalyticsService)`, etc. with Protocol pattern
- Integration tests: full post-publish scoring pipeline
- Edge cases: no metrics, no clicks, no revenue, no comments, zero-comment posts, negative sentiment, all-neutral sentiment, exactly 50 posts for correlation trigger, < 50 posts returns None, pre-publish score missing
- Test data: use factory functions returning frozen dataclasses (consistent with 7-1/7-2/7-3)

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 7, Story 7.4]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error Handling: Retry + Graceful Degradation]
- [Source: _bmad-output/implementation-artifacts/7-1-instagram-engagement-metrics-collection.md — MetricsQueryService, PerformanceComparison]
- [Source: _bmad-output/implementation-artifacts/7-2-utm-click-through-tracking.md — ClickAnalyticsService, CTR computation]
- [Source: _bmad-output/implementation-artifacts/7-3-shopify-sales-attribution.md — RevenueAnalyticsService, PostAnalyticsSummary]
- [Source: teams/dawo/generators/content_quality/schemas.py — Pre-publish DEFAULT_WEIGHTS, QualityScoreResult]
- [Source: teams/dawo/generators/content_quality/agent.py — ContentQualityScorer orchestration pattern]
- [Source: core/analytics/metrics_query.py — PerformanceComparison with percentage fields]
- [Source: core/analytics/click_analytics.py — PostClickAnalytics, CTR formula]
- [Source: core/analytics/revenue_analytics.py — PostRevenueResult, get_combined_analytics()]
- [Source: core/analytics/repository.py — InstagramMetricsRepository batch query patterns]
- [Source: core/config.py — AnalyticsConfig, UTMConfig, AttributionConfig frozen dataclass patterns]
- [Source: core/scheduling/jobs.py — ARQ cron job patterns, _schedule_post_metrics()]
- [Source: core/publishing/events.py — PublishEventEmitter for future event integration]
- [Source: docs/project-context.md — Registration rules, DI patterns, anti-patterns]
- [Source: Instagram Graph API — GET /{media-id}/comments endpoint, 200 req/hr rate limit]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — all tests pass on first or second attempt.

### Completion Notes List

- 125 tests across 8 test files (26 model + 17 repository + 23 sentiment + 18 service + 14 analyzer + 12 config + 7 job + 8 integration)
- Graceful degradation pattern: neutral score (5.0) when data sources fail, controlled by `fallback` flag in data dicts
- Pure Python Pearson correlation (no numpy/scipy) validated with synthetic data
- Keyword-based sentiment analysis with ~180 Norwegian+English words, negation handling
- ARQ cron job runs daily at 03:00 UTC, queries posts past scoring_delay_days window
- Config builder fix: `field(default_factory=...)` not accessible as class attribute — used literal default dict instead

### File List

**New files created:**
- `core/analytics/quality_scoring_models.py` — PostPublishScoreRecord SQLAlchemy model
- `core/analytics/quality_scoring_repository.py` — QualityScoringRepository (data access)
- `core/analytics/quality_scoring_service.py` — PostPublishScoringService (scoring engine)
- `core/analytics/quality_scoring_analyzer.py` — VarianceAnalyzer + CorrelationReport
- `core/analytics/comment_sentiment.py` — CommentSentimentScorer (keyword-based)
- `migrations/versions/2026_02_25_001_create_post_publish_scores.py` — Alembic migration
- `tests/core/test_analytics/test_quality_scoring_models.py` — 26 tests
- `tests/core/test_analytics/test_quality_scoring_repository.py` — 17 tests
- `tests/core/test_analytics/test_quality_scoring_service.py` — 18 tests
- `tests/core/test_analytics/test_quality_scoring_analyzer.py` — 14 tests
- `tests/core/test_analytics/test_comment_sentiment.py` — 23 tests
- `tests/core/test_analytics/test_quality_scoring_config.py` — 12 tests
- `tests/core/test_analytics/test_quality_scoring_job.py` — 7 tests
- `tests/integration/test_quality_scoring_integration.py` — 8 tests

**Files modified:**
- `integrations/instagram/client.py` — Added `InstagramComment`, `get_comments()`, `InstagramPublishClientProtocol.get_comments()`
- `integrations/instagram/__init__.py` — Added `InstagramComment` export
- `core/config.py` — Added `QualityScoringConfig`, `CTRScale`, `ConversionScale`, `_build_quality_scoring_config()`
- `config/dawo_analytics.json` — Added `quality_scoring` section
- `core/scheduling/jobs.py` — Added `_run_post_publish_scoring` ARQ job + cron entry at 03:00 UTC
- `core/analytics/__init__.py` — Added 13 new exports for Story 7-4
- `teams/dawo/team_spec.py` — Registered 4 new `RegisteredService` entries
