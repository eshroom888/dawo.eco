# Story 3.7: Content Quality Scoring

Status: done

---

## Story

As an **operator**,
I want content scored for quality before I review it,
So that I can prioritize high-quality posts and identify weak ones.

---

## Acceptance Criteria

1. **Given** a content item is ready for queue
   **When** the quality scorer evaluates it
   **Then** it calculates a score (1-10) based on:
   - Compliance status (25%): COMPLIANT=full, WARNING=-2, REJECTED=0
   - Brand voice match (20%): from Brand Voice Validator
   - Visual quality (15%): from image quality score
   - Platform optimization (15%): hashtags, length, format fit
   - Engagement prediction (15%): based on past performance data
   - Authenticity (10%): human feel vs AI-generic

2. **Given** AI detectability is evaluated
   **When** content shows AI patterns
   **Then** authenticity score is reduced
   **And** specific AI markers are flagged (generic phrasing, perfect structure)

3. **Given** quality score is calculated
   **When** content enters approval queue
   **Then** score is displayed prominently
   **And** items are sorted by score (highest first)

---

## Tasks / Subtasks

- [x] Task 1: Create ContentQualityScorer package structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/generators/content_quality/` package
  - [x] 1.2 Implement `ContentQualityScorerProtocol` for testability
  - [x] 1.3 Implement `ContentQualityScorer` class with constructor injection pattern
  - [x] 1.4 Accept `EUComplianceChecker`, `BrandVoiceValidator`, `LLMClient` via injection
  - [x] 1.5 Create `QualityScoreRequest` and `QualityScoreResult` dataclasses
  - [x] 1.6 Export all types in `__init__.py` with complete `__all__` list

- [x] Task 2: Implement component score calculations (AC: #1)
  - [x] 2.1 Create `ComplianceScorer` - 25% weight (COMPLIANT=10, WARNING=8, REJECTED=0)
  - [x] 2.2 Create `BrandVoiceScorer` - 20% weight (from BrandVoiceValidator result)
  - [x] 2.3 Create `VisualQualityScorer` - 15% weight (from image quality score input)
  - [x] 2.4 Create `PlatformOptimizationScorer` - 15% weight (hashtags, length, format)
  - [x] 2.5 Create `EngagementPredictionScorer` - 15% weight (historical data lookup)
  - [x] 2.6 Create `AuthenticityScorer` - 10% weight (AI detectability check)

- [x] Task 3: Implement AI detectability analysis (AC: #2)
  - [x] 3.1 Create `AIDetectabilityAnalyzer` class for pattern detection
  - [x] 3.2 Implement generic phrasing detection (overused AI phrases)
  - [x] 3.3 Implement structure analysis (too-perfect formatting)
  - [x] 3.4 Implement vocabulary diversity check (limited word variation)
  - [x] 3.5 Return `AuthenticityResult` with score and flagged patterns
  - [x] 3.6 Use tier="generate" for LLM-based authenticity checks

- [x] Task 4: Implement platform optimization checks (AC: #1)
  - [x] 4.1 Validate hashtag count (optimal 5-15 for Instagram)
  - [x] 4.2 Check caption length (180-220 words for DAWO standard)
  - [x] 4.3 Validate format fit (feed post vs story vs reel requirements)
  - [x] 4.4 Check for required brand hashtags (#DAWO, #DAWOmushrooms)
  - [x] 4.5 Validate CTA presence and placement
  - [x] 4.6 Return `PlatformOptimizationResult` with score and suggestions

- [x] Task 5: Implement engagement prediction (AC: #1)
  - [x] 5.1 Create `EngagementPredictor` class with historical data access
  - [x] 5.2 Analyze content type performance (topic, length, hashtags)
  - [x] 5.3 Factor in posting time optimization
  - [x] 5.4 Consider source type (research, trending, evergreen)
  - [x] 5.5 Fallback to default score (5.0) when insufficient historical data
  - [x] 5.6 Return `EngagementPrediction` with score and confidence level

- [x] Task 6: Implement weighted aggregation (AC: #1, #3)
  - [x] 6.1 Implement `calculate_total_score()` with configurable weights
  - [x] 6.2 Default weights: compliance=0.25, brand=0.20, visual=0.15, platform=0.15, engagement=0.15, authenticity=0.10
  - [x] 6.3 Allow weight override via config injection
  - [x] 6.4 Round final score to 1 decimal place
  - [x] 6.5 Include component breakdown in result for transparency
  - [x] 6.6 Validate weights sum to 1.0 on initialization

- [x] Task 7: Implement schemas for data structures
  - [x] 7.1 Create `QualityScoreRequest` with content, assets, metadata
  - [x] 7.2 Create `QualityScoreResult` with total score and component breakdown
  - [x] 7.3 Create `ComponentScore` for individual scorer results
  - [x] 7.4 Create `AuthenticityResult` with AI markers and score
  - [x] 7.5 Create `PlatformOptimizationResult` with checks and suggestions
  - [x] 7.6 Create `EngagementPrediction` with score and confidence

- [x] Task 8: Register ContentQualityScorer in team_spec.py (AC: #1, #3)
  - [x] 8.1 Add `ContentQualityScorer` as RegisteredAgent with tier="generate"
  - [x] 8.2 Add capability tags: "content_quality", "quality_scoring", "content_evaluation"
  - [x] 8.3 Update `teams/dawo/generators/__init__.py` with exports

- [x] Task 9: Create unit tests
  - [x] 9.1 Test compliance scoring for each status (COMPLIANT, WARNING, REJECTED)
  - [x] 9.2 Test brand voice scoring with mock validator
  - [x] 9.3 Test visual quality scoring with various quality inputs
  - [x] 9.4 Test platform optimization with valid/invalid content
  - [x] 9.5 Test engagement prediction with and without historical data
  - [x] 9.6 Test authenticity scoring for AI-generated vs human-like content
  - [x] 9.7 Test weighted aggregation with custom weights
  - [x] 9.8 Test score rounding and edge cases (0, 10, boundary values)

- [x] Task 10: Create integration tests
  - [x] 10.1 Test end-to-end scoring with real validators
  - [x] 10.2 Test with sample content from previous stories
  - [x] 10.3 Test score consistency (same content = same score)
  - [x] 10.4 Test performance (< 10 seconds per content item)

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story creates the Content Quality Scorer that integrates with existing validators and content generators. Follow existing patterns from:
- `teams/dawo/validators/eu_compliance/` - Compliance checker integration
- `teams/dawo/validators/brand_voice/` - Brand voice validation integration
- `teams/dawo/generators/compliance_rewrite/` - Generator agent pattern with schemas

**Key Pattern:** This is a **generator** agent (produces output - quality scores) that orchestrates multiple validators. It aggregates scores from various sources into a unified quality metric.

### Existing Validator Interfaces (MUST USE)

**Source:** [teams/dawo/validators/eu_compliance/], [teams/dawo/validators/brand_voice/]

```python
# EU Compliance Checker (from Story 1.2)
from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ContentComplianceCheck,
    OverallStatus,  # COMPLIANT, WARNING, REJECTED
    ComplianceStatus,  # PROHIBITED, BORDERLINE, PERMITTED
)

