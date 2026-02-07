"""Instagram Transformer - standardizes data for Research Pool.

Implements the transform stage of the Harvester Framework:
    Scanner -> Harvester -> ThemeExtractor -> ClaimDetector -> [Transformer] -> Validator -> Publisher -> Research Pool

The InstagramTransformer:
    1. Takes harvested posts with theme and claim analysis
    2. Maps Instagram fields to Research Pool schema
    3. Sets CleanMarket flags for Epic 6 integration
    4. Returns TransformedResearch objects

Registration: team_spec.py as RegisteredService

Usage:
    # Created by Team Builder with injected dependencies
    transformer = InstagramTransformer(theme_extractor, claim_detector)

    # Execute transform stage
    transformed = await transformer.transform(harvested_posts)
"""

import logging
import re
from typing import Optional

from teams.dawo.research import TransformedResearch, ResearchSource, ComplianceStatus

from .schemas import (
    HarvestedPost,
    ThemeResult,
    ClaimDetectionResult,
)
from .theme_extractor import ThemeExtractor
from .claim_detector import HealthClaimDetector
from .config import MAX_CONTENT_LENGTH


# Module logger
logger = logging.getLogger(__name__)


class TransformerError(Exception):
    """Exception raised for transformer-level errors.

    Attributes:
        message: Error description
        partial_results: Any items transformed before error
    """

    def __init__(
        self,
        message: str,
        partial_results: Optional[list] = None,
    ):
        super().__init__(message)
        self.message = message
        self.partial_results = partial_results or []


