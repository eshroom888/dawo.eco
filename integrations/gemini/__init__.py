"""Gemini integration module (Nano Banana).

Provides AI image generation using Google Gemini.
"""

from integrations.gemini.client import (
    GeminiImageClient,
    GeminiImageClientProtocol,
    GeneratedImage,
    ImageStyle,
)
from integrations.gemini.metadata import (
    MetadataError,
    strip_ai_metadata,
    validate_no_ai_markers,
    get_image_metadata,
)

__all__ = [
    # Client
    "GeminiImageClient",
    "GeminiImageClientProtocol",
    "GeneratedImage",
    "ImageStyle",
    # Metadata utilities
    "MetadataError",
    "strip_ai_metadata",
    "validate_no_ai_markers",
    "get_image_metadata",
]