# Brand Voice Validator (from Story 1.3)
from teams.dawo.validators.brand_voice import (
    BrandVoiceValidator,
    BrandValidationResult,  # PASS, NEEDS_REVISION, FAIL
    BrandProfile,
)

# Map validator outputs to scores:
COMPLIANCE_SCORE_MAP = {
    OverallStatus.COMPLIANT: 10.0,
    OverallStatus.WARNING: 8.0,  # -2 from full as per AC
    OverallStatus.REJECTED: 0.0,
}

BRAND_VOICE_SCORE_MAP = {
    "PASS": 10.0,
    "NEEDS_REVISION": 6.0,
    "FAIL": 2.0,
}
```

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
teams/dawo/generators/
├── __init__.py                       # Add ContentQualityScorer exports
├── content_quality/                  # NEW package
│   ├── __init__.py                   # Package exports with __all__
│   ├── agent.py                      # ContentQualityScorer class
│   ├── schemas.py                    # Request/Result dataclasses
│   ├── scorers/                      # Individual scoring components
│   │   ├── __init__.py
│   │   ├── compliance.py             # ComplianceScorer
│   │   ├── brand_voice.py            # BrandVoiceScorer
│   │   ├── visual_quality.py         # VisualQualityScorer
│   │   ├── platform.py               # PlatformOptimizationScorer
│   │   ├── engagement.py             # EngagementPredictionScorer
│   │   └── authenticity.py           # AuthenticityScorer + AIDetectabilityAnalyzer
│   └── prompts.py                    # AI detectability prompts
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

```python
# CORRECT: Use tier name for registration
tier=TIER_GENERATE  # Maps to Sonnet for quality judgment accuracy

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - "claude-haiku", "claude-sonnet", "claude-opus"
# - Any hardcoded model IDs
```

### Quality Score Schema Design

**Source:** Design based on AC requirements

```python
# schemas.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class ContentType(Enum):
    """Content format type."""
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_REEL = "instagram_reel"

