# Story 3.5: Nano Banana AI Image Generation

Status: done

---

## Story

As an **operator**,
I want AI images generated for visual variety,
So that content has engaging visuals when product photos aren't suitable.

---

## Acceptance Criteria

1. **Given** a content item needs an AI-generated image
   **When** the Nano Banana (Gemini) generator is called
   **Then** it uses a prompt incorporating: topic, mood, Scandinavian aesthetic
   **And** it avoids: mushroom close-ups that look unappetizing, medical imagery
   **And** it returns a lifestyle-appropriate image

2. **Given** an AI image is generated
   **When** it's evaluated for quality
   **Then** it receives a quality score (1-10) based on:
   - Aesthetic appeal
   - Brand alignment
   - AI detectability risk (lower is better)
   **And** images scoring < 6 are flagged for human review

3. **Given** AI detectability is a concern
   **When** image is generated
   **Then** metadata does NOT include AI generation markers
   **And** style emphasizes natural, human-curated aesthetic
   **And** asset is saved to Google Drive with generation metadata

---

## Tasks / Subtasks

- [x] Task 1: Complete Gemini client implementation (AC: #1)
  - [x] 1.1 Implement `GeminiImageClient.generate_image()` with actual Gemini API call
  - [x] 1.2 Use Google Generative AI SDK (`google-generativeai` package)
  - [x] 1.3 Implement `GeminiImageClient.download_image()` for local storage
  - [x] 1.4 Add retry middleware wrapper for all API calls
  - [x] 1.5 Add request timeout handling (60 second max)
  - [x] 1.6 Add logging for all API operations
  - [x] 1.7 Implement prompt enhancement with negative prompts for forbidden content

- [x] Task 2: Create NanoBananaGenerator generator agent (AC: #1, #2, #3)
  - [x] 2.1 Create `teams/dawo/generators/nano_banana/` package structure
  - [x] 2.2 Implement `NanoBananaGeneratorProtocol` for testability
  - [x] 2.3 Implement `NanoBananaGenerator` class with constructor injection pattern
  - [x] 2.4 Accept `GeminiImageClientProtocol`, `GoogleDriveClientProtocol` via injection
  - [x] 2.5 Create `ImageGenerationRequest` and `ImageGenerationResult` dataclasses
  - [x] 2.6 Implement topic-to-prompt conversion with DAWO brand alignment

- [x] Task 3: Implement prompt engineering for DAWO aesthetics (AC: #1)
  - [x] 3.1 Create prompt template system for different content types
  - [x] 3.2 Build Scandinavian/Nordic aesthetic prompt prefix
  - [x] 3.3 Add negative prompt list (mushroom close-ups, medical imagery, clinical settings)
  - [x] 3.4 Include mood/atmosphere keywords based on content type
  - [x] 3.5 Validate prompt length limits for Gemini API
  - [x] 3.6 Create prompt builder utility function

- [x] Task 4: Implement image dimensions handling (AC: #1)
  - [x] 4.1 Reuse `InstagramFormat` dimension constants from Orshot story
  - [x] 4.2 Map content types to appropriate dimensions
  - [x] 4.3 Pass dimensions to Gemini API (aspect ratio)
  - [x] 4.4 Store dimensions in ImageGenerationResult metadata

- [x] Task 5: Implement quality scoring (AC: #2)
  - [x] 5.1 Create `ImageQualityScorer` class for evaluating generated images
  - [x] 5.2 Calculate aesthetic appeal score (based on successful generation, resolution)
  - [x] 5.3 Calculate brand alignment score (prompt compliance, style match)
  - [x] 5.4 Estimate AI detectability risk (penalize obvious AI patterns)
  - [x] 5.5 Combine into overall quality score (1-10)
  - [x] 5.6 Flag images scoring < 6 with `needs_review: True`

- [x] Task 6: Implement AI marker prevention (AC: #3)
  - [x] 6.1 Strip EXIF metadata from downloaded images
  - [x] 6.2 Remove any AI generation markers from file metadata
  - [x] 6.3 Use natural filenames without "ai-generated" indicators
  - [x] 6.4 Add prompt to emphasize "natural, human-curated, organic" aesthetic
  - [x] 6.5 Log metadata cleaning actions

- [x] Task 7: Integrate Google Drive asset storage (AC: #3)
  - [x] 7.1 Download generated image to temp location
  - [x] 7.2 Upload to Google Drive folder: `DAWO.ECO/Assets/Generated/`
  - [x] 7.3 Use filename pattern: `{date}_{style}_{topic}_{id}.png`
  - [x] 7.4 Store Drive file ID and URL in ImageGenerationResult
  - [x] 7.5 Handle upload failure gracefully (keep local copy, retry later)
  - [x] 7.6 Store generation metadata separately (prompt, style, score)

- [x] Task 8: Register NanoBananaGenerator in team_spec.py (AC: #1, #2, #3)
  - [x] 8.1 Add `NanoBananaGenerator` as RegisteredAgent with tier="generate"
  - [x] 8.2 Add capability tags: "image_generation", "gemini", "visual_content", "ai_art"
  - [x] 8.3 Register as service for injection

- [x] Task 9: Create unit tests
  - [x] 9.1 Test GeminiImageClient with mocked HTTP responses
  - [x] 9.2 Test prompt building with various content types
  - [x] 9.3 Test negative prompt enforcement
  - [x] 9.4 Test quality score calculation
  - [x] 9.5 Test metadata stripping
  - [x] 9.6 Test Google Drive integration with mock client
  - [x] 9.7 Test dimension handling for different formats
  - [x] 9.8 Test error handling for API failures

- [x] Task 10: Create integration tests
  - [x] 10.1 Test end-to-end image generation (skipped unless GEMINI_API_KEY set)
  - [x] 10.2 Test with real Gemini API (requires GEMINI_API_KEY env var)
  - [x] 10.3 Test Google Drive upload with real credentials
  - [x] 10.4 Verify metadata is stripped from uploaded images

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Implementation-Patterns], [project-context.md#Agent-Registration]

This story completes the Gemini client scaffold created in earlier preparation and creates the NanoBananaGenerator agent. Follow the existing patterns from:
- `integrations/gemini/client.py` - Existing scaffold with Protocol and placeholder methods
- `teams/dawo/generators/orshot_graphics/` - Agent package structure (Story 3-4)
- `integrations/orshot/` - Integration client patterns with retry middleware

**Key Pattern:** The Gemini client is an **integration** (in `integrations/gemini/`), while the NanoBananaGenerator is a **generator agent** (in `teams/dawo/generators/`). Keep separation clear:
- Integration: API calls, authentication, raw data handling
- Generator: Business logic, prompt engineering, quality scoring

### Existing Gemini Scaffold (COMPLETE THIS)

**Source:** [integrations/gemini/client.py]

The following already exists and needs implementation:

```python
# integrations/gemini/client.py - ALREADY EXISTS, needs completion
class GeminiImageClient:
    """Gemini client for AI image generation."""

    DEFAULT_MODEL = "gemini-2.0-flash-exp"  # Image generation capable model

    async def generate_image(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.NORDIC,
        width: int = 1080,
        height: int = 1080,
    ) -> GeneratedImage:
        # TODO: Implement Gemini API call
        ...

    async def download_image(
        self,
        image: GeneratedImage,
        output_path: Path,
    ) -> Path:
        # TODO: Implement download
        ...
```

**Existing types already defined:**
- `ImageStyle` enum: NATURAL, NORDIC, LIFESTYLE, PRODUCT, ABSTRACT
- `GeneratedImage` dataclass: id, prompt, style, image_url, local_path, width, height, created_at
- `GeminiImageClientProtocol`: Protocol for type-safe injection
- Style prefix builder: `_build_style_prefix()` method

### Gemini API Integration (CRITICAL)

**Source:** Google AI documentation

Use the `google-generativeai` Python SDK for image generation:

```python
# Install: pip install google-generativeai
import google.generativeai as genai

genai.configure(api_key=api_key)

# For image generation, use Imagen model
model = genai.ImageGenerationModel("imagen-3.0-generate-001")

# Generate image
response = await model.generate_images(
    prompt=enhanced_prompt,
    number_of_images=1,
    aspect_ratio="1:1",  # For Instagram square
    safety_filter_level="block_few",
    person_generation="allow_adult",
)

# Get image data
image = response.images[0]
image_bytes = image._image_bytes  # Raw bytes
```

**Alternative: Gemini 2.0 Flash with image output**
```python
model = genai.GenerativeModel("gemini-2.0-flash-exp")
response = model.generate_content(
    [prompt],
    generation_config={"response_mime_type": "image/png"}
)
```

**API constraints:**
- Rate limits: Research current limits for Imagen/Gemini
- Timeout: 60 seconds for image generation
- Retry on 429 (rate limit) and 503 (service unavailable)

### File Structure (MUST FOLLOW)

**Source:** [architecture.md#Agent-Package-Structure]

```
integrations/gemini/           # Complete existing client
├── __init__.py                # Already exists with exports
├── client.py                  # Complete placeholder methods
└── metadata.py                # NEW: Metadata stripping utilities

teams/dawo/generators/
├── __init__.py                # Add NanoBananaGenerator exports
├── nano_banana/               # NEW package
│   ├── __init__.py            # Package exports
│   ├── agent.py               # NanoBananaGenerator class
│   ├── schemas.py             # ImageGenerationRequest, ImageGenerationResult
│   ├── prompts.py             # Prompt templates and builder
│   └── quality.py             # ImageQualityScorer
```

### LLM Tier Assignment (CRITICAL)

**Source:** [project-context.md#LLM-Tier-Assignment]

This agent does NOT use LLM for core functionality (image generation is via Gemini Imagen API). Register with tier="generate" for consistency.

```python
# CORRECT: Use tier name
tier=TIER_GENERATE  # For registration

# FORBIDDEN in code/docstrings/comments:
# - "haiku", "sonnet", "opus"
# - Any hardcoded model IDs
```

### Prompt Engineering for DAWO Brand (CRITICAL)

**Source:** [config/dawo_brand_profile.json], Epic 3 requirements

Build prompts that enforce DAWO aesthetics:

```python
# prompts.py
STYLE_TEMPLATES = {
    "wellness": {
        "prefix": "Nordic minimalist wellness photography. Natural lighting, muted earth tones, clean Scandinavian interior. ",
        "negative": "mushrooms, fungi close-up, medical, clinical, laboratory, pills, capsules, hospital, doctor",
    },
    "nature": {
        "prefix": "Norwegian forest landscape photography. Misty atmosphere, pine trees, natural light, peaceful. ",
        "negative": "mushrooms, fungi close-up, bright colors, artificial lighting, people",
    },
    "lifestyle": {
        "prefix": "Scandinavian lifestyle photography. Cozy hygge aesthetic, warm natural tones, authentic feel. ",
        "negative": "medical, clinical, pills, capsules, obvious product placement",
    },
}

def build_prompt(topic: str, style: str, brand_keywords: list[str]) -> str:
    """Build optimized prompt for DAWO brand."""
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["wellness"])

    # Build positive prompt
    positive = f"{template['prefix']}{topic}. "
    positive += ", ".join(brand_keywords) if brand_keywords else ""
    positive += ". Organic, authentic, human-curated feel."

    return positive

def get_negative_prompt(style: str) -> str:
    """Get negative prompt for style."""
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["wellness"])
    base_negative = "AI generated, artificial, digital art, CGI, blurry, low quality, watermark"
    return f"{template['negative']}, {base_negative}"
```

### Quality Scoring System (AC: #2)

**Source:** Story 3.4 patterns, Epic 3 requirements

```python
# quality.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class QualityAssessment:
    """Quality assessment result."""
    aesthetic_score: float      # 1-10: Visual appeal
    brand_alignment: float      # 1-10: Matches DAWO aesthetic
    ai_detectability: float     # 1-10: Lower = more natural looking
    overall_score: float        # Weighted average
    needs_review: bool          # True if overall < 6
    flags: list[str]            # Specific quality issues

class ImageQualityScorer:
    """Score generated images for quality."""

    def score(
        self,
        image: GeneratedImage,
        prompt_compliance: float,  # 0-1: Did image match prompt
        generation_success: bool,
    ) -> QualityAssessment:
        """Calculate quality scores."""

        # Aesthetic appeal (based on successful generation, resolution)
        aesthetic = 8.0 if generation_success else 3.0
        if image.width >= 1080 and image.height >= 1080:
            aesthetic += 1.0

        # Brand alignment (based on style used)
        brand = 8.0 if image.style == ImageStyle.NORDIC else 6.0
        brand += prompt_compliance * 2.0  # Up to +2 for good compliance

        # AI detectability (estimate based on style)
        # NORDIC style aims for natural, less AI-looking
        ai_detect = 7.0 if image.style == ImageStyle.NORDIC else 5.0

        # Weighted average
        overall = (aesthetic * 0.3) + (brand * 0.4) + (ai_detect * 0.3)

        flags = []
        if aesthetic < 6:
            flags.append("low_aesthetic_quality")
        if brand < 6:
            flags.append("poor_brand_alignment")
        if ai_detect < 5:
            flags.append("high_ai_detectability")

        return QualityAssessment(
            aesthetic_score=min(10.0, aesthetic),
            brand_alignment=min(10.0, brand),
            ai_detectability=min(10.0, ai_detect),
            overall_score=min(10.0, max(1.0, overall)),
            needs_review=overall < 6.0,
            flags=flags,
        )
```

### Metadata Stripping (AC: #3)

**Source:** Story 3.5 requirements - prevent AI detection

```python
# metadata.py
from pathlib import Path
from PIL import Image
import piexif

def strip_ai_metadata(image_path: Path, output_path: Optional[Path] = None) -> Path:
    """Remove EXIF and AI generation markers from image.

    Args:
        image_path: Source image path
        output_path: Output path (default: overwrite source)

    Returns:
        Path to cleaned image
    """
    output = output_path or image_path

    # Open and resave without metadata
    with Image.open(image_path) as img:
        # Remove EXIF data
        data = img.getdata()
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(data)
        clean_img.save(output, format="PNG", optimize=True)

    return output


def validate_no_ai_markers(image_path: Path) -> bool:
    """Verify image has no AI generation markers."""
    with Image.open(image_path) as img:
        # Check for EXIF
        if img.info.get("exif"):
            return False
        # Check for AI markers in PNG text chunks
        if any("AI" in str(v) for v in img.info.values()):
            return False
    return True
```

### Google Drive Integration Pattern

**Source:** [3-2-google-drive-asset-storage.md], [integrations/google_drive/]

```python
from integrations.google_drive import (
    GoogleDriveClientProtocol,
    AssetType,
)

class NanoBananaGenerator:
    def __init__(
        self,
        gemini: GeminiImageClientProtocol,
        drive: GoogleDriveClientProtocol,
    ) -> None:
        self._gemini = gemini
        self._drive = drive
        self._scorer = ImageQualityScorer()

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        # 1. Build prompt with DAWO aesthetic
        prompt = build_prompt(request.topic, request.style, request.brand_keywords)

        # 2. Generate image via Gemini
        image = await self._gemini.generate_image(
            prompt=prompt,
            style=ImageStyle[request.style.upper()],
            width=request.width,
            height=request.height,
        )

        # 3. Download to temp location
        temp_path = Path(f"/tmp/{image.id}.png")
        await self._gemini.download_image(image, temp_path)

        # 4. Strip AI metadata
        strip_ai_metadata(temp_path)

        # 5. Upload to Google Drive
        drive_asset = await self._drive.upload(
            local_path=temp_path,
            folder="DAWO.ECO/Assets/Generated",
            asset_type=AssetType.GENERATED,
            filename=self._build_filename(request, image),
        )

        # 6. Calculate quality score
        quality = self._scorer.score(
            image=image,
            prompt_compliance=0.8,  # Estimate based on successful generation
            generation_success=bool(image.image_url),
        )

        return ImageGenerationResult(
            content_id=request.content_id,
            image_id=image.id,
            prompt_used=prompt,
            style=request.style,
            image_url=image.image_url,
            drive_url=drive_asset.url,
            drive_file_id=drive_asset.file_id,
            dimensions=(image.width, image.height),
            quality_score=quality.overall_score,
            needs_review=quality.needs_review,
            quality_flags=quality.flags,
            created_at=image.created_at,
        )
```

### ImageGenerationRequest and ImageGenerationResult Schemas

**Source:** Design based on Epic 3 requirements

```python
# schemas.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class ImageGenerationRequest:
    """Input for AI image generation."""
    content_id: str                    # Unique content identifier
    topic: str                         # Topic/theme for the image
    style: str = "wellness"            # Style: wellness, nature, lifestyle
    brand_keywords: list[str] = field(default_factory=list)  # Additional brand keywords
    width: int = 1080                  # Image width
    height: int = 1080                 # Image height
    avoid_elements: list[str] = field(default_factory=list)  # Things to avoid in image

@dataclass
class ImageGenerationResult:
    """Output from AI image generation."""
    content_id: str
    image_id: str
    prompt_used: str                   # Full prompt sent to Gemini
    style: str
    image_url: str                     # Gemini-generated URL (temporary)
    drive_url: Optional[str]           # Google Drive URL after upload
    drive_file_id: Optional[str]       # Google Drive file ID
    local_path: Optional[str]          # Local path if kept
    dimensions: tuple[int, int]        # Width, height
    quality_score: float               # 1-10 quality assessment
    needs_review: bool                 # True if score < 6
    quality_flags: list[str]           # Specific quality issues
    created_at: datetime
```

### Retry Middleware Integration

**Source:** [project-context.md#External-API-Calls], [teams/dawo/middleware/http_client.py]

```python
from teams.dawo.middleware.http_client import RetryableHttpClient

class GeminiImageClient:
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout

        # Configure Gemini SDK
        genai.configure(api_key=api_key)

    async def generate_image(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.NORDIC,
        width: int = 1080,
        height: int = 1080,
    ) -> GeneratedImage:
        """Generate an image from prompt with retry."""
        enhanced_prompt = f"{self._build_style_prefix(style)}{prompt}"

        try:
            # Use Imagen model for image generation
            model = genai.ImageGenerationModel("imagen-3.0-generate-001")

            # Determine aspect ratio
            aspect_ratio = self._get_aspect_ratio(width, height)

            response = await asyncio.to_thread(
                model.generate_images,
                prompt=enhanced_prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
            )

            image = response.images[0]
            image_id = str(uuid.uuid4())

            # Save image bytes to temp file to get URL
            temp_path = Path(f"/tmp/{image_id}.png")
            image.save(temp_path)

            return GeneratedImage(
                id=image_id,
                prompt=enhanced_prompt,
                style=style,
                image_url=str(temp_path),  # Local path as URL
                local_path=temp_path,
                width=width,
                height=height,
                created_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error("Gemini image generation failed: %s", str(e))
            raise
```

### Previous Story Learnings (CRITICAL - Apply All)

**Source:** [3-4-orshot-branded-graphics-integration.md#Dev-Notes]

| Learning | How to Apply |
|----------|--------------|
| Complete `__all__` exports from day 1 | Export NanoBananaGenerator, NanoBananaGeneratorProtocol, ImageGenerationRequest, ImageGenerationResult |
| Config injection pattern | Accept clients via constructor, never instantiate internally |
| `datetime` deprecation fix | Use `datetime.now(timezone.utc)` not `datetime.utcnow()` |
| Add logging to exception handlers | Log all Gemini and Drive API errors before raising |
| F-string logging anti-pattern | Use `%` formatting: `logger.info("Generating %s", topic)` |
| Integration tests separate | Create test_integration.py with env var skip markers |
| RetryableHttpClient pattern | Use existing middleware from `teams/dawo/middleware/http_client.py` |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [project-context.md#Anti-Patterns]

1. **NEVER instantiate GeminiImageClient internally** - Accept via constructor injection
2. **NEVER hardcode API keys** - Use environment variables (GEMINI_API_KEY)
3. **NEVER swallow API exceptions** - Log and re-raise or return error result
4. **NEVER skip retry middleware** - All external calls must use retry wrapper
5. **NEVER leave AI metadata in images** - Always strip before upload
6. **NEVER make synchronous API calls** - All calls must be async (use asyncio.to_thread if needed)

### Test Fixtures

**Source:** [tests/teams/dawo/generators/test_orshot_graphics/conftest.py] patterns

```python
# tests/teams/dawo/generators/test_nano_banana/conftest.py
import pytest
from unittest.mock import AsyncMock
from pathlib import Path
from datetime import datetime, timezone

@pytest.fixture
def mock_gemini_client():
    """Mock GeminiImageClient for generator tests."""
    client = AsyncMock()
    client.generate_image.return_value = GeneratedImage(
        id="gen_123",
        prompt="Nordic minimalist wellness photography...",
        style=ImageStyle.NORDIC,
        image_url="/tmp/gen_123.png",
        local_path=Path("/tmp/gen_123.png"),
        width=1080,
        height=1080,
        created_at=datetime.now(timezone.utc),
    )
    client.download_image.return_value = Path("/tmp/gen_123.png")
    return client

@pytest.fixture
def mock_drive_client():
    """Mock GoogleDriveClient for asset upload tests."""
    client = AsyncMock()
    client.upload.return_value = DriveAsset(
        file_id="drive_456",
        name="2026-02-07_nordic_wellness_gen123.png",
        url="https://drive.google.com/file/d/drive_456",
        folder="DAWO.ECO/Assets/Generated",
    )
    return client

@pytest.fixture
def sample_generation_request():
    """Sample generation request for tests."""
    return ImageGenerationRequest(
        content_id="content_789",
        topic="morning wellness routine with natural light",
        style="wellness",
        brand_keywords=["peaceful", "natural", "Norwegian"],
        width=1080,
        height=1080,
    )
```

### Registration in team_spec.py

**Source:** [project-context.md#Agent-Registration]

```python
# teams/dawo/team_spec.py (add to existing registrations)

from teams.dawo.generators.nano_banana import (
    NanoBananaGenerator,
    NanoBananaGeneratorProtocol,
)

AGENTS: List[RegisteredAgent] = [
    # ... existing agents ...
    RegisteredAgent(
        name="nano_banana_generator",
        agent_class=NanoBananaGenerator,
        capabilities=["image_generation", "gemini", "visual_content", "ai_art"],
        tier=TIER_GENERATE,
    ),
]
```

### Project Structure Notes

- **Integration Location**: `integrations/gemini/` (complete existing scaffold)
- **Agent Location**: `teams/dawo/generators/nano_banana/` (new package)
- **Dependencies**: GeminiImageClient, GoogleDriveClient, PIL (for metadata)
- **Used by**: Content Team orchestrator, approval workflow
- **External API**: Google Gemini / Imagen API
- **Performance**: < 60 seconds per generation (API dependent)
- **Environment Variable**: `GEMINI_API_KEY`

### References

- [Source: epics.md#Story-3.5] - Original story requirements (FR11)
- [Source: architecture.md#External-Integration-Points] - Integration patterns
- [Source: project-context.md#Integration-Clients] - Protocol injection pattern
- [Source: integrations/gemini/client.py] - Existing scaffold to complete
- [Source: integrations/google_drive/] - Asset storage integration
- [Source: 3-2-google-drive-asset-storage.md] - Drive storage patterns
- [Source: 3-4-orshot-branded-graphics-integration.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 73 unit tests passing
- 7 integration tests (skipped without GEMINI_API_KEY)
- No regressions in existing tests

### Completion Notes List

1. **Gemini Client Implementation** - Completed full implementation in `integrations/gemini/client.py` with Imagen model support, retry middleware, timeout handling, and fallback to Gemini 2.0 Flash model
2. **NanoBananaGenerator Agent** - Created generator agent following OrshotRenderer pattern with dependency injection for GeminiImageClient and GoogleDriveClient
3. **Prompt Engineering** - Implemented DAWO brand-aligned prompt templates with STYLE_TEMPLATES for WELLNESS, NATURE, LIFESTYLE, and ABSTRACT styles
4. **Quality Scoring** - Implemented ImageQualityScorer with weighted scoring (aesthetic 30%, brand 40%, AI detectability 30%) and review threshold at 6.0
5. **AI Marker Prevention** - Implemented metadata stripping using PIL to remove EXIF and AI generation markers
6. **Google Drive Integration** - Graceful upload with failure handling (continues without Drive if upload fails)
7. **Test Coverage** - 73 unit tests covering all components, 7 integration tests that skip without API key

### File List

**New Files:**
- `integrations/gemini/__init__.py` - Package exports with client and metadata utilities
- `integrations/gemini/client.py` - GeminiImageClient with full implementation
- `integrations/gemini/metadata.py` - Metadata stripping and validation utilities (strip_ai_metadata, validate_no_ai_markers)
- `teams/dawo/generators/nano_banana/__init__.py` - Package exports
- `teams/dawo/generators/nano_banana/agent.py` - NanoBananaGenerator class
- `teams/dawo/generators/nano_banana/schemas.py` - ImageGenerationRequest, ImageGenerationResult, enums
- `teams/dawo/generators/nano_banana/prompts.py` - Prompt templates and builder functions
- `teams/dawo/generators/nano_banana/quality.py` - ImageQualityScorer and QualityAssessment
- `tests/integrations/test_gemini/__init__.py` - Test package
- `tests/integrations/test_gemini/conftest.py` - Test fixtures
- `tests/integrations/test_gemini/test_client.py` - 24 Gemini client tests
- `tests/integrations/test_gemini/test_metadata.py` - 20 metadata stripping/validation tests
- `tests/teams/dawo/generators/test_nano_banana/__init__.py` - Test package
- `tests/teams/dawo/generators/test_nano_banana/conftest.py` - Test fixtures
- `tests/teams/dawo/generators/test_nano_banana/test_agent.py` - Generator tests
- `tests/teams/dawo/generators/test_nano_banana/test_prompts.py` - Prompt engineering tests
- `tests/teams/dawo/generators/test_nano_banana/test_quality.py` - Quality scorer tests
- `tests/teams/dawo/generators/test_nano_banana/test_integration.py` - Integration tests with metadata verification
- `requirements.txt` - Dependencies including google-generativeai and Pillow

**Modified Files:**
- `integrations/__init__.py` - Added gemini exports
- `teams/dawo/__init__.py` - Added generators exports
- `teams/dawo/generators/__init__.py` - Added nano_banana exports
- `teams/dawo/team_spec.py` - Registered NanoBananaGenerator agent

---

## Change Log

- 2026-02-07: Story created by Scrum Master with comprehensive dev context
- 2026-02-07: All tasks completed. Implementation includes GeminiImageClient, NanoBananaGenerator agent, prompt engineering, quality scoring, AI marker prevention, and Google Drive integration. 73 unit tests passing, 7 integration tests (skipped without API key). Status changed to review.
- 2026-02-07: Code review fixes applied:
  - Created `integrations/gemini/metadata.py` with `strip_ai_metadata()` and `validate_no_ai_markers()` functions
  - Updated `agent.py` to use centralized metadata utilities (no more silent Pillow failures)
  - Added 20 unit tests for metadata stripping (Task 9.5 now properly tested)
  - Fixed integration test to use real Drive credentials when GOOGLE_APPLICATION_CREDENTIALS is set (Task 10.3)
  - Added metadata verification tests to confirm AI markers are stripped before upload (Task 10.4)
  - Corrected File List classifications (requirements.txt and __init__.py are new files, not modified)
