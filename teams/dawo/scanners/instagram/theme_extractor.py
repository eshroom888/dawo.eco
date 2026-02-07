"""Theme Extractor - LLM-powered theme extraction from Instagram captions.

Implements the theme extraction stage of the Harvester Framework:
    Scanner -> Harvester -> [ThemeExtractor] -> ClaimDetector -> Transformer -> Validator -> Publisher -> Research Pool

The ThemeExtractor:
    1. Takes harvested posts
    2. Uses LLM (tier="generate") to analyze caption content
    3. Extracts content type, messaging patterns, topics
    4. Returns ThemeResult for each post

Registration: team_spec.py with tier="generate" (maps to Sonnet at runtime)

Usage:
    # Created by Team Builder with injected dependencies
    extractor = ThemeExtractor(llm_client)

    # Execute theme extraction
    theme = await extractor.extract_themes(caption, hashtags, account_name)
"""

import json
import logging
from typing import Any, Optional

from .schemas import ThemeResult, HarvestedPost
from .prompts import (
    THEME_EXTRACTION_PROMPT,
    THEME_EXTRACTION_SHORT_PROMPT,
    SHORT_CAPTION_THRESHOLD,
)


# Module logger
logger = logging.getLogger(__name__)


class ThemeExtractionError(Exception):
    """Exception raised for theme extraction errors.

    Attributes:
        message: Error description
        post_id: Media ID of the post that failed
    """

    def __init__(
        self,
        message: str,
        post_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.post_id = post_id


class ThemeExtractor:
    """LLM-powered theme extraction from Instagram captions.

    Uses tier="generate" (Sonnet) for quality theme analysis.
    Extracts content type, messaging patterns, and topics from
    Instagram post captions.

    Features:
        - Content type classification
        - Messaging pattern detection
        - Product/brand mention extraction
        - Influencer indicator detection
        - Topic tagging

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _llm: LLM client for theme extraction
    """

    def __init__(self, llm_client: Any):
        """Initialize theme extractor with injected dependencies.

        Args:
            llm_client: LLM client configured for tier="generate"
        """
        self._llm = llm_client

    async def extract_themes(
        self,
        caption: str,
        hashtags: list[str],
        account_name: str,
    ) -> ThemeResult:
        """Extract themes and patterns from Instagram post.

        Args:
            caption: Full post caption text
            hashtags: List of hashtags used
            account_name: Instagram account name

        Returns:
            ThemeResult with themes, patterns, and topics

        Raises:
            ThemeExtractionError: If extraction fails
        """
        if not caption or not caption.strip():
            # Return default result for empty captions
            return ThemeResult(
                content_type="promotional",
                messaging_patterns=[],
                detected_products=[],
                influencer_indicators=False,
                key_topics=list(hashtags[:5]) if hashtags else [],
                confidence_score=0.3,
            )

        # Choose prompt based on caption length
        if len(caption) < SHORT_CAPTION_THRESHOLD:
            prompt = THEME_EXTRACTION_SHORT_PROMPT
        else:
            prompt = THEME_EXTRACTION_PROMPT

        # Format prompt
        formatted_prompt = prompt.format(
            account_name=account_name,
            hashtags=", ".join(hashtags) if hashtags else "none",
            caption_length=len(caption),
            caption=caption[:5000],  # Truncate very long captions
        )

        try:
            # Call LLM
            response = await self._llm.generate(
                prompt=formatted_prompt,
                max_tokens=500,
            )

            # Parse JSON response
            return self._parse_response(response, hashtags)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Return default result on parse failure
            return self._default_result(hashtags)
        except Exception as e:
            logger.error(f"Theme extraction failed: {e}")
            raise ThemeExtractionError(f"Failed to extract themes: {e}")

    async def extract_themes_batch(
        self,
        posts: list[HarvestedPost],
    ) -> dict[str, ThemeResult]:
        """Extract themes for multiple posts.

        Args:
            posts: List of harvested posts

        Returns:
            Dict mapping media_id to ThemeResult
        """
        results: dict[str, ThemeResult] = {}

        for post in posts:
            try:
                theme = await self.extract_themes(
                    caption=post.caption,
                    hashtags=post.hashtags,
                    account_name=post.account_name,
                )
                results[post.media_id] = theme
            except ThemeExtractionError as e:
                logger.warning(f"Theme extraction failed for {post.media_id}: {e}")
                results[post.media_id] = self._default_result(post.hashtags)

        return results

    def _parse_response(
        self,
        response: str,
        fallback_hashtags: list[str],
    ) -> ThemeResult:
        """Parse LLM response into ThemeResult.

        Args:
            response: Raw LLM response text
            fallback_hashtags: Hashtags to use if topics extraction fails

        Returns:
            ThemeResult parsed from response
        """
        # Try to extract JSON from response
        try:
            # Handle potential markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            data = json.loads(text)

            return ThemeResult(
                content_type=data.get("content_type", "promotional"),
                messaging_patterns=data.get("messaging_patterns", []),
                detected_products=data.get("detected_products", []),
                influencer_indicators=data.get("influencer_indicators", False),
                key_topics=data.get("key_topics", fallback_hashtags[:5]),
                confidence_score=min(1.0, max(0.0, data.get("confidence_score", 0.5))),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse theme response: {e}")
            return self._default_result(fallback_hashtags)

    def _default_result(self, hashtags: list[str]) -> ThemeResult:
        """Create default ThemeResult for failed extractions.

        Args:
            hashtags: Hashtags to use as fallback topics

        Returns:
            Default ThemeResult with low confidence
        """
        return ThemeResult(
            content_type="promotional",
            messaging_patterns=[],
            detected_products=[],
            influencer_indicators=False,
            key_topics=list(hashtags[:5]) if hashtags else [],
            confidence_score=0.3,
        )
