"""Template handling for Orshot Graphics Generator.

Provides dimension constants, template selection logic,
and template validation utilities.
"""

import logging
from enum import Enum
from typing import NamedTuple, Optional

from integrations.orshot import OrshotTemplate
from .schemas import ContentType

logger = logging.getLogger(__name__)


class Dimensions(NamedTuple):
    """Image dimensions as width and height."""

    width: int
    height: int


class InstagramFormat(Enum):
    """Instagram content formats with required dimensions.

    Per Instagram design guidelines:
    - Feed posts: 1080x1080 (square) or 1080x1350 (portrait)
    - Stories and Reels: 1080x1920 (9:16 vertical)
    """

    FEED_POST = Dimensions(1080, 1080)      # Square post
    FEED_PORTRAIT = Dimensions(1080, 1350)  # 4:5 portrait
    STORY = Dimensions(1080, 1920)          # 9:16 vertical
    REEL_COVER = Dimensions(1080, 1920)     # 9:16 vertical


# Mapping from ContentType to preferred InstagramFormat
CONTENT_TYPE_FORMATS: dict[ContentType, InstagramFormat] = {
    ContentType.INSTAGRAM_FEED: InstagramFormat.FEED_POST,
    ContentType.INSTAGRAM_STORY: InstagramFormat.STORY,
    ContentType.INSTAGRAM_REEL: InstagramFormat.REEL_COVER,
}


def get_target_dimensions(content_type: ContentType) -> Dimensions:
    """Get target dimensions for a content type.

    Args:
        content_type: The content type to get dimensions for

    Returns:
        Dimensions tuple (width, height)
    """
    format_enum = CONTENT_TYPE_FORMATS.get(content_type, InstagramFormat.FEED_POST)
    return format_enum.value


def validate_template_dimensions(
    template: OrshotTemplate,
    content_type: ContentType,
) -> tuple[bool, str]:
    """Check if template dimensions match target format.

    Args:
        template: Template to validate
        content_type: Target content type

    Returns:
        Tuple of (is_valid, message)
    """
    target = get_target_dimensions(content_type)
    actual = Dimensions(*template.dimensions)

    if actual == target:
        return True, f"Dimensions match: {actual.width}x{actual.height}"

    # Log warning but allow proceeding (per story requirements)
    msg = (
        f"Dimension mismatch: template is {actual.width}x{actual.height}, "
        f"target is {target.width}x{target.height}"
    )
    logger.warning(msg)
    return False, msg


def select_template_for_content(
    templates: list[OrshotTemplate],
    content_type: ContentType,
) -> Optional[OrshotTemplate]:
    """Select the best template for a content type.

    Selection priority:
    1. Exact dimension match
    2. Similar aspect ratio
    3. First available template

    Args:
        templates: Available templates
        content_type: Target content type

    Returns:
        Best matching template, or None if no templates available
    """
    if not templates:
        logger.warning("No templates available for selection")
        return None

    target = get_target_dimensions(content_type)

    # Priority 1: Exact dimension match
    for template in templates:
        if template.dimensions == (target.width, target.height):
            logger.debug("Selected exact match: %s", template.name)
            return template

    # Priority 2: Similar aspect ratio (within 5%)
    target_ratio = target.width / target.height
    for template in templates:
        template_ratio = template.dimensions[0] / template.dimensions[1]
        if abs(template_ratio - target_ratio) < 0.05:
            logger.debug("Selected aspect ratio match: %s", template.name)
            return template

    # Priority 3: First available
    logger.warning(
        "No dimension or aspect ratio match found, using first template: %s",
        templates[0].name,
    )
    return templates[0]


def is_template_for_content_type(
    template: OrshotTemplate,
    content_type: ContentType,
) -> bool:
    """Check if a template is designed for a specific content type.

    Used for quality scoring - templates designed for the target
    format will produce better quality output.

    Args:
        template: Template to check
        content_type: Target content type

    Returns:
        True if template matches content type requirements
    """
    target = get_target_dimensions(content_type)
    return template.dimensions == (target.width, target.height)
