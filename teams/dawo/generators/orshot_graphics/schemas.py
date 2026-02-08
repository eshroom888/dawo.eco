"""Schemas for Orshot Graphics Generator.

Defines data structures for graphics rendering requests and results.
These dataclasses enable type-safe, testable graphics generation pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class ContentType(Enum):
    """Content types for template selection.

    Maps to Instagram content formats for proper template matching.
    """

    INSTAGRAM_FEED = "feed_post"
    INSTAGRAM_STORY = "story"
    INSTAGRAM_REEL = "reel"


@dataclass
class RenderRequest:
    """Input for graphics rendering.

    Attributes:
        content_id: Unique content identifier for tracking
        content_type: Target content format for template selection
        headline: Main text for the graphic
        product_name: Product name if applicable
        date_display: Date text for the graphic (e.g., "Februar 2026")
        topic: Content topic for filename generation
        template_id: Specific template ID, or auto-select if None
    """

    content_id: str
    content_type: ContentType
    headline: str
    topic: str
    product_name: Optional[str] = None
    date_display: Optional[str] = None
    template_id: Optional[str] = None


@dataclass
class RenderResult:
    """Output from graphics rendering.

    Attributes:
        content_id: Original content identifier
        template_id: Template used for rendering
        template_name: Human-readable template name
        image_url: Orshot-generated CDN URL
        drive_url: Google Drive URL after upload
        drive_file_id: Google Drive file ID
        local_path: Local path if downloaded
        dimensions: Image dimensions (width, height)
        quality_score: Quality assessment score (1-10)
        usage_count: Current monthly render usage
        usage_warning: True if usage exceeds 80% threshold
        generation_time_ms: Time taken to generate in milliseconds
        created_at: Timestamp when graphic was generated
        success: Whether generation completed successfully
        error_message: Error details if generation failed
    """

    content_id: str
    template_id: str
    template_name: str
    image_url: str
    dimensions: tuple[int, int]
    quality_score: float
    usage_count: int
    usage_warning: bool
    generation_time_ms: int
    drive_url: Optional[str] = None
    drive_file_id: Optional[str] = None
    local_path: Optional[Path] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_message: str = ""

    @classmethod
    def failure(cls, content_id: str, error: str) -> "RenderResult":
        """Create a failed result with error message.

        Args:
            content_id: Original content identifier
            error: Description of what went wrong

        Returns:
            RenderResult with success=False and error details
        """
        return cls(
            content_id=content_id,
            template_id="",
            template_name="",
            image_url="",
            dimensions=(0, 0),
            quality_score=0.0,
            usage_count=0,
            usage_warning=False,
            generation_time_ms=0,
            success=False,
            error_message=error,
        )
