"""Schemas for Instagram Caption Generator.

Defines data structures for caption generation requests and results.
These dataclasses enable type-safe, testable caption generation pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CaptionRequest:
    """Input for caption generation.

    Attributes:
        research_item_id: ID of the source research item
        research_source: Source platform (reddit, youtube, pubmed, news, instagram)
        research_content: Extracted insights from research
        research_tags: Tags associated with the research item
        product_handle: Optional Shopify product handle for product enrichment
        content_id: ID for UTM tracking in product links
        target_topic: Primary topic for hashtag selection (wellness, mushrooms, lifestyle)
    """

    research_item_id: str
    research_source: str
    research_content: str
    research_tags: list[str] = field(default_factory=list)
    product_handle: Optional[str] = None
    content_id: str = ""
    target_topic: str = "wellness"


@dataclass
class CaptionResult:
    """Output from caption generation.

    Attributes:
        caption_text: Generated Norwegian caption text
        word_count: Number of words in caption (target: 180-220)
        hashtags: Generated hashtags including brand tags
        product_link: Product URL with UTM parameters (if product provided)
        brand_voice_status: Validation status (PASS, NEEDS_REVISION, FAIL)
        brand_voice_score: Brand alignment score (0.0-1.0)
        revision_suggestions: Suggestions if validation requires revision
        authenticity_score: AI-generic pattern detection score (0.0-1.0, higher = more human)
        generation_time_ms: Time taken to generate caption in milliseconds
        created_at: Timestamp when caption was generated
        research_citation: Formatted citation for research source
        success: Whether generation completed successfully
        error_message: Error details if generation failed
    """

    caption_text: str
    word_count: int
    hashtags: list[str] = field(default_factory=list)
    product_link: Optional[str] = None
    brand_voice_status: str = "PENDING"
    brand_voice_score: float = 0.0
    revision_suggestions: list[str] = field(default_factory=list)
    authenticity_score: float = 1.0
    generation_time_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    research_citation: str = ""
    success: bool = True
    error_message: str = ""

    @classmethod
    def failure(cls, error: str) -> "CaptionResult":
        """Create a failed result with error message.

        Args:
            error: Description of what went wrong

        Returns:
            CaptionResult with success=False and error details
        """
        return cls(
            caption_text="",
            word_count=0,
            success=False,
            error_message=error,
        )
