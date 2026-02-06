"""Key Insight Extractor - LLM-powered insight extraction from video transcripts.

Implements the insight extraction stage of the YouTube Harvester Framework pipeline:
    Scanner → Harvester → [InsightExtractor] → Transformer → Validator → Publisher → Research Pool

This stage is UNIQUE to YouTube scanner - uses tier="generate" (Sonnet) for
quality summarization of video transcripts. Unlike Reddit scanner's rule-based
transformation, this uses LLM to extract meaningful insights.

CRITICAL: This component uses tier="generate" which maps to Sonnet at runtime.
NEVER reference model names directly in code - use tier terminology only.

Usage:
    llm_client = get_llm_client_for_tier("generate")  # Injected by Team Builder
    extractor = KeyInsightExtractor(llm_client)
    result = await extractor.extract_insights(transcript, title, channel_name)
"""

import json
import logging
import re
from typing import Any, Optional

from .schemas import InsightResult, QuotableInsight
from .prompts import (
    KEY_INSIGHT_EXTRACTION_PROMPT,
    KEY_INSIGHT_EXTRACTION_SHORT_PROMPT,
    SHORT_TRANSCRIPT_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
)


# Module logger
logger = logging.getLogger(__name__)


class InsightExtractionError(Exception):
    """Exception raised for insight extraction errors.

    Attributes:
        message: Error description
        video_id: YouTube video ID (if available)
        video_title: Video title (if available)
    """

    def __init__(
        self,
        message: str,
        video_id: Optional[str] = None,
        video_title: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.video_id = video_id
        self.video_title = video_title


class KeyInsightExtractor:
    """LLM-powered key insight extractor for video transcripts.

    Uses tier="generate" (Sonnet) to summarize video transcripts and extract:
        - Main summary (100-200 words)
        - Quotable insights (max 3)
        - Key topics for tagging

    This is the only LLM-powered stage in the YouTube pipeline. All other
    stages use rule-based processing.

    Features:
        - Adaptive prompts (full vs short based on transcript length)
        - JSON response parsing with validation
        - Confidence scoring for output quality
        - Graceful handling of malformed responses

    Attributes:
        _llm_client: LLM client for generate tier (injected)
    """

    def __init__(self, llm_client: Any):
        """Initialize insight extractor with LLM client.

        Args:
            llm_client: LLM client for tier="generate" (Sonnet)
                       Expected interface: async generate(prompt: str) -> str
        """
        self._llm_client = llm_client

    async def extract_insights(
        self,
        transcript: str,
        title: str,
        channel_name: str,
    ) -> InsightResult:
        """Extract key insights from video transcript using LLM.

        Uses tier="generate" (Sonnet) to analyze transcript and extract
        structured insights including summary, quotables, and topics.

        Args:
            transcript: Full video transcript text
            title: Video title for context
            channel_name: Channel name for context

        Returns:
            InsightResult with summary, quotable insights, and topics

        Raises:
            InsightExtractionError: If extraction fails (API error, parse error)
        """
        logger.debug(f"Extracting insights from video: {title[:50]}...")

        # Calculate word count for prompt selection
        word_count = len(transcript.split())
        logger.debug(f"Transcript word count: {word_count}")

        # Select prompt based on transcript length
        if word_count < SHORT_TRANSCRIPT_THRESHOLD:
            prompt = KEY_INSIGHT_EXTRACTION_SHORT_PROMPT.format(
                video_title=title,
                channel_name=channel_name,
                transcript=transcript,
            )
            logger.debug("Using short prompt for brief transcript")
        else:
            prompt = KEY_INSIGHT_EXTRACTION_PROMPT.format(
                video_title=title,
                channel_name=channel_name,
                transcript_length=word_count,
                transcript=transcript,
            )
            logger.debug("Using full prompt for standard transcript")

        try:
            # Call LLM for insight extraction
            response = await self._llm_client.generate(prompt)
            logger.debug(f"LLM response length: {len(response)} chars")

            # Parse JSON response
            result = self._parse_response(response, title)

            # Log confidence warnings
            if result.confidence_score < LOW_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Low confidence ({result.confidence_score}) for video: {title}"
                )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise InsightExtractionError(
                message=f"Invalid JSON response from LLM: {e}",
                video_title=title,
            ) from e
        except Exception as e:
            logger.error(f"Insight extraction failed for '{title}': {e}")
            raise InsightExtractionError(
                message=f"Insight extraction failed: {e}",
                video_title=title,
            ) from e

    def _parse_response(self, response: str, title: str) -> InsightResult:
        """Parse LLM response JSON into InsightResult.

        Handles extraction of JSON from response text, which may include
        markdown code blocks or extra whitespace.

        Args:
            response: Raw LLM response text
            title: Video title for error context

        Returns:
            InsightResult with parsed data

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Extract JSON from response (may be wrapped in markdown code block)
        json_str = self._extract_json(response)

        # Parse JSON
        data = json.loads(json_str)

        # Extract quotable insights
        quotable_insights = []
        for insight_data in data.get("quotable_insights", []):
            if isinstance(insight_data, dict):
                insight = QuotableInsight(
                    text=insight_data.get("text", ""),
                    context=insight_data.get("context", ""),
                    topic=insight_data.get("topic", ""),
                    is_claim=insight_data.get("is_claim", False),
                )
                quotable_insights.append(insight)

        # Build result with defaults for missing fields
        return InsightResult(
            main_summary=data.get("main_summary", ""),
            quotable_insights=quotable_insights,
            key_topics=data.get("key_topics", []),
            confidence_score=data.get("confidence_score", 0.0),
        )

    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response.

        LLMs often wrap JSON in markdown code blocks or add explanatory text.
        This method extracts the raw JSON.

        Args:
            response: Raw LLM response

        Returns:
            Extracted JSON string
        """
        # Try to find JSON in markdown code block
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        match = re.search(code_block_pattern, response)
        if match:
            return match.group(1).strip()

        # Try to find JSON object directly
        json_object_pattern = r"\{[\s\S]*\}"
        match = re.search(json_object_pattern, response)
        if match:
            return match.group(0)

        # Return as-is and let JSON parser handle it
        return response.strip()
