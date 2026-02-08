"""Image quality scoring for AI-generated images.

Provides quality assessment for generated images based on:
- Aesthetic appeal
- Brand alignment
- AI detectability risk
"""

import logging
from dataclasses import dataclass
from typing import Optional

from integrations.gemini import GeneratedImage, ImageStyle

logger = logging.getLogger(__name__)


@dataclass
class QualityAssessment:
    """Quality assessment result for a generated image.

    Attributes:
        aesthetic_score: Visual appeal score (1-10)
        brand_alignment: DAWO brand match score (1-10)
        ai_detectability: Natural appearance score (1-10, higher = less detectable)
        overall_score: Weighted average score (1-10)
        needs_review: True if overall < 6
        flags: Specific quality issues identified
    """

    aesthetic_score: float
    brand_alignment: float
    ai_detectability: float
    overall_score: float
    needs_review: bool
    flags: list[str]


class ImageQualityScorer:
    """Score generated images for quality.

    Evaluates AI-generated images on multiple dimensions
    to determine suitability for publication.

    Scoring weights:
    - Aesthetic appeal: 30%
    - Brand alignment: 40%
    - AI detectability: 30%
    """

    WEIGHTS = {
        "aesthetic": 0.30,
        "brand": 0.40,
        "ai_detect": 0.30,
    }

    REVIEW_THRESHOLD = 6.0

    def __init__(self) -> None:
        """Initialize the quality scorer."""
        logger.debug("ImageQualityScorer initialized")

    def score(
        self,
        image: GeneratedImage,
        prompt_compliance: float = 0.8,
        generation_success: bool = True,
    ) -> QualityAssessment:
        """Calculate quality scores for a generated image.

        Args:
            image: The generated image to evaluate
            prompt_compliance: How well image matches prompt (0-1)
            generation_success: Whether generation completed successfully

        Returns:
            QualityAssessment with all scores and flags
        """
        flags: list[str] = []

        # Calculate individual scores
        aesthetic = self._score_aesthetic(image, generation_success, flags)
        brand = self._score_brand_alignment(image, prompt_compliance, flags)
        ai_detect = self._score_ai_detectability(image, flags)

        # Calculate weighted overall score
        overall = (
            aesthetic * self.WEIGHTS["aesthetic"]
            + brand * self.WEIGHTS["brand"]
            + ai_detect * self.WEIGHTS["ai_detect"]
        )

        # Clamp to valid range
        overall = max(1.0, min(10.0, overall))

        needs_review = overall < self.REVIEW_THRESHOLD

        if needs_review:
            logger.warning(
                "Image %s scored %.1f, flagged for review: %s",
                image.id,
                overall,
                ", ".join(flags) if flags else "low overall score",
            )

        return QualityAssessment(
            aesthetic_score=min(10.0, aesthetic),
            brand_alignment=min(10.0, brand),
            ai_detectability=min(10.0, ai_detect),
            overall_score=overall,
            needs_review=needs_review,
            flags=flags,
        )

    def _score_aesthetic(
        self,
        image: GeneratedImage,
        generation_success: bool,
        flags: list[str],
    ) -> float:
        """Score aesthetic appeal of the image.

        Factors:
        - Generation success: Base score
        - Resolution: Bonus for high resolution
        - Aspect ratio validity: Penalty for unusual ratios

        Args:
            image: The generated image
            generation_success: Whether generation succeeded
            flags: List to append quality issues to

        Returns:
            Aesthetic score (1-10)
        """
        # Base score from generation success
        score = 8.0 if generation_success else 3.0

        if not generation_success:
            flags.append("generation_failed")
            return score

        # Resolution bonus
        if image.width >= 1080 and image.height >= 1080:
            score += 1.0
        elif image.width < 800 or image.height < 800:
            score -= 1.5
            flags.append("low_resolution")

        # Aspect ratio check
        ratio = image.width / image.height if image.height > 0 else 1
        if ratio < 0.5 or ratio > 2.0:
            score -= 0.5
            flags.append("unusual_aspect_ratio")

        return max(1.0, score)

    def _score_brand_alignment(
        self,
        image: GeneratedImage,
        prompt_compliance: float,
        flags: list[str],
    ) -> float:
        """Score brand alignment of the image.

        Factors:
        - Style used: Bonus for NORDIC style
        - Prompt compliance: How well image matches prompt

        Args:
            image: The generated image
            prompt_compliance: Prompt compliance score (0-1)
            flags: List to append quality issues to

        Returns:
            Brand alignment score (1-10)
        """
        # Base score from style
        if image.style == ImageStyle.NORDIC:
            score = 8.0
        elif image.style == ImageStyle.NATURAL:
            score = 7.5
        elif image.style == ImageStyle.LIFESTYLE:
            score = 7.0
        else:
            score = 6.0

        # Add prompt compliance bonus (up to +2)
        score += prompt_compliance * 2.0

        if prompt_compliance < 0.5:
            flags.append("poor_prompt_compliance")

        if image.style not in [ImageStyle.NORDIC, ImageStyle.NATURAL]:
            if score < 7.0:
                flags.append("poor_brand_alignment")

        return max(1.0, score)

    def _score_ai_detectability(
        self,
        image: GeneratedImage,
        flags: list[str],
    ) -> float:
        """Score AI detectability risk (higher = less detectable = better).

        Factors:
        - Style used: NORDIC aims for natural look
        - Prompt emphasis: Natural aesthetic prompts score higher

        Args:
            image: The generated image
            flags: List to append quality issues to

        Returns:
            AI detectability score (1-10, higher is better)
        """
        # Style-based scoring
        style_scores = {
            ImageStyle.NORDIC: 8.0,  # Minimalist, natural look
            ImageStyle.NATURAL: 7.5,  # Photography style
            ImageStyle.LIFESTYLE: 7.0,  # Realistic lifestyle
            ImageStyle.PRODUCT: 6.0,  # Clean but can look staged
            ImageStyle.ABSTRACT: 5.0,  # More obviously AI
        }

        score = style_scores.get(image.style, 6.0)

        # Check if prompt includes natural aesthetic keywords
        prompt_lower = image.prompt.lower()
        natural_keywords = ["organic", "authentic", "natural", "photography"]
        keyword_matches = sum(1 for kw in natural_keywords if kw in prompt_lower)
        score += keyword_matches * 0.3

        if score < 5.0:
            flags.append("high_ai_detectability")

        return max(1.0, min(10.0, score))

    def get_recommendation(self, assessment: QualityAssessment) -> str:
        """Get human-readable recommendation based on assessment.

        Args:
            assessment: Quality assessment result

        Returns:
            Recommendation string
        """
        if assessment.overall_score >= 9.0:
            return "Excellent - Ready for auto-publish"
        elif assessment.overall_score >= 7.0:
            return "Good - Suitable for publication"
        elif assessment.overall_score >= 6.0:
            return "Acceptable - May need minor review"
        elif assessment.overall_score >= 4.0:
            return "Needs review - Multiple issues detected"
        else:
            return "Poor quality - Consider regenerating"