class InstagramTransformer:
    """Instagram Transformer - standardizes data for Research Pool.

    Implements the transform stage of the Harvester Framework pipeline.
    Takes harvested posts and converts them to Research Pool schema,
    incorporating theme analysis and claim detection results.

    UNIQUE to Instagram:
        - Integrates ThemeExtractor results
        - Integrates HealthClaimDetector results
        - Sets cleanmarket_flag for Epic 6 integration
        - Preserves detected claims in source_metadata

    Features:
        - Research Pool schema mapping
        - Tag generation from hashtags and themes
        - CleanMarket flag propagation
        - Content sanitization

    All dependencies are injected via constructor - NEVER loads files directly.

    Attributes:
        _theme_extractor: LLM-powered theme extractor
        _claim_detector: LLM-powered claim detector
    """

    def __init__(
        self,
        theme_extractor: ThemeExtractor,
        claim_detector: HealthClaimDetector,
    ):
        """Initialize transformer with injected dependencies.

        Args:
            theme_extractor: Theme extraction service
            claim_detector: Health claim detection service
        """
        self._theme_extractor = theme_extractor
        self._claim_detector = claim_detector

    async def transform(
        self,
        harvested_posts: list[HarvestedPost],
    ) -> list[TransformedResearch]:
        """Transform harvested posts to Research Pool schema.

        Takes harvested posts, runs theme extraction and claim detection,
        then maps to Research Pool schema.

        Args:
            harvested_posts: List of harvested posts

        Returns:
            List of TransformedResearch objects ready for validation
        """
        logger.info(f"Starting transform for {len(harvested_posts)} posts")

        # Extract themes for all posts
        theme_results = await self._theme_extractor.extract_themes_batch(harvested_posts)

        # Detect claims for all posts
        claim_results = await self._claim_detector.detect_claims_batch(harvested_posts)

        # Transform each post
        transformed: list[TransformedResearch] = []
        for post in harvested_posts:
            try:
                theme = theme_results.get(post.media_id)
                claims = claim_results.get(post.media_id)

                item = self._transform_post(post, theme, claims)
                if item:
                    transformed.append(item)
            except Exception as e:
                logger.error(f"Failed to transform post {post.media_id}: {e}")
                # Continue with remaining posts

        logger.info(f"Transform complete: {len(transformed)} items created")
        return transformed

    def _transform_post(
        self,
        post: HarvestedPost,
        theme: Optional[ThemeResult],
        claims: Optional[ClaimDetectionResult],
    ) -> Optional[TransformedResearch]:
        """Transform a single post to Research Pool schema.

        Args:
            post: Harvested post data
            theme: Theme extraction result
            claims: Claim detection result

        Returns:
            TransformedResearch or None if failed
        """
        try:
            # Generate title - first 100 chars of caption or account-based
            title = self._generate_title(post)

            # Generate content - caption + theme analysis summary
            content = self._generate_content(post, theme)

            # Generate tags from hashtags and themes
            tags = self._generate_tags(post, theme)

            # Build source metadata
            source_metadata = self._build_metadata(post, theme, claims)

            # Determine if CleanMarket review needed
            cleanmarket_flag = claims.requires_cleanmarket_review if claims else False

            return TransformedResearch(
                source=ResearchSource.INSTAGRAM,
                title=title,
                content=content,
                url=post.permalink,
                tags=tags,
                source_metadata=source_metadata,
                created_at=post.timestamp,
                score=0.0,  # Will be set by scorer
                compliance_status=ComplianceStatus.COMPLIANT,  # Will be set by validator
            )

        except Exception as e:
            logger.error(f"Error transforming post {post.media_id}: {e}")
            return None

    def _generate_title(self, post: HarvestedPost) -> str:
        """Generate title for research item.

        Args:
            post: Harvested post data

        Returns:
            Title string (max 100 chars)
        """
        if post.caption and post.caption.strip():
            # First 100 chars of caption
            caption_clean = post.caption.strip()
            if len(caption_clean) > 100:
                return caption_clean[:97] + "..."
            return caption_clean
        else:
            # Account-based title
            return f"Instagram post from @{post.account_name}"

    def _generate_content(
        self,
        post: HarvestedPost,
        theme: Optional[ThemeResult],
    ) -> str:
        """Generate content for research item.

        Args:
            post: Harvested post data
            theme: Theme extraction result

        Returns:
            Content string with caption and theme summary
        """
        parts = []

        # Add caption
        if post.caption:
            parts.append(post.caption)

        # Add theme summary if available
        if theme and theme.content_type:
            summary = f"\n\n**Theme Analysis:**\n"
            summary += f"- Content Type: {theme.content_type}\n"
            if theme.messaging_patterns:
                summary += f"- Patterns: {', '.join(theme.messaging_patterns)}\n"
            if theme.key_topics:
                summary += f"- Topics: {', '.join(theme.key_topics)}\n"
            parts.append(summary)

        content = "\n".join(parts)

        # Truncate if too long
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH - 3] + "..."

        return content

    def _generate_tags(
        self,
        post: HarvestedPost,
        theme: Optional[ThemeResult],
    ) -> list[str]:
        """Generate tags for research item.

        Args:
            post: Harvested post data
            theme: Theme extraction result

        Returns:
            List of lowercase tags (no emojis)
        """
        tags = set()

        # Add hashtags (sanitized)
        for hashtag in post.hashtags[:10]:
            tag = self._sanitize_tag(hashtag)
            if tag:
                tags.add(tag)

        # Add theme topics
        if theme:
            for topic in theme.key_topics[:5]:
                tag = self._sanitize_tag(topic)
                if tag:
                    tags.add(tag)

            # Add content type as tag
            if theme.content_type:
                tags.add(theme.content_type.lower())

        # Add source-specific tags
        tags.add("instagram")
        if post.is_competitor:
            tags.add("competitor")

        return sorted(list(tags))[:15]  # Max 15 tags

    def _sanitize_tag(self, tag: str) -> Optional[str]:
        """Sanitize a tag by removing emojis and special characters.

        Args:
            tag: Raw tag string

        Returns:
            Sanitized tag or None if invalid
        """
        if not tag:
            return None

        # Remove emojis and special characters
        tag = re.sub(r'[^\w\s-]', '', tag.lower())
        tag = re.sub(r'\s+', '_', tag.strip())

        # Validate length
        if len(tag) < 2 or len(tag) > 50:
            return None

        return tag

    def _build_metadata(
        self,
        post: HarvestedPost,
        theme: Optional[ThemeResult],
        claims: Optional[ClaimDetectionResult],
    ) -> dict:
        """Build source_metadata for research item.

        Args:
            post: Harvested post data
            theme: Theme extraction result
            claims: Claim detection result

        Returns:
            Dict with Instagram-specific metadata
        """
        metadata = {
            "account": post.account_name,
            "account_type": post.account_type,
            "likes": post.likes,
            "comments": post.comments,
            "media_type": post.media_type,
            "hashtag_source": post.hashtag_source,
            "is_competitor": post.is_competitor,
        }

        # Add theme data
        if theme:
            metadata["theme"] = {
                "content_type": theme.content_type,
                "messaging_patterns": theme.messaging_patterns,
                "detected_products": theme.detected_products,
                "influencer_indicators": theme.influencer_indicators,
                "confidence": theme.confidence_score,
            }

        # Add claim data for CleanMarket integration
        if claims and claims.claims_detected:
            metadata["detected_claims"] = [
                {
                    "text": claim.claim_text,
                    "category": claim.category.value,
                    "severity": claim.severity,
                    "confidence": claim.confidence,
                }
                for claim in claims.claims_detected
            ]
            metadata["cleanmarket_summary"] = claims.summary
            metadata["overall_risk_level"] = claims.overall_risk_level

        return metadata
