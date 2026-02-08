"""Platform Optimization Scorer - Platform-specific optimization scoring.

Scores content for platform optimization including hashtags,
caption length, format fit, brand hashtags, and CTA presence.
"""

from dataclasses import dataclass
from typing import Optional

from teams.dawo.generators.content_quality.schemas import (
    ComponentScore,
    ContentType,
    PlatformOptimizationResult,
)


@dataclass
class PlatformScorerConfig:
    """Configuration for platform optimization scoring.

    Attributes:
        weight: Weight of platform optimization in total score (default 0.15)
        required_hashtags: Brand hashtags that should be present
    """

    weight: float = 0.15
    required_hashtags: list[str] = None

    def __post_init__(self):
        if self.required_hashtags is None:
            self.required_hashtags = ["DAWO", "DAWOmushrooms"]


# Platform rules per content type
PLATFORM_RULES = {
    ContentType.INSTAGRAM_FEED: {
        "hashtag_min": 5,
        "hashtag_max": 15,
        "hashtag_optimal": 11,
        "caption_words_min": 150,
        "caption_words_max": 250,
        "caption_words_target": 200,
    },
    ContentType.INSTAGRAM_STORY: {
        "hashtag_min": 0,
        "hashtag_max": 5,
        "hashtag_optimal": 3,
        "caption_words_min": 0,
        "caption_words_max": 50,
        "caption_words_target": 25,
    },
    ContentType.INSTAGRAM_REEL: {
        "hashtag_min": 3,
        "hashtag_max": 10,
        "hashtag_optimal": 7,
        "caption_words_min": 50,
        "caption_words_max": 150,
        "caption_words_target": 100,
    },
}

# CTA phrases to detect
CTA_PHRASES = [
    "link i bio",
    "link in bio",
    "sjekk ut",
    "check out",
    "prøv",
    "try",
]


class PlatformOptimizationScorer:
    """Scores platform-specific optimization.

    Checks hashtag count, caption length, format fit,
    brand hashtags, and CTA presence.

    Attributes:
        config: Scorer configuration
    """

    def __init__(
        self,
        config: Optional[PlatformScorerConfig] = None,
    ) -> None:
        """Initialize with optional configuration.

        Args:
            config: Optional scorer configuration
        """
        self._config = config or PlatformScorerConfig()

    def score(
        self,
        content: str,
        content_type: ContentType,
        hashtags: list[str],
    ) -> ComponentScore:
        """Score platform optimization.

        Args:
            content: Content text
            content_type: Type of content (feed, story, reel)
            hashtags: List of hashtags in content

        Returns:
            ComponentScore with platform optimization details
        """
        rules = PLATFORM_RULES.get(content_type, PLATFORM_RULES[ContentType.INSTAGRAM_FEED])
        suggestions: list[str] = []

        # Score hashtags
        hashtag_score = self._score_hashtags(hashtags, rules, suggestions)

        # Score caption length
        length_score = self._score_length(content, rules, suggestions)

        # Check brand hashtags
        brand_hashtags_present = self._check_brand_hashtags(hashtags, suggestions)

        # Check CTA presence
        has_cta = self._check_cta(content, content_type, suggestions)

        # Format score (all types get 10 if proper format)
        format_score = 10.0

        # Calculate overall score
        optimization_score = (
            hashtag_score * 0.3 +
            length_score * 0.3 +
            format_score * 0.2 +
            (10.0 if brand_hashtags_present else 5.0) * 0.1 +
            (10.0 if has_cta else 6.0) * 0.1
        )

        result = PlatformOptimizationResult(
            optimization_score=round(optimization_score, 1),
            hashtag_score=round(hashtag_score, 1),
            length_score=round(length_score, 1),
            format_score=format_score,
            brand_hashtags_present=brand_hashtags_present,
            has_cta=has_cta,
            suggestions=suggestions,
        )

        return ComponentScore(
            component="platform",
            raw_score=optimization_score,
            weight=self._config.weight,
            weighted_score=optimization_score * self._config.weight,
            details={
                "result": result,
                "suggestions": suggestions,
            },
        )

    def _score_hashtags(
        self,
        hashtags: list[str],
        rules: dict,
        suggestions: list[str],
    ) -> float:
        """Score hashtag count and relevance."""
        hashtag_count = len(hashtags)

        if hashtag_count < rules["hashtag_min"]:
            score = max(0, 10 - (rules["hashtag_min"] - hashtag_count) * 2)
            suggestions.append(f"Add more hashtags (minimum {rules['hashtag_min']})")
        elif hashtag_count > rules["hashtag_max"]:
            score = max(0, 10 - (hashtag_count - rules["hashtag_max"]) * 1)
            suggestions.append(f"Reduce hashtags (maximum {rules['hashtag_max']})")
        else:
            # Closer to optimal = higher score
            distance = abs(hashtag_count - rules["hashtag_optimal"])
            score = 10.0 - min(distance * 0.5, 3.0)

        return score

    def _score_length(
        self,
        content: str,
        rules: dict,
        suggestions: list[str],
    ) -> float:
        """Score caption length."""
        word_count = len(content.split())

        if word_count < rules["caption_words_min"]:
            score = max(0, 10 - (rules["caption_words_min"] - word_count) / 10)
            suggestions.append(f"Caption too short (target {rules['caption_words_target']} words)")
        elif word_count > rules["caption_words_max"]:
            score = max(0, 10 - (word_count - rules["caption_words_max"]) / 10)
            suggestions.append(f"Caption too long (maximum {rules['caption_words_max']} words)")
        else:
            distance = abs(word_count - rules["caption_words_target"])
            score = 10.0 - min(distance / 25, 3.0)

        return score

    def _check_brand_hashtags(
        self,
        hashtags: list[str],
        suggestions: list[str],
    ) -> bool:
        """Check for required brand hashtags."""
        hashtags_lower = [h.lower() for h in hashtags]
        brand_present = any(
            req.lower() in hashtags_lower
            for req in self._config.required_hashtags
        )

        if not brand_present:
            suggestions.append("Add brand hashtags (#DAWO, #DAWOmushrooms)")

        return brand_present

    def _check_cta(
        self,
        content: str,
        content_type: ContentType,
        suggestions: list[str],
    ) -> bool:
        """Check for call-to-action presence."""
        content_lower = content.lower()
        has_cta = any(phrase in content_lower for phrase in CTA_PHRASES)

        if not has_cta and content_type == ContentType.INSTAGRAM_FEED:
            suggestions.append("Add a call-to-action")

        return has_cta
