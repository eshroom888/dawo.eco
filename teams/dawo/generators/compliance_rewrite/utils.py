"""Utility functions for Compliance Rewrite Suggester.

Content reconstruction utilities for applying suggestions to content.
Handles position-based replacement and preserves content structure.
"""

from typing import Optional
import re

from .schemas import RewriteSuggestion


def apply_suggestion(
    content: str,
    suggestion: RewriteSuggestion,
    selected_index: int = 0
) -> str:
    """Apply a single suggestion to content.

    Uses position-based replacement when available for accuracy.
    Falls back to string replacement if positions are not set.

    Args:
        content: Original content text
        suggestion: The RewriteSuggestion with alternatives
        selected_index: Which suggestion to apply (0, 1, or 2)

    Returns:
        Content with phrase replaced

    Raises:
        ValueError: If selected_index is out of range
        ValueError: If suggestion has no alternatives and no keep recommendation
    """
    # Handle "keep as-is" case
    if suggestion.keep_recommendation and not suggestion.suggestions:
        return content

    if not suggestion.suggestions:
        raise ValueError("Suggestion has no alternatives to apply")

    if selected_index >= len(suggestion.suggestions):
        raise ValueError(
            f"Invalid suggestion index {selected_index}, "
            f"only {len(suggestion.suggestions)} alternatives available"
        )

    replacement = suggestion.suggestions[selected_index]

    # Use position-based replacement for accuracy
    if suggestion.start_position >= 0 and suggestion.end_position > suggestion.start_position:
        return (
            content[:suggestion.start_position]
            + replacement
            + content[suggestion.end_position:]
        )

    # Fallback to string replacement (first occurrence only)
    return content.replace(suggestion.original_phrase, replacement, 1)


def apply_all_suggestions(
    content: str,
    suggestions: list[RewriteSuggestion],
    selections: Optional[dict[int, int]] = None
) -> str:
    """Apply multiple suggestions to content.

    Applies in reverse position order to maintain accurate offsets.
    Uses first alternative (index 0) by default if no selections provided.

    Args:
        content: Original content
        suggestions: List of RewriteSuggestion objects
        selections: Map of suggestion index to selected alternative index.
                   Defaults to selecting first alternative for each.

    Returns:
        Fully rewritten content
    """
    if not suggestions:
        return content

    if selections is None:
        selections = {}

    # Filter out suggestions with keep recommendations and no alternatives
    applicable = [
        (idx, s) for idx, s in enumerate(suggestions)
        if s.suggestions or not s.keep_recommendation
    ]

    # Sort by position descending to maintain offsets during replacement
    # Use -1 as sentinel for "no position set" - these go last after reversing
    sorted_suggestions = sorted(
        applicable,
        key=lambda x: x[1].start_position if x[1].start_position >= 0 else -1,
        reverse=True
    )

    result = content
    for idx, suggestion in sorted_suggestions:
        if not suggestion.suggestions:
            continue

        selected = selections.get(idx, 0)  # Default to first suggestion
        try:
            result = apply_suggestion(result, suggestion, selected)
        except ValueError:
            # Skip invalid selections, use first alternative
            if suggestion.suggestions:
                result = apply_suggestion(result, suggestion, 0)

    return result


def find_phrase_position(content: str, phrase: str) -> tuple[int, int]:
    """Find the position of a phrase in content.

    Performs case-insensitive search with word boundary matching.

    Args:
        content: Content to search in
        phrase: Phrase to find

    Returns:
        Tuple of (start_position, end_position), or (0, 0) if not found
    """
    # Try exact match first
    pos = content.find(phrase)
    if pos >= 0:
        return pos, pos + len(phrase)

    # Try case-insensitive match
    content_lower = content.lower()
    phrase_lower = phrase.lower()
    pos = content_lower.find(phrase_lower)
    if pos >= 0:
        return pos, pos + len(phrase)

    # Try word boundary regex match
    try:
        pattern = r'\b' + re.escape(phrase_lower) + r'\b'
        match = re.search(pattern, content_lower)
        if match:
            return match.start(), match.end()
    except re.error:
        pass

    return 0, 0


def extract_context(content: str, start: int, end: int, window: int = 50) -> str:
    """Extract context around a position in content.

    Args:
        content: Full content text
        start: Start position of the phrase
        end: End position of the phrase
        window: Characters to include before and after

    Returns:
        Context string with the phrase and surrounding text
    """
    context_start = max(0, start - window)
    context_end = min(len(content), end + window)

    prefix = "..." if context_start > 0 else ""
    suffix = "..." if context_end < len(content) else ""

    return prefix + content[context_start:context_end] + suffix


def preserve_formatting(original: str, replacement: str) -> str:
    """Preserve original formatting in replacement.

    Matches capitalization and surrounding whitespace.

    Args:
        original: Original phrase with formatting
        replacement: Replacement text to format

    Returns:
        Replacement with matching formatting
    """
    if not original or not replacement:
        return replacement

    # Match leading/trailing whitespace
    leading_space = len(original) - len(original.lstrip())
    trailing_space = len(original) - len(original.rstrip())

    # Match capitalization
    result = replacement.strip()

    if original.strip().isupper():
        result = result.upper()
    elif original.strip().istitle():
        result = result.title()
    elif original.strip()[0].isupper() if original.strip() else False:
        result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()

    # Restore whitespace
    if leading_space:
        result = original[:leading_space] + result
    if trailing_space:
        result = result + original[-trailing_space:]

    return result


def count_words(text: str) -> int:
    """Count words in text, excluding hashtags.

    Args:
        text: Text to count words in

    Returns:
        Number of words (excluding hashtags)
    """
    # Remove hashtags
    text_no_tags = re.sub(r'#\w+', '', text)
    # Split on whitespace and count non-empty
    words = [w for w in text_no_tags.split() if w.strip()]
    return len(words)


def validate_rewrite_length(original: str, rewritten: str, tolerance: float = 0.2) -> bool:
    """Validate rewritten content length is similar to original.

    Args:
        original: Original content
        rewritten: Rewritten content
        tolerance: Allowed deviation (0.2 = 20%)

    Returns:
        True if length is within tolerance
    """
    original_words = count_words(original)
    rewritten_words = count_words(rewritten)

    if original_words == 0:
        return True

    deviation = abs(rewritten_words - original_words) / original_words
    return deviation <= tolerance