@dataclass
class ComponentScore:
    """Individual component scoring result."""
    component: str              # "compliance", "brand_voice", etc.
    raw_score: float           # 0-10 score
    weight: float              # 0.0-1.0 weight
    weighted_score: float      # raw_score * weight
    details: dict[str, any]    # Component-specific details

@dataclass
class AuthenticityResult:
    """AI detectability analysis result."""
    authenticity_score: float          # 0-10 (higher = more human-like)
    ai_probability: float              # 0.0-1.0 probability of AI generation
    flagged_patterns: list[str]        # E.g., ["generic_phrasing", "perfect_structure"]
    vocabulary_diversity: float        # 0.0-1.0 word variation score
    analysis_confidence: float         # 0.0-1.0 confidence in analysis

@dataclass
class PlatformOptimizationResult:
    """Platform-specific optimization check result."""
    optimization_score: float          # 0-10
    hashtag_score: float              # 0-10 (count, relevance)
    length_score: float               # 0-10 (within target range)
    format_score: float               # 0-10 (matches content type)
    brand_hashtags_present: bool
    has_cta: bool
    suggestions: list[str]            # Improvement suggestions

@dataclass
class EngagementPrediction:
    """Engagement prediction based on historical data."""
    predicted_score: float            # 0-10 expected engagement
    confidence: float                 # 0.0-1.0 prediction confidence
    similar_content_avg: Optional[float]  # Average score of similar content
    data_points: int                  # Number of historical items used

@dataclass
class QualityScoreRequest:
    """Input for quality scoring."""
    content: str                      # Caption text
    content_type: ContentType         # Feed, story, reel
    hashtags: list[str]               # Content hashtags
    visual_quality_score: float       # From image generator (0-10)
    source_type: str                  # "trending", "scheduled", "evergreen", "research"
    compliance_check: Optional[ContentComplianceCheck]  # Pre-computed if available
    brand_validation: Optional[BrandValidationResult]   # Pre-computed if available
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class QualityScoreResult:
    """Complete quality scoring result."""
    total_score: float                # Final 0-10 score (1 decimal)
    component_scores: list[ComponentScore]  # Individual component breakdowns
    authenticity: AuthenticityResult
    platform_optimization: PlatformOptimizationResult
    engagement_prediction: EngagementPrediction
    scoring_time_ms: int
    recommendations: list[str]        # Improvement suggestions
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

### AI Detectability Patterns to Check

**Source:** Design based on AC #2 and content quality research

```python
# Common AI-generated content markers
AI_PATTERN_MARKERS = {
    "generic_phrasing": [
        "in today's fast-paced world",
        "it's no secret that",
        "let's dive in",
        "first and foremost",
        "at the end of the day",
        "game-changer",
        "unlock your potential",
    ],
    "perfect_structure": {
        "list_indicators": r"^(\d+\.|•|-)\s",  # Every paragraph starts with bullet
        "uniform_length": 0.1,  # Variance threshold - too uniform is suspicious
    },
    "vocabulary_repetition": {
        "noun_repeat_threshold": 3,  # Same noun more than 3x is suspicious
        "filler_words": ["really", "very", "actually", "basically"],
    },
    "norwegian_ai_markers": [
        "i dagens moderne verden",
        "det er ingen hemmelighet at",
        "la oss dykke inn i",
        "først og fremst",
        "på slutten av dagen",
        "spillveksler",  # Literal translation of "game-changer"
    ],
}
```

