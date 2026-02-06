"""YouTube Transformer - standardizes videos for Research Pool.

Implements the transform stage of the Harvester Framework pipeline:
    Scanner → Harvester → InsightExtractor → [Transformer] → Validator → Publisher → Research Pool

The transformer takes harvested videos with extracted insights and converts
them to the TransformedResearch schema required by the Research Pool.

UNIQUE to YouTube: Uses KeyInsightExtractor for LLM-powered summarization
before transformation. Videos without transcripts skip insight extraction.

Usage:
    insight_extractor = KeyInsightExtractor(llm_client)
    transformer = YouTubeTransformer(insight_extractor)
    standardized = await transformer.transform(harvested_videos)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from teams.dawo.research import TransformedResearch, ResearchSource

from .schemas import HarvestedVideo, InsightResult, QuotableInsight
from .config import MAX_CONTENT_LENGTH


# Module logger
logger = logging.getLogger(__name__)

# YouTube URL base
YOUTUBE_URL_BASE = "https://youtube.com/watch?v="


class TransformerError(Exception):
    """Exception raised for transformer-level errors.

    Attributes:
        message: Error description
        video_id: YouTube video ID (if available)
    """

    def __init__(self, message: str, video_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.video_id = video_id


class YouTubeTransformer:
    """YouTube Transformer - converts videos to Research Pool schema.

    Takes harvested videos and transforms them to the standardized
    TransformedResearch format required by the Research Pool.

    UNIQUE to YouTube: Integrates with KeyInsightExtractor to extract
    LLM-powered insights from transcripts before transformation.

    Features:
        - LLM insight extraction via KeyInsightExtractor
        - Field mapping to Research Pool schema
        - Content combining (summary + quotable insights)
        - Tag generation from key topics
        - Content length truncation
        - Graceful handling of videos without transcripts

    Attributes:
        _insight_extractor: KeyInsightExtractor for LLM summarization
    """

    def __init__(self, insight_extractor: Any):
        """Initialize transformer with insight extractor.

        Args:
            insight_extractor: KeyInsightExtractor for LLM insight extraction
                             Injected by Team Builder - uses tier="generate"
        """
        self._insight_extractor = insight_extractor

    async def transform(
        self,
        harvested_videos: list[HarvestedVideo],
    ) -> list[TransformedResearch]:
        """Transform harvested videos to Research Pool schema.

        For each video:
        1. Extract insights using LLM (if transcript available)
        2. Map YouTube fields to TransformedResearch schema
        3. Combine summary and quotable insights into content
        4. Generate tags from key topics

        Args:
            harvested_videos: Videos from harvester stage with transcripts

        Returns:
            List of TransformedResearch objects ready for validation
        """
        if not harvested_videos:
            return []

        logger.info(f"Transforming {len(harvested_videos)} videos")

        transformed: list[TransformedResearch] = []

        for video in harvested_videos:
            try:
                item = await self._transform_single(video)
                transformed.append(item)
            except Exception as e:
                logger.error(f"Failed to transform video {video.video_id}: {e}")
                # Continue with remaining videos

        logger.info(f"Transformed {len(transformed)} videos successfully")
        return transformed

    async def _transform_single(self, video: HarvestedVideo) -> TransformedResearch:
        """Transform a single video to Research Pool schema.

        Args:
            video: Harvested video to transform

        Returns:
            TransformedResearch object
        """
        # Extract insights if transcript available
        insight_result: Optional[InsightResult] = None

        if video.transcript_available and video.transcript:
            try:
                insight_result = await self._insight_extractor.extract_insights(
                    transcript=video.transcript,
                    title=video.title,
                    channel_name=video.channel_title,
                )
                logger.debug(
                    f"Extracted insights for video {video.video_id}: "
                    f"{len(insight_result.quotable_insights)} insights"
                )
            except Exception as e:
                logger.warning(
                    f"Insight extraction failed for video {video.video_id}: {e}"
                )
                # Continue without insights

        # Build content from insights or description
        content = self._build_content(video, insight_result)

        # Sanitize content
        content = self._sanitize_content(content)

        # Generate tags from insights or title
        tags = self._generate_tags(video, insight_result)

        # Build source metadata
        source_metadata = {
            "channel": video.channel_title,
            "channel_id": video.channel_id,
            "views": video.view_count,
            "likes": video.like_count,
            "comments": video.comment_count,
            "duration_seconds": video.duration_seconds,
            "video_id": video.video_id,
            "has_transcript": video.transcript_available,
            "transcript_language": video.transcript_language,
            "is_auto_generated": video.is_auto_generated,
            "insight_count": len(insight_result.quotable_insights) if insight_result else 0,
            "confidence_score": insight_result.confidence_score if insight_result else 0.0,
        }

        # Build full YouTube URL
        url = f"{YOUTUBE_URL_BASE}{video.video_id}"

        return TransformedResearch(
            source=ResearchSource.YOUTUBE,
            title=video.title[:500],  # Enforce max title length
            content=content,
            url=url,
            tags=tags,
            source_metadata=source_metadata,
            created_at=video.published_at,
        )

    def _build_content(
        self,
        video: HarvestedVideo,
        insight_result: Optional[InsightResult],
    ) -> str:
        """Build content from insights or video description.

        Combines main summary and quotable insights into structured content.

        Args:
            video: Harvested video
            insight_result: LLM insight extraction result (if available)

        Returns:
            Combined content string
        """
        parts: list[str] = []

        if insight_result:
            # Add main summary
            if insight_result.main_summary:
                parts.append(f"Summary: {insight_result.main_summary}")

            # Add quotable insights
            if insight_result.quotable_insights:
                parts.append("\nKey Insights:")
                for i, insight in enumerate(insight_result.quotable_insights, 1):
                    insight_text = f"{i}. \"{insight.text}\""
                    if insight.context:
                        insight_text += f" ({insight.context})"
                    if insight.is_claim:
                        insight_text += " [CLAIM]"
                    parts.append(insight_text)
        else:
            # No insights - use video description
            parts.append(video.description or video.title)

        return "\n".join(parts)

    def _sanitize_content(self, content: str) -> str:
        """Sanitize content by truncating if too long.

        Args:
            content: Raw content string

        Returns:
            Sanitized content string
        """
        # Truncate if too long
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[: MAX_CONTENT_LENGTH - 3] + "..."

        return content

    def _generate_tags(
        self,
        video: HarvestedVideo,
        insight_result: Optional[InsightResult],
    ) -> list[str]:
        """Generate tags from insights or video content.

        Uses key topics from LLM extraction, supplemented by
        keyword detection from title.

        Args:
            video: Harvested video
            insight_result: LLM insight extraction result (if available)

        Returns:
            List of tag strings
        """
        tags: set[str] = set()

        # Add tags from insight extraction
        if insight_result and insight_result.key_topics:
            tags.update(insight_result.key_topics)

        # Keyword-based tags from title
        title_lower = video.title.lower()
        keyword_to_tag = {
            "lion's mane": "lions_mane",
            "lions mane": "lions_mane",
            "chaga": "chaga",
            "reishi": "reishi",
            "cordyceps": "cordyceps",
            "shiitake": "shiitake",
            "maitake": "maitake",
            "mushroom": "mushroom",
            "adaptogen": "adaptogen",
        }

        for keyword, tag in keyword_to_tag.items():
            if keyword in title_lower:
                tags.add(tag)

        # Topic-based tags from title
        topic_keywords = {
            "cognitive": ["brain", "focus", "memory", "cognitive", "mental"],
            "immune": ["immune", "immunity"],
            "energy": ["energy", "fatigue", "stamina"],
            "research": ["study", "research", "science", "scientific"],
            "review": ["review", "comparison", "vs"],
        }

        for tag, keywords in topic_keywords.items():
            if any(kw in title_lower for kw in keywords):
                tags.add(tag)

        return sorted(list(tags))
