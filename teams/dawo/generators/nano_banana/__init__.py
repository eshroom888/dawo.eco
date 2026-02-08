"""Nano Banana AI Image Generator - AI image generation for DAWO.

This module provides Gemini/Imagen-powered AI image generation
with DAWO brand aesthetics and Scandinavian style.

Exports:
    NanoBananaGenerator: Main AI image generator agent class
    NanoBananaGeneratorProtocol: Protocol for generator interface (testability)
    ImageGenerationRequest: Input dataclass for image generation
    ImageGenerationResult: Output dataclass with image and quality info
    ImageStyleType: Style type enum for generation
    ContentFormat: Content format enum for dimensions
    ImageQualityScorer: Quality scorer for generated images
    QualityAssessment: Quality assessment result dataclass
    build_prompt: Prompt builder with DAWO brand alignment
    get_negative_prompt: Get negative prompt for style
    get_brand_keywords: Get default DAWO brand keywords
    STYLE_MAP: Mapping from ImageStyleType to Gemini ImageStyle
"""

from .agent import (
    NanoBananaGenerator,
    NanoBananaGeneratorProtocol,
    STYLE_MAP,
)
from .schemas import (
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageStyleType,
    ContentFormat,
)
from .quality import (
    ImageQualityScorer,
    QualityAssessment,
)
from .prompts import (
    build_prompt,
    get_negative_prompt,
    get_brand_keywords,
)

__all__: list[str] = [
    # Core agent
    "NanoBananaGenerator",
    # Protocols
    "NanoBananaGeneratorProtocol",
    # Data classes
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "QualityAssessment",
    # Enums
    "ImageStyleType",
    "ContentFormat",
    # Utilities
    "ImageQualityScorer",
    "build_prompt",
    "get_negative_prompt",
    "get_brand_keywords",
    # Constants
    "STYLE_MAP",
]
