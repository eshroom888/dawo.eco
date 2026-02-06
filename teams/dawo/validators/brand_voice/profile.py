"""Brand Profile Configuration Manager.

Handles brand profile loading and validation.
Note: Profile is ALWAYS injected via constructor - this module
provides utilities for profile validation and schema definitions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TonePillar:
    """Configuration for a single tone pillar."""
    description: str
    positive_markers: list[str]
    negative_markers: list[str]


@dataclass
class BrandProfile:
    """Structured brand profile configuration.

    This is a typed representation of the brand profile dictionary.
    Can be used to validate profile structure.
    """
    brand_name: str
    version: str
    tone_pillars: dict[str, TonePillar]
    forbidden_terms: dict[str, list[str]]
    ai_generic_patterns: list[str]
    style_examples: dict[str, list[str]]
    scoring_thresholds: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict) -> "BrandProfile":
        """Create BrandProfile from dictionary.

        Args:
            data: Raw profile dictionary (from config file)

        Returns:
            BrandProfile instance

        Raises:
            ValueError: If required keys are missing
        """
        required_keys = ["brand_name", "tone_pillars", "forbidden_terms"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required configuration key: {key}")

        # Parse tone pillars
        tone_pillars = {}
        for name, config in data.get("tone_pillars", {}).items():
            tone_pillars[name] = TonePillar(
                description=config.get("description", ""),
                positive_markers=config.get("positive_markers", []),
                negative_markers=config.get("negative_markers", [])
            )

        return cls(
            brand_name=data.get("brand_name", ""),
            version=data.get("version", "1.0"),
            tone_pillars=tone_pillars,
            forbidden_terms=data.get("forbidden_terms", {}),
            ai_generic_patterns=data.get("ai_generic_patterns", []),
            style_examples=data.get("style_examples", {"good": [], "bad": []}),
            scoring_thresholds=data.get("scoring_thresholds", {
                "pass": 0.8,
                "needs_revision": 0.5,
                "fail": 0.0
            })
        )


def validate_profile(profile: dict) -> tuple[bool, Optional[str]]:
    """Validate brand profile dictionary structure.

    Args:
        profile: Brand profile dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_keys = [
        "brand_name",
        "tone_pillars",
        "forbidden_terms"
    ]

    for key in required_keys:
        if key not in profile:
            return False, f"Missing required key: {key}"

    # Validate tone_pillars structure
    tone_pillars = profile.get("tone_pillars", {})
    for pillar_name, pillar_config in tone_pillars.items():
        if not isinstance(pillar_config, dict):
            return False, f"Invalid tone pillar config for '{pillar_name}'"

    # Validate forbidden_terms structure
    forbidden_terms = profile.get("forbidden_terms", {})
    if not isinstance(forbidden_terms, dict):
        return False, "forbidden_terms must be a dictionary"

    for category, terms in forbidden_terms.items():
        if not isinstance(terms, list):
            return False, f"forbidden_terms['{category}'] must be a list"

    # Validate ai_generic_patterns if present
    ai_patterns = profile.get("ai_generic_patterns", [])
    if not isinstance(ai_patterns, list):
        return False, "ai_generic_patterns must be a list"

    return True, None


# Default DAWO brand profile schema reference
DAWO_PROFILE_SCHEMA = {
    "brand_name": "string - Brand name (e.g., 'DAWO')",
    "version": "string - Profile version (e.g., '2026-02')",
    "tone_pillars": {
        "warm": {
            "description": "string - Pillar description",
            "positive_markers": ["list", "of", "positive", "words"],
            "negative_markers": ["list", "of", "negative", "words"]
        },
        "educational": "Same structure as warm",
        "nordic_simplicity": "Same structure as warm"
    },
    "forbidden_terms": {
        "medicinal": ["list", "of", "forbidden", "medical", "terms"],
        "sales_pressure": ["list", "of", "sales", "terms"],
        "superlatives": ["list", "of", "superlative", "terms"]
    },
    "ai_generic_patterns": [
        "Regex patterns or literal strings to detect AI writing"
    ],
    "style_examples": {
        "good": ["List of good DAWO content examples"],
        "bad": ["List of bad content examples to avoid"]
    },
    "scoring_thresholds": {
        "pass": 0.8,
        "needs_revision": 0.5,
        "fail": 0.0
    }
}
