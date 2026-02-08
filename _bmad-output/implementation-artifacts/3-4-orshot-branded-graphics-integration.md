# Story 3.4: Orshot Branded Graphics Integration

Status: complete

---

## Story

As an **operator**,
I want branded graphics generated via Orshot using my Canva templates,
So that posts have consistent visual identity without manual design.

---

## Acceptance Criteria

1. **Given** a content item needs a branded graphic
   **When** the Orshot renderer is called
   **Then** it uses a template imported from Canva
   **And** it injects dynamic content: headline, product_name, date
   **And** it returns a high-resolution image (1080x1080 for Instagram feed)

2. **Given** Orshot Starter tier is configured ($30/mo, 3,000 renders)
   **When** renders are requested
   **Then** usage is tracked against monthly limit
   **And** operator is alerted at 80% usage
   **And** render requests respect rate limits

3. **Given** a template is selected
   **When** the graphic is generated
   **Then** it preserves DAWO brand colors, fonts, and spacing
   **And** generated asset is saved to Google Drive (Story 3.2)
   **And** quality score is assigned based on template match

---

## Tasks / Subtasks

- [x] Task 1: Complete Orshot client implementation (AC: #1)
  - [x] 1.1 Implement `OrshotClient.list_templates()` with actual API call
  - [x] 1.2 Implement `OrshotClient.generate_graphic()` with variable injection
  - [x] 1.3 Implement `OrshotClient.download_graphic()` for local storage
  - [x] 1.4 Add retry middleware wrapper for all API calls
  - [x] 1.5 Add request timeout handling (60 second max)
  - [x] 1.6 Add logging for all API operations

- [x] Task 2: Create OrshotRenderer generator agent (AC: #1, #3)
  - [x] 2.1 Create `teams/dawo/generators/orshot_graphics/` package structure
  - [x] 2.2 Implement `OrshotRendererProtocol` for testability
  - [x] 2.3 Implement `OrshotRenderer` class with constructor injection pattern
  - [x] 2.4 Accept `OrshotClientProtocol`, `GoogleDriveClientProtocol`, `UsageTrackerProtocol` via injection
  - [x] 2.5 Create `RenderRequest` and `RenderResult` dataclasses
  - [x] 2.6 Implement template selection logic based on content type

- [x] Task 3: Implement template variable injection (AC: #1)
  - [x] 3.1 Parse template variable requirements from `OrshotTemplate.variables`
  - [x] 3.2 Map content data to template variables (headline, product_name, date)
  - [x] 3.3 Validate all required variables are provided before render
  - [x] 3.4 Handle optional variables gracefully (use defaults or empty)
  - [x] 3.5 Sanitize text variables (length limits, special characters)

- [x] Task 4: Implement render dimensions handling (AC: #1)
  - [x] 4.1 Define dimension constants for Instagram formats:
        - Feed post: 1080x1080
        - Story: 1080x1920
        - Reel cover: 1080x1920
  - [x] 4.2 Validate template dimensions match target format
  - [x] 4.3 Log warning if dimension mismatch (proceed anyway)
  - [x] 4.4 Store dimensions in RenderResult metadata

- [x] Task 5: Implement usage tracking (AC: #2)
  - [x] 5.1 Create `OrshotUsageTracker` class for monthly render counting
  - [x] 5.2 Persist usage count to Redis with monthly key: `orshot:usage:{YYYY-MM}`
  - [x] 5.3 Check usage before each render request
  - [x] 5.4 Return warning in result when usage > 80% (2,400 renders)
  - [x] 5.5 Return error and refuse render when usage = 100% (3,000 renders)
  - [x] 5.6 Send Discord alert at 80% threshold (one-time per month)

- [x] Task 6: Implement rate limiting (AC: #2)
  - [x] 6.1 Research Orshot API rate limits (using 60/minute default - not documented by Orshot)
  - [x] 6.2 Implement token bucket rate limiter for requests
  - [x] 6.3 Queue requests when rate limited, process in order
  - [x] 6.4 Add backoff when receiving 429 responses
  - [x] 6.5 Log rate limit events for monitoring

- [x] Task 7: Integrate Google Drive asset storage (AC: #3)
  - [x] 7.1 Download generated graphic from Orshot URL
  - [x] 7.2 Upload to Google Drive folder: `DAWO.ECO/Assets/Orshot/`
  - [x] 7.3 Use filename pattern: `{date}_{template}_{topic}_{id}.png`
  - [x] 7.4 Store Drive file ID and URL in RenderResult
  - [x] 7.5 Handle upload failure gracefully (keep local copy, retry later)

- [x] Task 8: Implement quality scoring (AC: #3)
  - [x] 8.1 Calculate quality score (1-10) based on:
        - Template match (is template designed for content type?)
        - Variable completeness (all variables filled?)
        - Image resolution (meets minimum?)
        - Generation success (no errors?)
  - [x] 8.2 Add `quality_score` to RenderResult
  - [x] 8.3 Flag low-quality renders (score < 6) for review

- [x] Task 9: Register OrshotRenderer in team_spec.py (AC: #1, #2, #3)
  - [x] 9.1 Add `OrshotRenderer` as RegisteredAgent with tier="generate"
  - [x] 9.2 Add capability tags: "graphics_generation", "orshot", "visual_content"
  - [x] 9.3 Register as service for injection

- [x] Task 10: Create unit tests
  - [x] 10.1 Test OrshotClient with mocked HTTP responses
  - [x] 10.2 Test template listing and caching
  - [x] 10.3 Test variable injection with valid/invalid inputs
  - [x] 10.4 Test usage tracking increment/check
  - [x] 10.5 Test rate limiting behavior
  - [x] 10.6 Test Google Drive integration with mock client
  - [x] 10.7 Test quality score calculation
  - [x] 10.8 Test error handling for API failures

- [x] Task 11: Create integration tests
  - [x] 11.1 Test end-to-end graphic generation (skipped unless ORSHOT_API_KEY set)
  - [x] 11.2 Test with real Orshot API (requires ORSHOT_API_KEY env var)
  - [x] 11.3 Test Google Drive upload with real credentials

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story completes the Orshot client scaffold created in earlier preparation and creates the OrshotRenderer generator agent. Follow the existing patterns from:
- `integrations/orshot/client.py` - Existing scaffold with Protocol and placeholder methods
- `teams/dawo/generators/instagram_caption/` - Agent package structure
- `integrations/shopify/` - Integration client patterns with retry middleware

**Key Pattern:** The Orshot client is an **integration** (in `integrations/orshot/`), while the OrshotRenderer is a **generator agent** (in `teams/dawo/generators/`). Keep separation clear:
- Integration: API calls, authentication, raw data handling
- Generator: Business logic, template selection, quality scoring

### Existing Orshot Scaffold (COMPLETE THIS)

**Source:** [integrations/orshot/client.py]

The following already exists and needs implementation:

```python
# integrations/orshot/client.py - ALREADY EXISTS, needs completion
class OrshotClient:
    """Orshot client for branded graphics generation."""

    async def list_templates(self) -> list[OrshotTemplate]:
        # TODO: Implement Orshot API call
        ...

    async def generate_graphic(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> GeneratedGraphic:
        # TODO: Implement Orshot API call
        ...

    async def download_graphic(
        self,
        graphic: GeneratedGraphic,
        output_path: Path,
    ) -> Path:
        # TODO: Implement download
        ...
```

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
integrations/orshot/           # Complete existing client
├── __init__.py                # Already exists with exports
├── client.py                  # Complete placeholder methods
├── usage.py                   # NEW: OrshotUsageTracker
└── rate_limiter.py            # NEW: Rate limiting logic

teams/dawo/generators/
├── __init__.py                # Add OrshotRenderer exports
├── orshot_graphics/           # NEW package
│   ├── __init__.py            # Package exports
│   ├── agent.py               # OrshotRenderer class
│   ├── schemas.py             # RenderRequest, RenderResult
│   └── templates.py           # Template selection logic, dimension constants
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

This agent does NOT use LLM for core functionality (graphics generation is via Orshot API). However, if template selection requires AI reasoning:

```python
# CORRECT: Use tier name if LLM needed for template selection
tier=TIER_GENERATE  # Maps to Sonnet at runtime

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - Any hardcoded model IDs
```

### Orshot API Integration (RESEARCH REQUIRED)

**Source:** Web research needed for Orshot API documentation

The developer MUST research Orshot API documentation for:
1. **Authentication method** - API key header format
2. **Endpoint structure** - Base URL, resource paths
3. **Rate limits** - Requests per minute/hour
4. **Template management** - How to list Canva-imported templates
5. **Variable injection** - Format for passing dynamic content
6. **Response format** - Image URL, metadata returned

**Starter tier constraints ($30/mo):**
- 3,000 renders/month
- Alert at 80% = 2,400 renders
- Hard stop at 100% = 3,000 renders

### Instagram Dimension Constants

**Source:** Instagram design guidelines

```python
# templates.py
from enum import Enum
from typing import NamedTuple

class Dimensions(NamedTuple):
    width: int
    height: int

class InstagramFormat(Enum):
    """Instagram content formats with required dimensions."""
    FEED_POST = Dimensions(1080, 1080)    # Square post
    FEED_PORTRAIT = Dimensions(1080, 1350)  # 4:5 portrait
    STORY = Dimensions(1080, 1920)         # 9:16 vertical
    REEL_COVER = Dimensions(1080, 1920)    # 9:16 vertical

def validate_dimensions(template: OrshotTemplate, target: InstagramFormat) -> bool:
    """Check if template dimensions match target format."""
    return template.dimensions == target.value
```

### Usage Tracking Pattern

**Source:** Design based on Story 3.4 requirements

```python
# usage.py
import redis.asyncio as redis
from datetime import datetime

class OrshotUsageTracker:
    """Track monthly Orshot render usage."""

    MONTHLY_LIMIT = 3000
    WARNING_THRESHOLD = 0.80  # 80%

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def get_usage(self) -> int:
        """Get current month's render count."""
        key = f"orshot:usage:{datetime.now():%Y-%m}"
        count = await self._redis.get(key)
        return int(count) if count else 0

    async def increment(self) -> tuple[int, bool, bool]:
        """Increment usage count.

        Returns:
            Tuple of (new_count, is_warning, is_limit_reached)
        """
        key = f"orshot:usage:{datetime.now():%Y-%m}"
        count = await self._redis.incr(key)

        # Set expiry to 45 days to handle month rollover
        if count == 1:
            await self._redis.expire(key, 45 * 24 * 60 * 60)

        is_warning = count >= self.MONTHLY_LIMIT * self.WARNING_THRESHOLD
        is_limit = count >= self.MONTHLY_LIMIT

        return count, is_warning, is_limit

    async def can_render(self) -> bool:
        """Check if rendering is allowed."""
        return await self.get_usage() < self.MONTHLY_LIMIT
```

### RenderRequest and RenderResult Schemas

**Source:** Design based on Epic 3 requirements

```python
# schemas.py
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

class ContentType(Enum):
    """Content types for template selection."""
    INSTAGRAM_FEED = "feed_post"
    INSTAGRAM_STORY = "story"
    INSTAGRAM_REEL = "reel"

@dataclass
class RenderRequest:
    """Input for graphics rendering."""
    content_id: str                    # Unique content identifier
    content_type: ContentType          # For template selection
    headline: str                      # Main text for graphic
    product_name: Optional[str]        # Product name if applicable
    date_display: Optional[str]        # Date text for graphic
    topic: str                         # Topic for filename
    template_id: Optional[str] = None  # Specific template, or auto-select

@dataclass
class RenderResult:
    """Output from graphics rendering."""
    content_id: str
    template_id: str
    template_name: str
    image_url: str                     # Orshot-generated URL
    drive_url: Optional[str]           # Google Drive URL after upload
    drive_file_id: Optional[str]       # Google Drive file ID
    local_path: Optional[Path]         # Local path if downloaded
    dimensions: tuple[int, int]        # Width, height
    quality_score: float               # 1-10 quality assessment
    usage_count: int                   # Current monthly usage
    usage_warning: bool                # True if > 80% usage
    generation_time_ms: int
    created_at: datetime
```

### Google Drive Integration Pattern

**Source:** [3-2-google-drive-asset-storage.md], [integrations/google_drive/]

```python
from integrations.google_drive import (
    GoogleDriveClientProtocol,
    AssetType,
)

class OrshotRenderer:
    def __init__(
        self,
        orshot: OrshotClientProtocol,
        drive: GoogleDriveClientProtocol,
        usage_tracker: OrshotUsageTracker,
    ) -> None:
        self._orshot = orshot
        self._drive = drive
        self._usage = usage_tracker

    async def render(self, request: RenderRequest) -> RenderResult:
        # 1. Check usage limits
        if not await self._usage.can_render():
            raise UsageLimitExceeded("Monthly render limit reached")

        # 2. Select template if not specified
        template = await self._select_template(request)

        # 3. Build variables
        variables = self._build_variables(request)

        # 4. Generate graphic via Orshot
        graphic = await self._orshot.generate_graphic(
            template_id=template.id,
            variables=variables,
        )

        # 5. Download to temp location
        temp_path = await self._orshot.download_graphic(
            graphic=graphic,
            output_path=self._get_temp_path(request),
        )

        # 6. Upload to Google Drive
        drive_asset = await self._drive.upload(
            local_path=temp_path,
            folder="DAWO.ECO/Assets/Orshot",
            asset_type=AssetType.ORSHOT,
            filename=self._build_filename(request, template),
        )

        # 7. Track usage
        count, warning, _ = await self._usage.increment()

        # 8. Calculate quality score
        quality = self._calculate_quality(template, request, graphic)

        return RenderResult(...)
```

### Retry Middleware Integration

**Source:** [project-context.md#External-API-Calls], [architecture.md#Error-Handling]

```python
from library.middleware.retry import with_retry

class OrshotClient:
    @with_retry(max_attempts=3, backoff_base=1.0)
    async def generate_graphic(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> GeneratedGraphic:
        """Generate graphic with retry wrapper."""
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{self._base_url}/render",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "template_id": template_id,
                    "variables": variables,
                },
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            )
            response.raise_for_status()
            data = await response.json()
            return GeneratedGraphic(...)
```

### Quality Score Calculation

**Source:** Design based on Story 3.4 requirements

```python
def _calculate_quality(
    self,
    template: OrshotTemplate,
    request: RenderRequest,
    graphic: GeneratedGraphic,
) -> float:
    """Calculate render quality score (1-10)."""
    score = 10.0

    # Template match (-2 if wrong content type)
    if not self._is_template_for_type(template, request.content_type):
        score -= 2.0

    # Variable completeness (-1 per missing required variable)
    missing = self._get_missing_variables(template, graphic.variables_used)
    score -= len(missing) * 1.0

    # Resolution check (-1 if below minimum)
    min_dim = 1080
    if template.dimensions[0] < min_dim or template.dimensions[1] < min_dim:
        score -= 1.0

    # Generation success (-3 if image URL empty)
    if not graphic.image_url:
        score -= 3.0

    return max(1.0, min(10.0, score))
```

### Discord Alerts for Usage

**Source:** [architecture.md#Error-Handling], [project-context.md#External-API-Calls]

```python
from integrations.discord import send_alert

async def _check_usage_alert(self, count: int, warning: bool) -> None:
    """Send Discord alert if usage threshold reached."""
    if warning:
        # Check if alert already sent this month
        alert_key = f"orshot:alert:{datetime.now():%Y-%m}"
        if not await self._redis.exists(alert_key):
            await send_alert(
                title="Orshot Usage Warning",
                message=f"Monthly render usage at {count}/3000 (80%+)",
                level="warning",
            )
            await self._redis.set(alert_key, "1", ex=45 * 24 * 60 * 60)
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-3-instagram-caption-generator.md#Dev-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export OrshotRenderer, OrshotRendererProtocol, RenderRequest, RenderResult |
| Config injection pattern | Accept clients via constructor, never instantiate internally |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all Orshot and Drive API errors before raising |
| F-string logging anti-pattern | Use `%` formatting: `logger.info("Rendering %s", template_id)` |
| Integration tests separate | Create test_integration.py with env var skip markers |
| Circular import fix | Use lazy imports if needed (see 3-3 completion notes) |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER instantiate OrshotClient internally** - Accept via constructor injection
2. **NEVER hardcode API URLs** - Use config/env vars
3. **NEVER swallow API exceptions** - Log and re-raise or return error result
4. **NEVER skip retry middleware** - All external calls must use retry wrapper
5. **NEVER store credentials in code** - Use environment variables
6. **NEVER make synchronous API calls** - All calls must be async

### Test Fixtures

**Source:** [tests/teams/dawo/generators/test_instagram_caption/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_orshot_graphics/conftest.py
import pytest
from unittest.mock import AsyncMock
from pathlib import Path

@pytest.fixture
def mock_orshot_client():
    """Mock OrshotClient for renderer tests."""
    client = AsyncMock()
    client.list_templates.return_value = [
        OrshotTemplate(
            id="tpl_123",
            name="DAWO Feed Post",
            canva_id="canva_abc",
            variables=["headline", "product_name", "date"],
            dimensions=(1080, 1080),
        ),
    ]
    client.generate_graphic.return_value = GeneratedGraphic(
        id="gen_456",
        template_id="tpl_123",
        image_url="https://cdn.orshot.com/renders/gen_456.png",
        local_path=None,
        variables_used={"headline": "Test", "product_name": "Løvemanke"},
        created_at=datetime.now(timezone.utc),
    )
    client.download_graphic.return_value = Path("/tmp/gen_456.png")
    return client

@pytest.fixture
def mock_drive_client():
    """Mock GoogleDriveClient for asset upload tests."""
    client = AsyncMock()
    client.upload.return_value = DriveAsset(
        file_id="drive_789",
        name="2026-02-07_feed_wellness_gen456.png",
        url="https://drive.google.com/file/d/drive_789",
        folder="DAWO.ECO/Assets/Orshot",
    )
    return client

@pytest.fixture
def mock_usage_tracker():
    """Mock OrshotUsageTracker."""
    tracker = AsyncMock()
    tracker.can_render.return_value = True
    tracker.get_usage.return_value = 100
    tracker.increment.return_value = (101, False, False)
    return tracker

@pytest.fixture
def sample_render_request():
    """Sample render request for tests."""
    return RenderRequest(
        content_id="content_123",
        content_type=ContentType.INSTAGRAM_FEED,
        headline="Naturens kraft i hver kapsel",
        product_name="Løvemanke Ekstrakt",
        date_display="Februar 2026",
        topic="wellness",
    )
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.orshot_graphics import (
    OrshotRenderer,
    OrshotRendererProtocol,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="orshot_renderer",
        agent_class=OrshotRenderer,
        capabilities=["graphics_generation", "orshot", "visual_content"],
        tier=TIER_GENERATE,  # Uses Sonnet if LLM needed for template selection
    ),
]
```

### Project Structure Notes

- **Integration Location**: `integrations/orshot/` (complete existing scaffold)
- **Agent Location**: `teams/dawo/generators/orshot_graphics/` (new package)
- **Dependencies**: OrshotClient, GoogleDriveClient, Redis (for usage tracking)
- **Used by**: Content Team orchestrator, approval workflow
- **External API**: Orshot (https://orshot.com)
- **Performance**: < 30 seconds per render (API dependent)

### References

- [Source: epics.md#Story-3.4] - Original story requirements (FR10)
- [Source: architecture.md#External-Integration-Points] - Integration patterns
- [Source: project-context.md#Integration-Clients] - Protocol injection pattern
- [Source: integrations/orshot/client.py] - Existing scaffold to complete
- [Source: integrations/google_drive/] - Asset storage integration
- [Source: 3-2-google-drive-asset-storage.md] - Drive storage patterns
- [Source: 3-3-instagram-caption-generator.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. **Orshot API Integration**: Successfully researched and implemented Orshot API client with endpoints `/studio-templates-list` (GET) and `/generate/images` (POST). Authentication via Bearer token in Authorization header.

2. **RetryableHttpClient Pattern**: Used existing `RetryableHttpClient` from `teams/dawo/middleware/http_client.py` for all API calls, ensuring consistent retry behavior with exponential backoff.

3. **Usage Tracking**: Implemented `OrshotUsageTracker` with Redis persistence and Discord alerts at 80% threshold. Monthly keys auto-expire after 45 days.

4. **Rate Limiting**: Implemented token bucket rate limiter with both Redis (distributed) and in-memory (fallback) modes. Exponential backoff for 429 responses.

5. **Test Coverage**: 93 total tests collected:
   - 16 OrshotClient unit tests (passing)
   - 17 OrshotRenderer tests (passing)
   - 24 usage tracking tests (passing)
   - 24 rate limiter tests (passing)
   - 6 integration tests (skipped without ORSHOT_API_KEY)
   - 6 additional conftest/fixture tests

6. **Exception Handling Fix**: Fixed ValueError handling in `generate_graphic()` to properly distinguish template-not-found errors from JSON decode errors.

### File List

**Integration Files (integrations/orshot/):**
- `__init__.py` - Updated with all exports
- `client.py` - Complete OrshotClient implementation
- `usage.py` - OrshotUsageTracker with Redis persistence
- `rate_limiter.py` - Token bucket rate limiter

**Generator Agent Files (teams/dawo/generators/orshot_graphics/):**
- `__init__.py` - Package exports
- `agent.py` - OrshotRenderer class
- `schemas.py` - RenderRequest, RenderResult dataclasses
- `templates.py` - InstagramFormat, Dimensions, template selection

**Team Registration:**
- `teams/dawo/team_spec.py` - Added OrshotRenderer agent and Orshot services
- `teams/dawo/generators/__init__.py` - Added OrshotRenderer exports

**Project Configuration (updated):**
- `_bmad-output/project-context.md` - Updated with Epic 3 patterns
- `config/dawo_brand_profile.json` - Updated brand configuration

**Test Files:**
- `tests/integrations/test_orshot/test_client.py` - Client unit tests
- `tests/integrations/test_orshot/test_usage.py` - Usage tracking tests
- `tests/integrations/test_orshot/test_rate_limiter.py` - Rate limiter tests
- `tests/integrations/test_orshot/test_integration.py` - Integration tests
- `tests/teams/dawo/generators/test_orshot_graphics/test_renderer.py` - Renderer tests
- `tests/teams/dawo/generators/test_orshot_graphics/conftest.py` - Test fixtures

---

## Change Log

- 2026-02-07: Story created by Scrum Master with comprehensive dev context
- 2026-02-07: Story completed - All 11 tasks implemented and tested
- 2026-02-07: Code review (Amelia) - Fixed 7 issues:
  - Added missing exports: UsageLimitExceeded, UsageTrackerProtocol, template utilities
  - Updated documentation: env var name, test count, Task 6.1 research note
  - Added missing files to File List: project-context.md, dawo_brand_profile.json
