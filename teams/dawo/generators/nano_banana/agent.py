"""Nano Banana AI Image Generator Agent.

Generates AI images using Gemini/Imagen API with DAWO brand aesthetics.
Stores generated assets to Google Drive with quality scoring.

Configuration is received via dependency injection - NEVER loads config directly.

The generator follows the Content Generator Framework:
1. Build prompt with DAWO brand alignment
2. Generate image via Gemini API
3. Strip AI metadata from image
4. Upload to Google Drive
5. Calculate quality score
6. Return result with asset details
"""

import logging
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from integrations.gemini import (
    GeminiImageClientProtocol,
    GeneratedImage,
    ImageStyle,
    strip_ai_metadata,
    validate_no_ai_markers,
)
from integrations.google_drive import (
    GoogleDriveClientProtocol,
    AssetType,
    DriveAsset,
)

from .schemas import (
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageStyleType,
)
from .prompts import (
    build_prompt,
    get_negative_prompt,
    get_brand_keywords,
)
from .quality import (
    ImageQualityScorer,
    QualityAssessment,
)

logger = logging.getLogger(__name__)


# Map our ImageStyleType to Gemini's ImageStyle
STYLE_MAP: dict[ImageStyleType, ImageStyle] = {
    ImageStyleType.WELLNESS: ImageStyle.NORDIC,
    ImageStyleType.NATURE: ImageStyle.NATURAL,
    ImageStyleType.LIFESTYLE: ImageStyle.LIFESTYLE,
    ImageStyleType.ABSTRACT: ImageStyle.ABSTRACT,
}


@runtime_checkable
class NanoBananaGeneratorProtocol(Protocol):
    """Protocol defining the Nano Banana generator interface.

    Any class implementing this protocol can be used for AI image generation.
    Enables easy mocking and alternative implementations.
    """

    async def generate(
        self, request: ImageGenerationRequest
    ) -> ImageGenerationResult:
        """Generate an AI image.

        Args:
            request: Image generation request with topic and style

        Returns:
            ImageGenerationResult with image URLs and quality info
        """
        ...


