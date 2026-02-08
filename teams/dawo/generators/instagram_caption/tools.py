"""Caption generation tools and utilities.

Provides helper functions for caption validation, word counting,
and hashtag generation for Norwegian Instagram captions.
"""

import re
from typing import Optional


# Constants from brand profile
MIN_WORDS = 180
MAX_WORDS = 220
MAX_HASHTAGS = 15
BRAND_TAGS = ["#DAWO", "#DAWOmushrooms", "#nordisksopp"]

# Topic hashtag pools (Norwegian)
TOPIC_HASHTAGS = {
    "wellness": ["#naturligvelvære", "#hverdagsmagi", "#nordiskliv"],
    "mushrooms": ["#løvemanke", "#chaga", "#sopp", "#funksjonellesopp"],
    "lifestyle": ["#enklehverdag", "#slowliving", "#nordiskdesign"],
}


def count_words(text: str) -> int:
    """Count words in text, excluding hashtags.

    Args:
        text: Caption text to count

    Returns:
        Number of words (not including hashtags)
    """
    if not text:
        return 0

    # Remove hashtags before counting
    text_without_hashtags = re.sub(r"#\w+", "", text)
    # Split on whitespace and filter empty strings
    words = [w for w in text_without_hashtags.split() if w.strip()]
    return len(words)


def validate_word_count(text: str) -> tuple[bool, str]:
    """Validate caption meets word count requirements (180-220 words).

    Args:
        text: Caption text to validate

    Returns:
        Tuple of (is_valid, message)
    """
    word_count = count_words(text)

    if word_count < MIN_WORDS:
        return False, f"Caption too short: {word_count} words (minimum: {MIN_WORDS})"
    if word_count > MAX_WORDS:
        return False, f"Caption too long: {word_count} words (maximum: {MAX_WORDS})"

    return True, f"Word count valid: {word_count} words"


def generate_hashtags(
    topic: str,
    research_tags: Optional[list[str]] = None,
    max_total: int = MAX_HASHTAGS,
) -> list[str]:
    """Generate hashtags for caption including brand tags.

    Always includes brand tags, then adds topic-relevant tags.

    Args:
        topic: Primary topic (wellness, mushrooms, lifestyle)
        research_tags: Additional tags from research item
        max_total: Maximum total hashtags (default: 15)

    Returns:
        List of hashtags including brand tags
    """
    hashtags = list(BRAND_TAGS)  # Always include brand tags

    # Add topic pool hashtags
    topic_pool = TOPIC_HASHTAGS.get(topic, [])
    for tag in topic_pool:
        if len(hashtags) < max_total and tag not in hashtags:
            hashtags.append(tag)

    # Convert research tags to hashtags
    if research_tags:
        for tag in research_tags:
            if len(hashtags) >= max_total:
                break
            # Format as hashtag
            hashtag = f"#{tag.lower().replace(' ', '').replace('_', '')}"
            if hashtag not in hashtags:
                hashtags.append(hashtag)

    return hashtags[:max_total]


def validate_hashtags(hashtags: list[str]) -> tuple[bool, str]:
    """Validate hashtag list meets requirements.

    Args:
        hashtags: List of hashtags to validate

    Returns:
        Tuple of (is_valid, message)
    """
    if len(hashtags) > MAX_HASHTAGS:
        return False, f"Too many hashtags: {len(hashtags)} (maximum: {MAX_HASHTAGS})"

    # Check brand tags are included
    missing_brand_tags = [tag for tag in BRAND_TAGS if tag not in hashtags]
    if missing_brand_tags:
        return False, f"Missing required brand tags: {', '.join(missing_brand_tags)}"

    return True, f"Hashtags valid: {len(hashtags)} tags"


def format_research_citation(
    source_type: str,
    research_content: str,
) -> str:
    """Format research source appropriately for caption.

    Different sources get different citation styles:
    - pubmed: "Forskning viser..." with academic tone
    - reddit/instagram: "Mange opplever..." for social trends
    - news: Reference to news/industry
    - youtube: Reference to content creator insights

    Args:
        source_type: Research source (pubmed, reddit, youtube, news, instagram)
        research_content: Summary of research findings

    Returns:
        Norwegian citation phrase for the caption
    """
    citation_formats = {
        "pubmed": "Forskning viser at",
        "reddit": "Mange i fellesskapet deler at",
        "instagram": "Trenden viser at",
        "youtube": "Eksperter forteller at",
        "news": "Nylige rapporter viser at",
    }

    base_citation = citation_formats.get(source_type, "Vi har lært at")
    return base_citation


def extract_hashtags_from_text(text: str) -> list[str]:
    """Extract hashtags from caption text.

    Args:
        text: Caption text containing hashtags

    Returns:
        List of hashtags found in text
    """
    return re.findall(r"#\w+", text)


def remove_hashtags_from_text(text: str) -> str:
    """Remove hashtags from caption text.

    Args:
        text: Caption text containing hashtags

    Returns:
        Text with hashtags removed
    """
    return re.sub(r"#\w+\s*", "", text).strip()