### Platform Optimization Rules

**Source:** [config/dawo_brand_profile.json], Instagram best practices

```python
# Instagram platform optimization rules
PLATFORM_RULES = {
    "instagram_feed": {
        "hashtag_min": 5,
        "hashtag_max": 15,
        "hashtag_optimal": 11,
        "caption_words_min": 150,
        "caption_words_max": 250,
        "caption_words_target": 200,
        "required_hashtags": ["DAWO", "DAWOmushrooms"],
        "requires_cta": True,
    },
    "instagram_story": {
        "hashtag_min": 0,
        "hashtag_max": 5,
        "caption_words_max": 50,
        "requires_cta": False,
    },
    "instagram_reel": {
        "hashtag_min": 3,
        "hashtag_max": 10,
        "caption_words_min": 50,
        "caption_words_max": 150,
        "requires_cta": True,
    },
}
```

### Weight Configuration

**Source:** [epics.md#Story-3.7]

```python
# Default scoring weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "compliance": 0.25,      # EU compliance status
    "brand_voice": 0.20,     # Brand voice match
    "visual_quality": 0.15,  # Image quality score
    "platform": 0.15,        # Platform optimization
    "engagement": 0.15,      # Engagement prediction
    "authenticity": 0.10,    # AI detectability (inverse)
}

# Weight validation
def validate_weights(weights: dict[str, float]) -> None:
    """Ensure weights sum to 1.0."""
    total = sum(weights.values())
    if not (0.99 <= total <= 1.01):  # Allow small float error
        raise ValueError(f"Weights must sum to 1.0, got {total}")
```

### ContentQualityScorer Agent Pattern

**Source:** [teams/dawo/generators/compliance_rewrite/agent.py]

```python
# agent.py
from typing import Optional, Protocol
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from teams.dawo.validators.eu_compliance import (
    EUComplianceChecker,
    ContentComplianceCheck,
    OverallStatus,
)
from teams.dawo.validators.brand_voice import (
    BrandVoiceValidator,
    BrandValidationResult,
    BrandProfile,
)

from .schemas import (
    QualityScoreRequest,
    QualityScoreResult,
    ComponentScore,
    DEFAULT_WEIGHTS,
)
from .scorers import (
    ComplianceScorer,
    BrandVoiceScorer,
    VisualQualityScorer,
    PlatformOptimizationScorer,
    EngagementPredictionScorer,
    AuthenticityScorer,
)

logger = logging.getLogger(__name__)


class ContentQualityScorerProtocol(Protocol):
    """Protocol for content quality scorer."""

    async def score_content(
        self,
        request: QualityScoreRequest
    ) -> QualityScoreResult:
        """Calculate quality score for content."""
        ...


class ContentQualityScorer:
    """Calculates unified quality score for content items.

    Aggregates scores from multiple components (compliance, brand voice,
    visual quality, platform optimization, engagement prediction, authenticity)
    into a single 0-10 quality score with configurable weights.

    Uses the 'generate' tier (defaults to Sonnet) for AI detectability analysis.
    Configuration is received via dependency injection - NEVER loads config directly.
    """

    def __init__(
        self,
        compliance_checker: EUComplianceChecker,
        brand_validator: BrandVoiceValidator,
        llm_client: LLMClient,
        weights: Optional[dict[str, float]] = None,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            compliance_checker: EU Compliance Checker for compliance scoring
            brand_validator: Brand Voice Validator for brand alignment
            llm_client: LLM client for AI detectability analysis
            weights: Optional custom scoring weights (default: DEFAULT_WEIGHTS)
        """
        self._weights = weights or DEFAULT_WEIGHTS
        validate_weights(self._weights)

        # Initialize component scorers
        self._compliance_scorer = ComplianceScorer(compliance_checker)
        self._brand_scorer = BrandVoiceScorer(brand_validator)
        self._visual_scorer = VisualQualityScorer()
        self._platform_scorer = PlatformOptimizationScorer()
        self._engagement_scorer = EngagementPredictionScorer()
        self._authenticity_scorer = AuthenticityScorer(llm_client)

    async def score_content(
        self,
        request: QualityScoreRequest
    ) -> QualityScoreResult:
        """Calculate quality score for content.

        Args:
            request: QualityScoreRequest with content and metadata

        Returns:
            QualityScoreResult with total score and component breakdown
        """
        start_time = datetime.now(timezone.utc)
        component_scores = []
        recommendations = []

        try:
            # Score each component
            compliance = await self._score_compliance(request)
            component_scores.append(compliance)

            brand_voice = await self._score_brand_voice(request)
            component_scores.append(brand_voice)

            visual = self._score_visual_quality(request)
            component_scores.append(visual)

            platform = self._score_platform(request)
            component_scores.append(platform)
            recommendations.extend(platform.details.get("suggestions", []))

            engagement = await self._score_engagement(request)
            component_scores.append(engagement)

            authenticity = await self._score_authenticity(request)
            component_scores.append(authenticity)

            # Calculate weighted total
            total_score = sum(cs.weighted_score for cs in component_scores)
            total_score = round(total_score, 1)

            # Clamp to valid range
            total_score = max(0.0, min(10.0, total_score))

            end_time = datetime.now(timezone.utc)
            scoring_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return QualityScoreResult(
                total_score=total_score,
                component_scores=component_scores,
                authenticity=authenticity.details["result"],
                platform_optimization=platform.details["result"],
                engagement_prediction=engagement.details["prediction"],
                scoring_time_ms=scoring_time_ms,
                recommendations=recommendations,
                created_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error("Quality scoring failed: %s", e)
            raise
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-6-content-compliance-rewrite-suggestions.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export ContentQualityScorer, Protocol, all schemas |
| Config injection pattern | Accept validators, LLMClient via constructor |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all scoring errors before returning/raising |
| F-string logging anti-pattern | Use `%` formatting: `logger.error("Scoring failed: %s", e)` |
| Integration tests separate | Create test_integration.py with env var skip markers |
| TYPE_CHECKING pattern | Use TYPE_CHECKING for Protocol imports in schemas |
| Position-0 awareness | Handle edge cases in score calculations (0/0, empty lists) |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER instantiate validators internally** - Accept via constructor injection
2. **NEVER load weights from file** - Accept weights dict via injection
3. **NEVER hardcode model names** - Use tier system
4. **NEVER swallow exceptions without logging** - Log all errors
5. **NEVER return invalid scores** - Clamp 0-10, handle edge cases
6. **NEVER skip weight validation** - Validate on __init__

### Integration Points

**Source:** [epics.md#Epic-3], [architecture.md#Data-Flow]

```python
# Content Quality Scorer integrates into content pipeline:

# 1. After content generation
caption_result = await caption_generator.generate(request)

# 2. After compliance check
compliance_check = await eu_checker.check_content(caption_result.caption_text)

# 3. After brand validation
brand_validation = await brand_validator.validate(caption_result.caption_text)

# 4. Quality scoring (this story)
quality_result = await quality_scorer.score_content(
    QualityScoreRequest(
        content=caption_result.caption_text,
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=caption_result.hashtags,
        visual_quality_score=image_result.quality_score,  # From 3.4 or 3.5
        source_type="research",
        compliance_check=compliance_check,
        brand_validation=brand_validation,
    )
)

# 5. Submit to approval queue with score
await approval_manager.submit(
    content=caption_result,
    quality_score=quality_result.total_score,
    quality_breakdown=quality_result.component_scores,
)
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.content_quality import (
    ContentQualityScorer,
    ContentQualityScorerProtocol,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="content_quality_scorer",
        agent_class=ContentQualityScorer,
        capabilities=["content_quality", "quality_scoring", "content_evaluation"],
        tier=TIER_GENERATE,  # Uses Sonnet for AI detectability analysis
    ),
]
```

### Test Fixtures

**Source:** [tests/teams/dawo/generators/test_compliance_rewrite/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_content_quality/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from teams.dawo.validators.eu_compliance import (
    ContentComplianceCheck,
    OverallStatus,
)
from teams.dawo.validators.brand_voice import BrandValidationResult
from teams.dawo.generators.content_quality import (
    QualityScoreRequest,
    ContentType,
)

@pytest.fixture
def mock_compliance_checker():
    """Mock EUComplianceChecker returning COMPLIANT."""
    checker = AsyncMock()
    checker.check_content.return_value = ContentComplianceCheck(
        overall_status=OverallStatus.COMPLIANT,
        flagged_phrases=[],
        novel_food_check=None,
        compliance_score=1.0,
        llm_enhanced=False,
    )
    return checker

@pytest.fixture
def mock_brand_validator():
    """Mock BrandVoiceValidator returning PASS."""
    validator = AsyncMock()
    validator.validate.return_value = BrandValidationResult(
        status="PASS",
        issues=[],
        suggestions=[],
        score=9.0,
    )
    return validator

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for authenticity analysis."""
    client = AsyncMock()
    client.generate.return_value = """
AUTHENTICITY_SCORE: 8.5
AI_PROBABILITY: 0.15
PATTERNS_DETECTED: none
VOCABULARY_DIVERSITY: 0.78
CONFIDENCE: 0.85
"""
    return client

@pytest.fixture
def sample_quality_request():
    """Sample content for quality scoring."""
    return QualityScoreRequest(
        content="Løvemanke har vært brukt i tradisjonell asiatisk kultur i århundrer. Opplev denne fantastiske soppen som en del av din daglige rutine. #DAWO #DAWOmushrooms #lionsmane #wellness #norge",
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=["DAWO", "DAWOmushrooms", "lionsmane", "wellness", "norge"],
        visual_quality_score=8.5,
        source_type="research",
        compliance_check=None,  # Will be computed
        brand_validation=None,  # Will be computed
    )

@pytest.fixture
def low_quality_request():
    """Sample AI-like content for testing low scores."""
    return QualityScoreRequest(
        content="In today's fast-paced world, it's no secret that supplements are game-changers. Let's dive in and unlock your potential!",
        content_type=ContentType.INSTAGRAM_FEED,
        hashtags=["supplements"],  # Too few, no brand hashtags
        visual_quality_score=4.0,
        source_type="evergreen",
        compliance_check=None,
        brand_validation=None,
    )
```

