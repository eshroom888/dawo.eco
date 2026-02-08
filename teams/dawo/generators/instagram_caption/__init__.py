"""Instagram Caption Generator - Norwegian caption generation for DAWO.

This module provides Instagram caption generation following DAWO brand voice.
Generates warm, educational, Nordic-simple captions in Norwegian.

Exports:
    CaptionGenerator: Main caption generator agent class
    CaptionGeneratorProtocol: Protocol for generator interface (testability)
    LLMClientProtocol: Protocol for LLM client interface
    CaptionRequest: Input dataclass for caption generation
    CaptionResult: Output dataclass with caption and validation status
    count_words: Utility to count words excluding hashtags
    validate_word_count: Validate caption meets 180-220 word requirement
    generate_hashtags: Generate hashtags with brand tags
    validate_hashtags: Validate hashtag list meets requirements
    format_research_citation: Format research source for caption
    extract_hashtags_from_text: Extract hashtags from caption text
    remove_hashtags_from_text: Remove hashtags from caption text
    MIN_WORDS: Minimum word count (180)
    MAX_WORDS: Maximum word count (220)
    MAX_HASHTAGS: Maximum hashtags (15)
    BRAND_TAGS: Required brand hashtags
"""

from .agent import (
    CaptionGenerator,
    CaptionGeneratorProtocol,
    LLMClientProtocol,
)
from .schemas import (
    CaptionRequest,
    CaptionResult,
)
from .tools import (
    count_words,
    validate_word_count,
    generate_hashtags,
    validate_hashtags,
    format_research_citation,
    extract_hashtags_from_text,
    remove_hashtags_from_text,
    MIN_WORDS,
    MAX_WORDS,
    MAX_HASHTAGS,
    BRAND_TAGS,
)

__all__: list[str] = [
    # Core agent
    "CaptionGenerator",
    # Protocols
    "CaptionGeneratorProtocol",
    "LLMClientProtocol",
    # Data classes
    "CaptionRequest",
    "CaptionResult",
    # Utilities
    "count_words",
    "validate_word_count",
    "generate_hashtags",
    "validate_hashtags",
    "format_research_citation",
    "extract_hashtags_from_text",
    "remove_hashtags_from_text",
    # Constants
    "MIN_WORDS",
    "MAX_WORDS",
    "MAX_HASHTAGS",
    "BRAND_TAGS",
]
