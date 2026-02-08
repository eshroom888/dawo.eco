"""Compliance Rewrite Suggester - EU-compliant content rewrites.

This module provides rewrite suggestions for non-compliant content,
transforming prohibited or borderline phrases into EU-compliant
alternatives while maintaining DAWO brand voice.

Uses the 'generate' tier (defaults to Sonnet) for quality rewrites.

Exports:
    ComplianceRewriteSuggester: Main rewrite suggester agent class
    ComplianceRewriteSuggesterProtocol: Protocol for dependency injection
    RewriteRequest: Input dataclass for rewrite generation
    RewriteResult: Output dataclass with suggestions and rewritten content
    RewriteSuggestion: Individual phrase suggestion dataclass
    apply_suggestion: Apply a single suggestion to content
    apply_all_suggestions: Apply multiple suggestions to content
    find_phrase_position: Find phrase position in content
    extract_context: Extract context around a phrase
    preserve_formatting: Preserve formatting in replacements
    count_words: Count words excluding hashtags
    validate_rewrite_length: Validate rewritten content length
    get_system_prompt: Get language-specific system prompt
    get_prompt_template: Get language-specific prompt template
    get_keep_instruction: Get keep instruction for borderline phrases
    REWRITE_SYSTEM_PROMPT_NO: Norwegian system prompt
    REWRITE_SYSTEM_PROMPT_EN: English system prompt
    MAX_REVALIDATION_ITERATIONS: Maximum revalidation loop iterations
    CONTEXT_WINDOW_CHARS: Characters to include for context
    GENERATION_TIMEOUT_MS: Generation timeout in milliseconds
"""

from .agent import (
    ComplianceRewriteSuggester,
    ComplianceRewriteSuggesterProtocol,
    MAX_REVALIDATION_ITERATIONS,
    CONTEXT_WINDOW_CHARS,
    GENERATION_TIMEOUT_MS,
)
from .schemas import (
    RewriteRequest,
    RewriteResult,
    RewriteSuggestion,
)
from .utils import (
    apply_suggestion,
    apply_all_suggestions,
    find_phrase_position,
    extract_context,
    preserve_formatting,
    count_words,
    validate_rewrite_length,
)
from .prompts import (
    get_system_prompt,
    get_prompt_template,
    get_keep_instruction,
    REWRITE_SYSTEM_PROMPT_NO,
    REWRITE_SYSTEM_PROMPT_EN,
)

__all__: list[str] = [
    # Core agent
    "ComplianceRewriteSuggester",
    # Protocols
    "ComplianceRewriteSuggesterProtocol",
    # Data classes
    "RewriteRequest",
    "RewriteResult",
    "RewriteSuggestion",
    # Utilities
    "apply_suggestion",
    "apply_all_suggestions",
    "find_phrase_position",
    "extract_context",
    "preserve_formatting",
    "count_words",
    "validate_rewrite_length",
    # Prompt utilities
    "get_system_prompt",
    "get_prompt_template",
    "get_keep_instruction",
    # Constants
    "REWRITE_SYSTEM_PROMPT_NO",
    "REWRITE_SYSTEM_PROMPT_EN",
    "MAX_REVALIDATION_ITERATIONS",
    "CONTEXT_WINDOW_CHARS",
    "GENERATION_TIMEOUT_MS",
]