class NanoBananaGenerator:
    """AI image generator using Gemini/Imagen API.

    Generates images with DAWO brand aesthetics (Nordic/Scandinavian).
    Stores results to Google Drive with quality scoring.

    CRITICAL: Accept config via dependency injection - NEVER load directly.

    Attributes:
        _gemini: Gemini client for image generation
        _drive: Google Drive client for asset storage
        _scorer: Quality scorer for generated images
    """

    def __init__(
        self,
        gemini: GeminiImageClientProtocol,
        drive: GoogleDriveClientProtocol,
    ) -> None:
        """Initialize the AI image generator with injected dependencies.

        Args:
            gemini: Gemini client for image generation.
                   Injected by Team Builder - NEVER instantiate directly.
            drive: Google Drive client for asset storage.
        """
        self._gemini = gemini
        self._drive = drive
        self._scorer = ImageQualityScorer()

        logger.info("NanoBananaGenerator initialized")

    async def generate(
        self, request: ImageGenerationRequest
    ) -> ImageGenerationResult:
        """Generate an AI image from request.

        Follows the Content Generator Framework:
        1. Build prompt with DAWO brand alignment
        2. Generate image via Gemini
        3. Strip AI metadata
        4. Upload to Drive
        5. Calculate quality score
        6. Return result

        Args:
            request: Image generation request

        Returns:
            ImageGenerationResult with image URLs and quality info
        """
        start_time = time.time()

        try:
            # Step 1: Build prompt with DAWO aesthetics
            prompt = self._build_request_prompt(request)
            negative_prompt = get_negative_prompt(
                request.style,
                request.avoid_elements,
            )

            # Get dimensions
            width, height = request.get_dimensions()

            # Map style
            gemini_style = STYLE_MAP.get(request.style, ImageStyle.NORDIC)

            logger.info(
                "Generating image for %s: style=%s, dimensions=%dx%d",
                request.content_id,
                request.style.value,
                width,
                height,
            )

            # Step 2: Generate image via Gemini
            image = await self._gemini.generate_image(
                prompt=prompt,
                style=gemini_style,
                width=width,
                height=height,
                negative_prompt=negative_prompt,
            )

            # Step 3: Download and strip metadata
            temp_path = await self._download_and_clean(image, request)

            # Step 4: Upload to Google Drive
            drive_asset = await self._upload_to_drive(temp_path, request, image)

            # Step 5: Calculate quality score
            quality = self._scorer.score(
                image=image,
                prompt_compliance=0.8,  # Estimate based on successful generation
                generation_success=bool(image.local_path),
            )

            # Step 6: Build result
            generation_time_ms = int((time.time() - start_time) * 1000)

            return ImageGenerationResult(
                content_id=request.content_id,
                image_id=image.id,
                prompt_used=prompt,
                style=request.style.value,
                image_url=image.image_url,
                drive_url=drive_asset.web_view_link if drive_asset else None,
                drive_file_id=drive_asset.id if drive_asset else None,
                local_path=temp_path,
                dimensions=(image.width, image.height),
                quality_score=quality.overall_score,
                needs_review=quality.needs_review,
                quality_flags=quality.flags,
                generation_time_ms=generation_time_ms,
                success=True,
            )

        except Exception as e:
            logger.error(
                "Image generation failed for %s: %s",
                request.content_id,
                str(e),
            )
            return ImageGenerationResult.failure(request.content_id, str(e))

    def _build_request_prompt(self, request: ImageGenerationRequest) -> str:
        """Build prompt from request with brand alignment.

        Args:
            request: Image generation request

        Returns:
            Complete prompt string
        """
        # Use default brand keywords if none provided
        keywords = request.brand_keywords or get_brand_keywords()

        return build_prompt(
            topic=request.topic,
            style=request.style,
            brand_keywords=keywords,
        )

    async def _download_and_clean(
        self,
        image: GeneratedImage,
        request: ImageGenerationRequest,
    ) -> Path:
        """Download image and strip AI metadata.

        Args:
            image: Generated image
            request: Original request

        Returns:
            Path to cleaned image
        """
        # Generate unique filename (no "ai-generated" indicators)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        short_id = str(uuid.uuid4())[:8]
        safe_topic = "".join(c for c in request.topic.lower() if c.isalnum())[:20]
        filename = f"{date_str}_{request.style.value}_{safe_topic}_{short_id}.png"

        # Use system temp directory
        temp_dir = Path(tempfile.gettempdir()) / "dawo_gemini"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / filename

        # Download image
        await self._gemini.download_image(image, temp_path)

        # Strip AI metadata
        self._strip_metadata(temp_path)

        logger.debug("Downloaded and cleaned image to %s", temp_path)
        return temp_path

    def _strip_metadata(self, image_path: Path) -> None:
        """Strip EXIF and AI metadata from image.

        Uses the centralized metadata stripping utility which raises
        MetadataError if Pillow is not available (no silent failures).

        Args:
            image_path: Path to image file

        Raises:
            MetadataError: If Pillow is not installed or stripping fails
        """
        # Use centralized metadata utility - raises on failure (no silent skip)
        strip_ai_metadata(image_path)

        # Validate the result
        is_clean, issues = validate_no_ai_markers(image_path)
        if not is_clean:
            logger.warning(
                "Image %s still has markers after stripping: %s",
                image_path.name,
                ", ".join(issues),
            )

    async def _upload_to_drive(
        self,
        local_path: Path,
        request: ImageGenerationRequest,
        image: GeneratedImage,
    ) -> Optional[DriveAsset]:
        """Upload image to Google Drive.

        Uploads to DAWO.ECO/Assets/Generated/ folder.

        Args:
            local_path: Path to local file
            request: Original request
            image: Generated image metadata

        Returns:
            DriveAsset if successful, None on failure
        """
        try:
            metadata = {
                "content_id": request.content_id,
                "image_id": image.id,
                "style": request.style.value,
                "topic": request.topic,
                "prompt": image.prompt[:500],  # Truncate for metadata
            }

            asset = await self._drive.upload_asset(
                file_path=local_path,
                asset_type=AssetType.AI_IMAGE,
                metadata=metadata,
            )

            logger.info(
                "Uploaded image to Drive: %s -> %s",
                local_path.name,
                asset.id,
            )
            return asset

        except Exception as e:
            logger.error(
                "Failed to upload to Drive (keeping local copy): %s", e
            )
            return None
