"""Prompt engineering for DAWO brand aesthetics.

Provides prompt templates and building utilities for AI image generation
with DAWO brand alignment and Scandinavian aesthetic focus.
"""

from typing import Optional

from .schemas import ImageStyleType


# Style templates with positive and negative prompts
STYLE_TEMPLATES: dict[ImageStyleType, dict[str, str]] = {
    ImageStyleType.WELLNESS: {
        "prefix": (
            "Nordic minimalist wellness photography. "
            "Natural lighting, muted earth tones, clean Scandinavian interior. "
            "Peaceful, serene atmosphere. "
        ),
        "suffix": (
            "Organic textures, authentic feel, cozy hygge aesthetic. "
            "Professional photography, soft focus background."
        ),
        "negative": (
            "mushrooms, fungi close-up, medical, clinical, laboratory, "
            "pills, capsules, hospital, doctor, supplements, medicine"
        ),
    },
    ImageStyleType.NATURE: {
        "prefix": (
            "Norwegian forest landscape photography. "
            "Misty atmosphere, pine trees, natural light, peaceful. "
            "Nordic wilderness, Scandinavian nature. "
        ),
        "suffix": (
            "Pristine environment, clean air feeling, morning dew. "
            "Wide angle, natural composition, no people."
        ),
        "negative": (
            "mushrooms, fungi close-up, bright colors, artificial lighting, "
            "people, urban, buildings, cars, roads"
        ),
    },
    ImageStyleType.LIFESTYLE: {
        "prefix": (
            "Scandinavian lifestyle photography. "
            "Cozy hygge aesthetic, warm natural tones, authentic feel. "
            "Modern Nordic interior, clean design. "
        ),
        "suffix": (
            "Natural materials, wood and wool textures. "
            "Soft window light, lived-in warmth."
        ),
        "negative": (
            "medical, clinical, pills, capsules, obvious product placement, "
            "cluttered, messy, dark, cold feeling"
        ),
    },
    ImageStyleType.ABSTRACT: {
        "prefix": (
            "Abstract artistic interpretation of wellness. "
            "Muted Nordic color palette, flowing organic shapes. "
            "Minimalist composition, calming visual. "
        ),
        "suffix": (
            "Subtle gradients, natural textures abstracted. "
            "Artistic photography, creative interpretation."
        ),
        "negative": (
            "mushrooms, fungi, medical imagery, clinical, "
            "harsh colors, digital artifacts, busy patterns"
        ),
    },
}

# Base negative prompt applied to all styles
BASE_NEGATIVE_PROMPT = (
    "AI generated, artificial, digital art, CGI, blurry, "
    "low quality, watermark, text overlay, logo, "
    "pixelated, distorted, unnatural"
)

# Maximum prompt lengths for Gemini API
MAX_POSITIVE_PROMPT_LENGTH = 1500
MAX_NEGATIVE_PROMPT_LENGTH = 500


def build_prompt(
    topic: str,
    style: ImageStyleType,
    brand_keywords: Optional[list[str]] = None,
    mood: Optional[str] = None,
) -> str:
    """Build optimized prompt for DAWO brand.

    Args:
        topic: Main topic/theme for the image
        style: Image style preset
        brand_keywords: Additional brand-aligned keywords
        mood: Optional mood/atmosphere descriptor

    Returns:
        Complete prompt string for Gemini API
    """
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES[ImageStyleType.WELLNESS])

    # Build positive prompt
    prompt_parts = [template["prefix"]]

    # Add topic
    prompt_parts.append(f"{topic}. ")

    # Add mood if provided
    if mood:
        prompt_parts.append(f"{mood} atmosphere. ")

    # Add brand keywords
    if brand_keywords:
        prompt_parts.append(", ".join(brand_keywords))
        prompt_parts.append(". ")

    # Add suffix for style consistency
    prompt_parts.append(template["suffix"])

    # Add natural aesthetic emphasis
    prompt_parts.append(" Organic, authentic, human-curated aesthetic.")

    prompt = "".join(prompt_parts)

    # Validate and truncate if needed
    if len(prompt) > MAX_POSITIVE_PROMPT_LENGTH:
        prompt = prompt[:MAX_POSITIVE_PROMPT_LENGTH - 3] + "..."

    return prompt


def get_negative_prompt(
    style: ImageStyleType,
    additional_avoid: Optional[list[str]] = None,
) -> str:
    """Get negative prompt for style with additional avoidance.

    Args:
        style: Image style preset
        additional_avoid: Additional elements to avoid

    Returns:
        Complete negative prompt string
    """
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES[ImageStyleType.WELLNESS])

    # Combine style-specific and base negatives
    negative_parts = [template["negative"], BASE_NEGATIVE_PROMPT]

    # Add additional elements to avoid
    if additional_avoid:
        negative_parts.append(", ".join(additional_avoid))

    negative = ", ".join(negative_parts)

    # Validate and truncate if needed
    if len(negative) > MAX_NEGATIVE_PROMPT_LENGTH:
        negative = negative[:MAX_NEGATIVE_PROMPT_LENGTH - 3] + "..."

    return negative


def get_brand_keywords() -> list[str]:
    """Get default DAWO brand keywords.

    Returns:
        List of brand-aligned keywords for prompt enhancement
    """
    return [
        "peaceful",
        "natural",
        "Norwegian",
        "wellness",
        "clean",
        "pure",
        "Nordic",
        "authentic",
    ]


def validate_prompt_length(prompt: str, negative: str) -> tuple[bool, str]:
    """Validate prompt lengths against API limits.

    Args:
        prompt: Positive prompt
        negative: Negative prompt

    Returns:
        Tuple of (is_valid, message)
    """
    issues = []

    if len(prompt) > MAX_POSITIVE_PROMPT_LENGTH:
        issues.append(
            f"Positive prompt exceeds {MAX_POSITIVE_PROMPT_LENGTH} chars "
            f"(current: {len(prompt)})"
        )

    if len(negative) > MAX_NEGATIVE_PROMPT_LENGTH:
        issues.append(
            f"Negative prompt exceeds {MAX_NEGATIVE_PROMPT_LENGTH} chars "
            f"(current: {len(negative)})"
        )

    if issues:
        return False, "; ".join(issues)

    return True, "Prompts within limits"
