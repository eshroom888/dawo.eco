"""Health Claim Extraction configuration.

Epic 6, Story 6-6: Health Claim Extraction Engine.

Frozen dataclasses for extraction configuration including bilingual
regex patterns (English + Norwegian) for health claim detection.

Classes:
    ClaimPattern: Individual regex pattern with category and language.
    HealthClaimExtractionConfig: Main extraction configuration.

Functions:
    build_health_claim_extraction_config: Build config from JSON dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClaimPattern:
    """Individual claim detection pattern.

    Attributes:
        pattern: Regex pattern string for matching.
        category: Claim category (treatment, prevention, enhancement, general_wellness).
        language: Pattern language code ("en" or "no").
    """

    pattern: str
    category: str
    language: str


DEFAULT_CLAIM_CATEGORIES = (
    "treatment",
    "prevention",
    "enhancement",
    "general_wellness",
)

DEFAULT_EU_ARTICLE_MAPPING: dict[str, str] = {
    "treatment": "prohibited",
    "prevention": "14.1a",
    "enhancement": "13.1",
    "general_wellness": "13.1",
}


@dataclass(frozen=True)
class HealthClaimExtractionConfig:
    """Configuration for the health claim extraction engine.

    Attributes:
        enabled: Whether extraction is active.
        batch_size: Max content items per run.
        confidence_threshold: Minimum confidence for auto-proceed to violation detection.
        max_claims_per_content: Safety limit per content item.
        context_window_chars: Characters around matched phrase for context.
        use_llm: Whether to use LLM classification (False = regex-only).
        prohibited_patterns: Patterns for prohibited health claims.
        borderline_patterns: Patterns for borderline claims.
        permitted_patterns: Patterns for permitted wellness language.
        claim_categories: Valid claim category names.
        eu_article_mapping: Category to EU article mapping.
    """

    prohibited_patterns: tuple[ClaimPattern, ...] = ()
    borderline_patterns: tuple[ClaimPattern, ...] = ()
    permitted_patterns: tuple[ClaimPattern, ...] = ()
    enabled: bool = True
    batch_size: int = 20
    confidence_threshold: int = 70
    max_claims_per_content: int = 10
    context_window_chars: int = 100
    use_llm: bool = True
    claim_categories: tuple[str, ...] = DEFAULT_CLAIM_CATEGORIES
    eu_article_mapping: dict[str, str] = field(
        default_factory=lambda: dict(DEFAULT_EU_ARTICLE_MAPPING)
    )

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if not self.prohibited_patterns:
            raise ValueError("prohibited_patterns must contain at least 1 pattern")
        if not (0 <= self.confidence_threshold <= 100):
            raise ValueError(
                f"confidence_threshold must be 0-100, got {self.confidence_threshold}"
            )
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")


def build_health_claim_extraction_config(
    data: dict,
) -> HealthClaimExtractionConfig:
    """Build HealthClaimExtractionConfig from a JSON-loaded dict.

    Args:
        data: Dictionary from JSON config file.

    Returns:
        Validated HealthClaimExtractionConfig instance.

    Raises:
        ValueError: If validation fails.
    """
    prohibited = tuple(
        ClaimPattern(
            pattern=p["pattern"],
            category=p["category"],
            language=p["language"],
        )
        for p in data.get("prohibited_patterns", [])
    )
    borderline = tuple(
        ClaimPattern(
            pattern=p["pattern"],
            category=p["category"],
            language=p["language"],
        )
        for p in data.get("borderline_patterns", [])
    )
    permitted = tuple(
        ClaimPattern(
            pattern=p["pattern"],
            category=p["category"],
            language=p["language"],
        )
        for p in data.get("permitted_patterns", [])
    )
    categories = tuple(data.get("claim_categories", DEFAULT_CLAIM_CATEGORIES))
    eu_mapping = data.get("eu_article_mapping", dict(DEFAULT_EU_ARTICLE_MAPPING))

    return HealthClaimExtractionConfig(
        enabled=data.get("enabled", True),
        batch_size=data.get("batch_size", 20),
        confidence_threshold=data.get("confidence_threshold", 70),
        max_claims_per_content=data.get("max_claims_per_content", 10),
        context_window_chars=data.get("context_window_chars", 100),
        use_llm=data.get("use_llm", True),
        prohibited_patterns=prohibited,
        borderline_patterns=borderline,
        permitted_patterns=permitted,
        claim_categories=categories,
        eu_article_mapping=eu_mapping,
    )


__all__ = [
    "ClaimPattern",
    "HealthClaimExtractionConfig",
    "build_health_claim_extraction_config",
]