### Project Structure Notes

- **Location**: `teams/dawo/generators/content_quality/` (new package)
- **Dependencies**: EUComplianceChecker (Epic 1), BrandVoiceValidator (Epic 1), LLMClient
- **Used by**: Content Team orchestrator, Approval Queue (Epic 4)
- **LLM Tier**: generate (maps to Sonnet for authenticity analysis accuracy)
- **Performance**: < 10 seconds per content item
- **Weights**: Configurable, default per AC requirements

### References

- [Source: epics.md#Story-3.7] - Original story requirements (FR15)
- [Source: architecture.md#Agent-Package-Structure] - Package patterns
- [Source: project-context.md#LLM-Tier-Assignment] - Tier system
- [Source: project-context.md#Agent-Registration] - Registration pattern
- [Source: teams/dawo/validators/eu_compliance/] - Compliance checker integration
- [Source: teams/dawo/validators/brand_voice/] - Brand voice validation
- [Source: teams/dawo/generators/compliance_rewrite/] - Previous story patterns
- [Source: 3-6-content-compliance-rewrite-suggestions.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. **Package Structure**: Created `teams/dawo/generators/content_quality/` following existing compliance_rewrite patterns
2. **Separate Scorer Classes**: Implemented all 6 component scorers as separate classes in `scorers/` subdirectory per story requirements
3. **AI Detectability**: Implemented pattern matching for both English and Norwegian AI markers, with optional LLM-based analysis via `prompts.py`
4. **Platform Optimization**: Implemented hashtag count validation (5-15 optimal), caption length scoring (180-220 words), CTA detection, and brand hashtag presence
5. **Mock Fixtures**: Created comprehensive conftest.py with mock fixtures for compliance checker (COMPLIANT/WARNING/REJECTED), brand validator (PASS/NEEDS_REVISION/FAIL), and LLM client
6. **BrandValidationResult Fix**: Discovered actual parameters differ from dev notes (uses brand_score, authenticity_score, tone_analysis instead of suggestions, overall_score, status)
7. **Method Name Fix**: BrandVoiceValidator uses `validate_content()` not `validate()`
8. **Test Coverage**: 55 tests total (18 package structure + 29 scoring + 8 integration), 1 skipped for API-dependent integration tests
9. **ContentType Alias**: Exported as QualityContentType to avoid conflict with orshot's ContentType
10. **Code Review Fixes**: Fixed 3 CRITICAL, 4 MEDIUM, 3 LOW issues found during adversarial code review

### Code Review Fixes Applied

**CRITICAL Issues Fixed:**
- Created separate scorer classes (ComplianceScorer, BrandVoiceScorer, VisualQualityScorer, PlatformOptimizationScorer, EngagementPredictionScorer, AuthenticityScorer)
- Implemented LLM-based authenticity checks with prompts.py
- Added missing prompts.py file for AI detectability prompts

**MEDIUM Issues Fixed:**
- Documented infrastructure file changes (integrations/__init__.py, teams/dawo/__init__.py)
- Updated scorers/__init__.py with proper exports
- Removed forbidden term "Sonnet" from docstrings
- Added HistoricalDataProviderProtocol for future engagement data integration

**LOW Issues Fixed:**
- Exported LLMClientProtocol from package
- Added all scorer classes and configs to package exports

### File List

**New Files Created:**
- `teams/dawo/generators/content_quality/__init__.py` - Package exports with complete __all__ list
- `teams/dawo/generators/content_quality/agent.py` - ContentQualityScorer class and protocol
- `teams/dawo/generators/content_quality/schemas.py` - All dataclasses (ComponentScore, AuthenticityResult, PlatformOptimizationResult, EngagementPrediction, QualityScoreRequest, QualityScoreResult)
- `teams/dawo/generators/content_quality/prompts.py` - AI detectability prompts and response parser
- `teams/dawo/generators/content_quality/scorers/__init__.py` - Scorer exports
- `teams/dawo/generators/content_quality/scorers/compliance.py` - ComplianceScorer class
- `teams/dawo/generators/content_quality/scorers/brand_voice.py` - BrandVoiceScorer class
- `teams/dawo/generators/content_quality/scorers/visual_quality.py` - VisualQualityScorer class
- `teams/dawo/generators/content_quality/scorers/platform.py` - PlatformOptimizationScorer class
- `teams/dawo/generators/content_quality/scorers/engagement.py` - EngagementPredictionScorer class
- `teams/dawo/generators/content_quality/scorers/authenticity.py` - AuthenticityScorer class
- `tests/teams/dawo/generators/test_content_quality/__init__.py` - Test package init
- `tests/teams/dawo/generators/test_content_quality/conftest.py` - Mock fixtures
- `tests/teams/dawo/generators/test_content_quality/test_package_structure.py` - 18 package/import tests
- `tests/teams/dawo/generators/test_content_quality/test_scoring.py` - 29 component scoring tests
- `tests/teams/dawo/generators/test_content_quality/test_integration.py` - 8 integration tests

**Modified Files:**
- `teams/dawo/team_spec.py` - Added ContentQualityScorer registration with tier=TIER_GENERATE
- `teams/dawo/generators/__init__.py` - Added content_quality exports with QualityContentType alias
- `integrations/__init__.py` - Added lazy import system to avoid circular imports
- `teams/dawo/__init__.py` - Added lazy import system to avoid circular imports

---

## Change Log

- 2026-02-08: Story created by Scrum Master with comprehensive dev context
- 2026-02-08: Code review completed - fixed 3 CRITICAL, 4 MEDIUM, 3 LOW issues. Created separate scorer classes, added LLM-based authenticity analysis, fixed forbidden term in docstrings.
