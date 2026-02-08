# Story 3.8: Auto-Publish Eligibility Tagging

Status: done

---

## Story

As an **operator**,
I want high-quality compliant content tagged for potential auto-publishing,
So that I can build trust in the system before enabling automation.

---

## Acceptance Criteria

1. **Given** a content item has quality score >= 9
   **When** compliance status is COMPLIANT
   **Then** it receives tag: `WOULD_AUTO_PUBLISH`
   **And** this is displayed in approval queue as badge

2. **Given** content is tagged WOULD_AUTO_PUBLISH
   **When** operator reviews it
   **Then** they see: "This post would have auto-published"
   **And** system tracks: how many WOULD_AUTO_PUBLISH posts are approved unchanged

3. **Given** simulation data accumulates
   **When** operator views dashboard
   **Then** they see: WOULD_AUTO_PUBLISH accuracy rate
   **And** they can enable real auto-publish per content type when confident

4. **Given** auto-publish is disabled (default MVP)
   **When** content is tagged WOULD_AUTO_PUBLISH
   **Then** it still requires human approval
   **And** tag is informational only

---

## Tasks / Subtasks

- [x] Task 1: Create AutoPublishTagger package structure (AC: #1)
  - [x] 1.1 Create `teams/dawo/generators/auto_publish_tagger/` package
  - [x] 1.2 Implement `AutoPublishTaggerProtocol` for testability
  - [x] 1.3 Implement `AutoPublishTagger` class with constructor injection
  - [x] 1.4 Accept quality score as float via `TaggingRequest` (decoupled from scorer)
  - [x] 1.5 Create `TaggingRequest` and `TaggingResult` dataclasses
  - [x] 1.6 Export all types in `__init__.py` with complete `__all__` list

- [x] Task 2: Implement eligibility logic (AC: #1)
  - [x] 2.1 Create `check_eligibility()` method accepting QualityScoreResult and compliance status
  - [x] 2.2 Implement threshold check: `total_score >= AUTO_PUBLISH_THRESHOLD` (default: 9.0)
  - [x] 2.3 Implement compliance check: `overall_status == OverallStatus.COMPLIANT`
  - [x] 2.4 Return `EligibilityResult` with `is_eligible: bool` and `reason: str`
  - [x] 2.5 Make threshold configurable via constructor injection

- [x] Task 3: Create tagging data structures (AC: #1, #2)
  - [x] 3.1 Create `AutoPublishTag` enum with `WOULD_AUTO_PUBLISH`, `NOT_ELIGIBLE`, `APPROVED_UNCHANGED`, `APPROVED_MODIFIED`
  - [x] 3.2 Create `TaggingRequest` with content_id, quality_score, compliance_status
  - [x] 3.3 Create `TaggingResult` with tag, is_eligible, reason, tagged_at
  - [x] 3.4 Create `ApprovalOutcome` dataclass for tracking approval decisions

- [x] Task 4: Implement approval tracking service (AC: #2, #3)
  - [x] 4.1 Create `AutoPublishStatisticsService` for tracking tagging accuracy
  - [x] 4.2 Implement `record_tagging()` to log when content is tagged WOULD_AUTO_PUBLISH
  - [x] 4.3 Implement `record_approval_outcome()` to log approval decision (unchanged/modified/rejected)
  - [x] 4.4 Implement `get_accuracy_stats()` returning accuracy rate and totals
  - [x] 4.5 Store statistics in memory with interface for future database persistence

- [x] Task 5: Implement accuracy calculation (AC: #3)
  - [x] 5.1 Calculate accuracy rate: `approved_unchanged / total_would_auto_publish * 100`
  - [x] 5.2 Track by content type (instagram_feed, instagram_story, instagram_reel)
  - [x] 5.3 Track by time period (last 7 days, last 30 days, all time)
  - [x] 5.4 Return `AccuracyStats` with rate, total_tagged, approved_unchanged, approved_modified, rejected

- [x] Task 6: Create config persistence interface (AC: #3)
  - [x] 6.1 Create `AutoPublishConfigProtocol` for toggle state
  - [x] 6.2 Create `AutoPublishConfig` dataclass with per-content-type toggles
  - [x] 6.3 Default all toggles to `False` (MVP: disabled)
  - [x] 6.4 Implement `is_auto_publish_enabled(content_type)` check

- [x] Task 7: Register AutoPublishTagger in team_spec.py (AC: #1)
  - [x] 7.1 Add `AutoPublishTagger` as RegisteredAgent with tier="generate"
  - [x] 7.2 Add capability tags: "auto_publish", "content_tagging", "approval_eligibility"
  - [x] 7.3 Update `teams/dawo/generators/__init__.py` with exports

- [x] Task 8: Create unit tests
  - [x] 8.1 Test eligibility check with score >= 9 AND COMPLIANT (expect eligible)
  - [x] 8.2 Test eligibility check with score >= 9 AND WARNING (expect not eligible)
  - [x] 8.3 Test eligibility check with score < 9 AND COMPLIANT (expect not eligible)
  - [x] 8.4 Test eligibility check with score = 9.0 boundary (expect eligible)
  - [x] 8.5 Test eligibility check with score = 8.9 boundary (expect not eligible)
  - [x] 8.6 Test statistics tracking with various approval outcomes
  - [x] 8.7 Test accuracy calculation with sample data
  - [x] 8.8 Test config toggles (default disabled, explicit enable)

- [x] Task 9: Create integration tests
  - [x] 9.1 Test full tagging flow with mock ContentQualityScorer
  - [x] 9.2 Test statistics accumulation over multiple tagging operations
  - [x] 9.3 Test accuracy calculation with mixed outcomes
  - [x] 9.4 Test content type filtering for statistics

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story creates the Auto-Publish Eligibility Tagger that bridges content quality scoring (Story 3-7) with the approval workflow. It's a **generator** agent that produces tagging decisions and tracks statistics.

**Key Pattern:** This is a lightweight tagging service that evaluates quality + compliance and applies tags. It integrates downstream with the Approval Manager (Epic 4) for display.

### Existing Interfaces (MUST USE)

**Source:** [teams/dawo/generators/content_quality/], [teams/dawo/validators/eu_compliance/]

```python
# From Story 3-7: Content Quality Scorer
from teams.dawo.generators.content_quality import (
    QualityScoreResult,    # Contains total_score (0-10)
    ContentType,           # INSTAGRAM_FEED, INSTAGRAM_STORY, INSTAGRAM_REEL
)

# From Story 1-2: EU Compliance Checker
from teams.dawo.validators.eu_compliance import (
    OverallStatus,  # COMPLIANT, WARNING, REJECTED
)

# Eligibility check logic:
def check_eligibility(
    quality_result: QualityScoreResult,
    compliance_status: OverallStatus,
    threshold: float = 9.0,
) -> bool:
    return (
        quality_result.total_score >= threshold
        and compliance_status == OverallStatus.COMPLIANT
    )
```

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
teams/dawo/generators/
├── __init__.py                       # Add AutoPublishTagger exports
├── auto_publish_tagger/              # NEW package
│   ├── __init__.py                   # Package exports with __all__
│   ├── agent.py                      # AutoPublishTagger class
│   ├── schemas.py                    # Request/Result/Config dataclasses
│   ├── statistics.py                 # AutoPublishStatisticsService
│   └── constants.py                  # Thresholds and defaults
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

```python
# This agent does NOT need LLM - pure logic-based tagging
# However, registered as tier=TIER_GENERATE for consistency in case future enhancements need LLM
tier=TIER_GENERATE

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - "claude-haiku", "claude-sonnet", "claude-opus"
```

### Schema Design

**Source:** Design based on AC requirements

```python
# schemas.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AutoPublishTag(Enum):
    """Auto-publish eligibility tag status."""

    WOULD_AUTO_PUBLISH = "would_auto_publish"      # Eligible for auto-publish
    NOT_ELIGIBLE = "not_eligible"                   # Does not meet criteria
    APPROVED_UNCHANGED = "approved_unchanged"       # Was tagged, approved as-is
    APPROVED_MODIFIED = "approved_modified"         # Was tagged, approved with edits
    REJECTED = "rejected"                           # Was tagged but rejected


@dataclass
class EligibilityResult:
    """Result of eligibility check."""

    is_eligible: bool
    tag: AutoPublishTag
    reason: str
    quality_score: float
    compliance_status: str  # "COMPLIANT", "WARNING", "REJECTED"
    threshold: float = 9.0


@dataclass
class TaggingRequest:
    """Input for auto-publish tagging."""

    content_id: str
    quality_score: float
    compliance_status: str  # OverallStatus value as string
    content_type: str       # ContentType value as string
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaggingResult:
    """Result of tagging operation."""

    content_id: str
    tag: AutoPublishTag
    is_eligible: bool
    reason: str
    display_message: str    # "This post would have auto-published"
    tagged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ApprovalOutcome:
    """Record of approval decision for statistics."""

    content_id: str
    original_tag: AutoPublishTag
    outcome: AutoPublishTag  # APPROVED_UNCHANGED, APPROVED_MODIFIED, REJECTED
    content_type: str
    was_edited: bool
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AccuracyStats:
    """Auto-publish accuracy statistics."""

    total_tagged: int                   # Total WOULD_AUTO_PUBLISH tagged
    approved_unchanged: int             # Approved without edits
    approved_modified: int              # Approved with edits
    rejected: int                       # Rejected
    accuracy_rate: float                # approved_unchanged / total_tagged * 100
    content_type: Optional[str] = None  # Filter by content type (None = all)
    period_days: Optional[int] = None   # Filter by time period (None = all time)


@dataclass
class AutoPublishConfig:
    """Auto-publish toggle configuration."""

    instagram_feed_enabled: bool = False
    instagram_story_enabled: bool = False
    instagram_reel_enabled: bool = False

    def is_enabled(self, content_type: str) -> bool:
        """Check if auto-publish is enabled for content type."""
        mapping = {
            "instagram_feed": self.instagram_feed_enabled,
            "instagram_story": self.instagram_story_enabled,
            "instagram_reel": self.instagram_reel_enabled,
        }
        return mapping.get(content_type, False)
```

### AutoPublishTagger Agent Pattern

**Source:** [teams/dawo/generators/content_quality/agent.py]

```python
# agent.py
from typing import Protocol
from datetime import datetime, timezone
import logging

from .schemas import (
    TaggingRequest,
    TaggingResult,
    EligibilityResult,
    AutoPublishTag,
    AutoPublishConfig,
)
from .statistics import AutoPublishStatisticsService
from .constants import DEFAULT_THRESHOLD, ELIGIBLE_MESSAGE

logger = logging.getLogger(__name__)


class AutoPublishTaggerProtocol(Protocol):
    """Protocol for auto-publish tagger."""

    def tag_content(
        self,
        request: TaggingRequest
    ) -> TaggingResult:
        """Apply auto-publish eligibility tag to content."""
        ...

    def check_eligibility(
        self,
        quality_score: float,
        compliance_status: str,
    ) -> EligibilityResult:
        """Check if content meets auto-publish eligibility criteria."""
        ...


class AutoPublishTagger:
    """Tags content with auto-publish eligibility status.

    Evaluates content quality score and EU compliance status to determine
    if content would qualify for auto-publishing (score >= 9, COMPLIANT).

    Uses 'generate' tier (defaults to configured model) for future LLM enhancements.
    Configuration is received via dependency injection - NEVER loads config directly.
    """

    def __init__(
        self,
        statistics_service: AutoPublishStatisticsService,
        config: AutoPublishConfig | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            statistics_service: Service for tracking tagging statistics
            config: Auto-publish toggle configuration
            threshold: Quality score threshold for eligibility (default: 9.0)
        """
        self._statistics = statistics_service
        self._config = config or AutoPublishConfig()
        self._threshold = threshold

    def check_eligibility(
        self,
        quality_score: float,
        compliance_status: str,
    ) -> EligibilityResult:
        """Check if content meets auto-publish eligibility criteria.

        Args:
            quality_score: Total quality score from ContentQualityScorer (0-10)
            compliance_status: EU compliance status ("COMPLIANT", "WARNING", "REJECTED")

        Returns:
            EligibilityResult with eligibility decision and reason
        """
        score_eligible = quality_score >= self._threshold
        compliance_eligible = compliance_status == "COMPLIANT"
        is_eligible = score_eligible and compliance_eligible

        if is_eligible:
            tag = AutoPublishTag.WOULD_AUTO_PUBLISH
            reason = f"Quality score {quality_score} >= {self._threshold} and compliance COMPLIANT"
        elif not score_eligible:
            tag = AutoPublishTag.NOT_ELIGIBLE
            reason = f"Quality score {quality_score} below threshold {self._threshold}"
        else:
            tag = AutoPublishTag.NOT_ELIGIBLE
            reason = f"Compliance status {compliance_status} is not COMPLIANT"

        return EligibilityResult(
            is_eligible=is_eligible,
            tag=tag,
            reason=reason,
            quality_score=quality_score,
            compliance_status=compliance_status,
            threshold=self._threshold,
        )

    def tag_content(
        self,
        request: TaggingRequest
    ) -> TaggingResult:
        """Apply auto-publish eligibility tag to content.

        Args:
            request: TaggingRequest with content details

        Returns:
            TaggingResult with tag and display information
        """
        try:
            eligibility = self.check_eligibility(
                quality_score=request.quality_score,
                compliance_status=request.compliance_status,
            )

            # Record for statistics tracking
            if eligibility.is_eligible:
                self._statistics.record_tagging(
                    content_id=request.content_id,
                    content_type=request.content_type,
                )

            display_message = ELIGIBLE_MESSAGE if eligibility.is_eligible else ""

            return TaggingResult(
                content_id=request.content_id,
                tag=eligibility.tag,
                is_eligible=eligibility.is_eligible,
                reason=eligibility.reason,
                display_message=display_message,
                tagged_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error("Auto-publish tagging failed for content %s: %s", request.content_id, e)
            raise
```

### Statistics Service

**Source:** Design based on AC #2, #3

```python
# statistics.py
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from .schemas import ApprovalOutcome, AccuracyStats, AutoPublishTag

logger = logging.getLogger(__name__)


class AutoPublishStatisticsService:
    """Service for tracking auto-publish tagging statistics.

    Maintains in-memory statistics for tagging operations.
    Can be extended with database persistence in the future.
    """

    def __init__(self) -> None:
        """Initialize with empty statistics."""
        self._tagged_content: list[dict] = []
        self._outcomes: list[ApprovalOutcome] = []

    def record_tagging(
        self,
        content_id: str,
        content_type: str,
    ) -> None:
        """Record when content is tagged WOULD_AUTO_PUBLISH.

        Args:
            content_id: Unique content identifier
            content_type: Content type (instagram_feed, etc.)
        """
        self._tagged_content.append({
            "content_id": content_id,
            "content_type": content_type,
            "tagged_at": datetime.now(timezone.utc),
        })
        logger.info(
            "Recorded auto-publish tagging for content %s (type: %s)",
            content_id, content_type
        )

    def record_approval_outcome(
        self,
        content_id: str,
        content_type: str,
        was_edited: bool,
        was_approved: bool,
    ) -> None:
        """Record approval decision for tagged content.

        Args:
            content_id: Unique content identifier
            content_type: Content type
            was_edited: True if content was modified before approval
            was_approved: True if approved, False if rejected
        """
        if was_approved:
            outcome = (
                AutoPublishTag.APPROVED_UNCHANGED
                if not was_edited
                else AutoPublishTag.APPROVED_MODIFIED
            )
        else:
            outcome = AutoPublishTag.REJECTED

        self._outcomes.append(ApprovalOutcome(
            content_id=content_id,
            original_tag=AutoPublishTag.WOULD_AUTO_PUBLISH,
            outcome=outcome,
            content_type=content_type,
            was_edited=was_edited,
            recorded_at=datetime.now(timezone.utc),
        ))
        logger.info(
            "Recorded approval outcome %s for content %s",
            outcome.value, content_id
        )

    def get_accuracy_stats(
        self,
        content_type: Optional[str] = None,
        period_days: Optional[int] = None,
    ) -> AccuracyStats:
        """Calculate accuracy statistics for auto-publish tagging.

        Args:
            content_type: Filter by content type (None = all)
            period_days: Filter by time period in days (None = all time)

        Returns:
            AccuracyStats with accuracy rate and breakdown
        """
        cutoff = None
        if period_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Filter outcomes
        filtered = [
            o for o in self._outcomes
            if (content_type is None or o.content_type == content_type)
            and (cutoff is None or o.recorded_at >= cutoff)
        ]

        # Count outcomes
        total = len(filtered)
        unchanged = sum(1 for o in filtered if o.outcome == AutoPublishTag.APPROVED_UNCHANGED)
        modified = sum(1 for o in filtered if o.outcome == AutoPublishTag.APPROVED_MODIFIED)
        rejected = sum(1 for o in filtered if o.outcome == AutoPublishTag.REJECTED)

        # Calculate accuracy rate
        accuracy = (unchanged / total * 100) if total > 0 else 0.0

        return AccuracyStats(
            total_tagged=total,
            approved_unchanged=unchanged,
            approved_modified=modified,
            rejected=rejected,
            accuracy_rate=round(accuracy, 1),
            content_type=content_type,
            period_days=period_days,
        )
```

### Constants

```python
# constants.py
"""Constants for auto-publish eligibility tagging."""

# Quality score threshold for auto-publish eligibility
DEFAULT_THRESHOLD: float = 9.0

# Display message for eligible content
ELIGIBLE_MESSAGE: str = "This post would have auto-published"

# Required compliance status for eligibility
REQUIRED_COMPLIANCE_STATUS: str = "COMPLIANT"
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-7-content-quality-scoring.md]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export AutoPublishTagger, Protocol, all schemas |
| Config injection pattern | Accept config via constructor, never load directly |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all tagging errors before raising |
| F-string logging anti-pattern | Use `%` formatting: `logger.error("Failed: %s", e)` |
| TYPE_CHECKING pattern | Use TYPE_CHECKING for Protocol imports if circular |
| Boundary value testing | Test threshold at exactly 9.0 and 8.9 |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER hardcode threshold** - Accept via constructor injection
2. **NEVER bypass compliance check** - Both score AND compliance required
3. **NEVER mutate content** - Tagging is read-only metadata
4. **NEVER auto-approve** - MVP always requires human approval
5. **NEVER swallow exceptions without logging** - Log all errors

### Integration Points

**Source:** [epics.md#Epic-3], [architecture.md#Data-Flow]

```python
# Auto-Publish Tagger integrates into content pipeline:

# 1. After quality scoring (Story 3-7)
quality_result = await quality_scorer.score_content(request)

# 2. After compliance check (Story 1-2)
compliance_result = await eu_checker.check_content(content_text)

# 3. Apply auto-publish tag (this story)
tagging_result = auto_publish_tagger.tag_content(
    TaggingRequest(
        content_id=content_id,
        quality_score=quality_result.total_score,
        compliance_status=compliance_result.overall_status.value,
        content_type=content_type.value,
    )
)

# 4. Submit to approval queue with tag (Epic 4 will display badge)
await approval_manager.submit(
    content=content,
    quality_score=quality_result.total_score,
    auto_publish_tag=tagging_result.tag.value,
    auto_publish_eligible=tagging_result.is_eligible,
    display_message=tagging_result.display_message,
)

# 5. When operator approves/rejects (Epic 4 integration)
statistics_service.record_approval_outcome(
    content_id=content_id,
    content_type=content_type,
    was_edited=was_edited,
    was_approved=was_approved,
)
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.auto_publish_tagger import (
    AutoPublishTagger,
    AutoPublishTaggerProtocol,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="auto_publish_tagger",
        agent_class=AutoPublishTagger,
        capabilities=["auto_publish", "content_tagging", "approval_eligibility"],
        tier=TIER_GENERATE,  # For future LLM enhancements
    ),
]
```

### Test Fixtures

**Source:** [tests/teams/dawo/generators/test_content_quality/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_auto_publish_tagger/conftest.py
import pytest
from datetime import datetime, timezone

from teams.dawo.generators.auto_publish_tagger import (
    AutoPublishTagger,
    AutoPublishStatisticsService,
    AutoPublishConfig,
    TaggingRequest,
    AutoPublishTag,
)


@pytest.fixture
def statistics_service():
    """Fresh statistics service for each test."""
    return AutoPublishStatisticsService()


@pytest.fixture
def default_tagger(statistics_service):
    """AutoPublishTagger with default configuration."""
    return AutoPublishTagger(
        statistics_service=statistics_service,
        config=AutoPublishConfig(),
        threshold=9.0,
    )


@pytest.fixture
def eligible_request():
    """Request that should be tagged WOULD_AUTO_PUBLISH."""
    return TaggingRequest(
        content_id="test-content-001",
        quality_score=9.5,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )


@pytest.fixture
def ineligible_score_request():
    """Request with low quality score."""
    return TaggingRequest(
        content_id="test-content-002",
        quality_score=8.5,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )


@pytest.fixture
def ineligible_compliance_request():
    """Request with non-compliant status."""
    return TaggingRequest(
        content_id="test-content-003",
        quality_score=9.5,
        compliance_status="WARNING",
        content_type="instagram_feed",
    )


@pytest.fixture
def boundary_eligible_request():
    """Request at exact threshold boundary (score = 9.0)."""
    return TaggingRequest(
        content_id="test-content-004",
        quality_score=9.0,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )


@pytest.fixture
def boundary_ineligible_request():
    """Request just below threshold (score = 8.9)."""
    return TaggingRequest(
        content_id="test-content-005",
        quality_score=8.9,
        compliance_status="COMPLIANT",
        content_type="instagram_feed",
    )
```

### Edge Cases to Handle

1. **Boundary scores**: 9.0 exactly should be eligible, 8.9999 should not
2. **Missing compliance status**: Should fail with clear error
3. **Unknown content type**: Should still tag but log warning
4. **Statistics with no data**: Return 0% accuracy, not division error
5. **Concurrent tagging**: Statistics service should be thread-safe (future concern)

### Project Structure Notes

- **Location**: `teams/dawo/generators/auto_publish_tagger/` (new package)
- **Dependencies**: ContentQualityScorer (Story 3-7), EUComplianceChecker (Story 1-2)
- **Used by**: Content Team orchestrator, Approval Manager (Epic 4)
- **LLM Tier**: generate (for future enhancements, currently pure logic)
- **Persistence**: In-memory (MVP), future: database-backed via Protocol pattern

### References

- [Source: epics.md#Story-3.8] - Original story requirements (FR16)
- [Source: architecture.md#Agent-Package-Structure] - Package patterns
- [Source: project-context.md#LLM-Tier-Assignment] - Tier system
- [Source: project-context.md#Agent-Registration] - Registration pattern
- [Source: teams/dawo/generators/content_quality/] - Quality scoring integration
- [Source: teams/dawo/validators/eu_compliance/] - Compliance checker integration
- [Source: 3-7-content-quality-scoring.md] - Previous story patterns and learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - all tests pass.

### Completion Notes List

- Created `teams/dawo/generators/auto_publish_tagger/` package with complete structure
- Implemented `AutoPublishTagger` with `check_eligibility()` and `tag_content()` methods
- Implemented `AutoPublishStatisticsService` for tracking tagging accuracy over time
- Created all data classes: `TaggingRequest`, `TaggingResult`, `EligibilityResult`, `ApprovalOutcome`, `AccuracyStats`, `AutoPublishConfig`
- Created `AutoPublishTag` enum with 5 states: WOULD_AUTO_PUBLISH, NOT_ELIGIBLE, APPROVED_UNCHANGED, APPROVED_MODIFIED, REJECTED
- Eligibility logic: score >= 9.0 AND compliance == "COMPLIANT" (both required)
- Threshold is configurable via constructor injection (default 9.0)
- All config toggles default to False for MVP (informational-only mode)
- Statistics support filtering by content_type and period_days
- Accuracy calculation handles division by zero (returns 0% for empty stats)
- Registered AutoPublishTagger as agent and AutoPublishStatisticsService as service in team_spec.py
- 41 unit and integration tests created, all passing
- Full test suite: 1596 passed (10 pre-existing errors in news client tests unrelated to this story)

### File List

**New Files:**
- teams/dawo/generators/auto_publish_tagger/__init__.py
- teams/dawo/generators/auto_publish_tagger/agent.py
- teams/dawo/generators/auto_publish_tagger/schemas.py
- teams/dawo/generators/auto_publish_tagger/statistics.py
- teams/dawo/generators/auto_publish_tagger/constants.py
- tests/teams/dawo/generators/test_auto_publish_tagger/__init__.py
- tests/teams/dawo/generators/test_auto_publish_tagger/conftest.py
- tests/teams/dawo/generators/test_auto_publish_tagger/test_eligibility.py
- tests/teams/dawo/generators/test_auto_publish_tagger/test_statistics.py
- tests/teams/dawo/generators/test_auto_publish_tagger/test_integration.py

**Modified Files:**
- teams/dawo/generators/__init__.py (added auto_publish_tagger exports)
- teams/dawo/team_spec.py (added AutoPublishTagger agent and service registrations)
- _bmad-output/implementation-artifacts/sprint-status.yaml (status: in-progress → review)

---

## Change Log

- 2026-02-08: Story created by Scrum Master with comprehensive dev context (YOLO mode)
- 2026-02-08: Implementation complete - all 9 tasks done, 41 tests passing, ready for review
- 2026-02-08: Code review fixes applied:
  - Added `AutoPublishConfigProtocol` for dependency injection (Task 6.1)
  - Renamed `AccuracyStats.total_tagged` to `total_with_outcome` for clarity
  - Added validation in `record_approval_outcome` to warn when content was not previously tagged
  - Added `get_tagging_count()` method to query tagged content count
  - Removed unused test fixtures from conftest.py
  - Updated exports in `__init__.py` and `generators/__init__.py`
