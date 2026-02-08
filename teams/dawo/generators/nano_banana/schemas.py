"""Schemas for Nano Banana AI Image Generator.

Defines data structures for AI image generation requests and results.
These dataclasses enable type-safe, testable image generation pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class ImageStyleType(Enum):
    """Image style types for AI generation.

    Maps to DAWO brand aesthetic categories.
    """

    WELLNESS = "wellness"  # Nordic minimalist wellness
    NATURE = "nature"  # Norwegian forest/landscape
    LIFESTYLE = "lifestyle"  # Scandinavian lifestyle/hygge
    ABSTRACT = "abstract"  # Artistic/conceptual


class ContentFormat(Enum):
    """Content format types for dimension selection.

    Maps to Instagram content formats.
    """

    FEED_SQUARE = "feed_square"  # 1080x1080
    FEED_PORTRAIT = "feed_portrait"  # 1080x1350
    STORY = "story"  # 1080x1920
    REEL = "reel"  # 1080x1920


@dataclass
class ImageGenerationRequest:
    """Input for AI image generation.

    Attributes:
        content_id: Unique content identifier for tracking
        topic: Topic/theme for the image
        style: Image style for aesthetic selection
        content_format: Target content format for dimensions
        brand_keywords: Additional brand-aligned keywords
        avoid_elements: Elements to exclude from image
        width: Image width override (default from format)
        height: Image height override (default from format)
    """

    content_id: str
    topic: str
    style: ImageStyleType = ImageStyleType.WELLNESS
    content_format: ContentFormat = ContentFormat.FEED_SQUARE
    brand_keywords: list[str] = field(default_factory=list)
    avoid_elements: list[str] = field(default_factory=list)
    width: Optional[int] = None
    height: Optional[int] = None

    def get_dimensions(self) -> tuple[int, int]:
        """Get image dimensions based on format or overrides.

        Returns:
            Tuple of (width, height)
        """
        if self.width and self.height:
            return (self.width, self.height)

        # Default dimensions per content format
        format_dims = {
            ContentFormat.FEED_SQUARE: (1080, 1080),
            ContentFormat.FEED_PORTRAIT: (1080, 1350),
            ContentFormat.STORY: (1080, 1920),
            ContentFormat.REEL: (1080, 1920),
        }
        return format_dims.get(self.content_format, (1080, 1080))


@dataclass
class ImageGenerationResult:
    """Output from AI image generation.

    Attributes:
        content_id: Original content identifier
        image_id: Unique image generation ID
        prompt_used: Full prompt sent to Gemini
        style: Style used for generation
        image_url: Local or temporary URL to image
        drive_url: Google Drive URL after upload
        drive_file_id: Google Drive file ID
        local_path: Local path to image file
        dimensions: Image dimensions (width, height)
        quality_score: Quality assessment score (1-10)
        needs_review: True if score < 6
        quality_flags: Specific quality issues identified
        generation_time_ms: Time taken to generate in milliseconds
        created_at: Timestamp when image was generated
        success: Whether generation completed successfully
        error_message: Error details if generation failed
    """

    content_id: str
    image_id: str
    prompt_used: str
    style: str
    image_url: str
    dimensions: tuple[int, int]
    quality_score: float
    needs_review: bool
    generation_time_ms: int
    drive_url: Optional[str] = None
    drive_file_id: Optional[str] = None
    local_path: Optional[Path] = None
    quality_flags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_message: str = ""

    @classmethod
    def failure(cls, content_id: str, error: str) -> "ImageGenerationResult":
        """Create a failed result with error message.

        Args:
            content_id: Original content identifier
            error: Description of what went wrong

        Returns:
            ImageGenerationResult with success=False and error details
        """
        return cls(
            content_id=content_id,
            image_id="",
            prompt_used="",
            style="",
            image_url="",
            dimensions=(0, 0),
            quality_score=0.0,
            needs_review=True,
            generation_time_ms=0,
            success=False,
            error_message=error,
        )
