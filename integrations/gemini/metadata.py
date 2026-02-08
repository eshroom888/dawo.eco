"""Metadata utilities for AI-generated images.

Provides functions to strip EXIF and AI generation markers from images
to prevent AI detection in published content.

Per AC #3 of Story 3.5:
- Metadata does NOT include AI generation markers
- Style emphasizes natural, human-curated aesthetic
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MetadataError(Exception):
    """Error during metadata operations."""

    pass


def strip_ai_metadata(
    image_path: Path,
    output_path: Optional[Path] = None,
) -> Path:
    """Remove EXIF and AI generation markers from image.

    Creates a clean copy of the image without any metadata that could
    indicate AI generation. This is critical for brand authenticity.

    Args:
        image_path: Source image path
        output_path: Output path (default: overwrite source)

    Returns:
        Path to cleaned image

    Raises:
        MetadataError: If PIL is not available or stripping fails
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise MetadataError(
            "Pillow (PIL) is required for metadata stripping. "
            "Install with: pip install Pillow"
        ) from e

    output = output_path or image_path

    # Create parent directory if needed
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(image_path) as img:
            # Get raw pixel data without metadata
            data = list(img.getdata())

            # Create new image without any EXIF or metadata
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)

            # Save without metadata, optimized for size
            clean_img.save(output, format="PNG", optimize=True)

        logger.debug("Stripped metadata from %s", image_path.name)
        return output

    except Exception as e:
        logger.error("Failed to strip metadata from %s: %s", image_path, e)
        raise MetadataError(f"Failed to strip metadata: {e}") from e


def validate_no_ai_markers(image_path: Path) -> tuple[bool, list[str]]:
    """Verify image has no AI generation markers.

    Checks for common indicators of AI-generated content in image metadata.

    Args:
        image_path: Path to image file to validate

    Returns:
        Tuple of (is_clean, issues_found)
        - is_clean: True if no AI markers detected
        - issues_found: List of detected issues (empty if clean)

    Raises:
        MetadataError: If PIL is not available or validation fails
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise MetadataError(
            "Pillow (PIL) is required for metadata validation. "
            "Install with: pip install Pillow"
        ) from e

    issues: list[str] = []

    try:
        with Image.open(image_path) as img:
            # Check for EXIF data
            if img.info.get("exif"):
                issues.append("EXIF metadata present")

            # Check PNG text chunks for AI indicators
            ai_keywords = [
                "AI",
                "artificial",
                "generated",
                "DALL-E",
                "Midjourney",
                "Stable Diffusion",
                "Gemini",
                "Imagen",
                "diffusion",
                "neural",
            ]

            for key, value in img.info.items():
                value_str = str(value).lower()
                for keyword in ai_keywords:
                    if keyword.lower() in value_str:
                        issues.append(f"AI marker in {key}: contains '{keyword}'")

            # Check for software tags that indicate AI generation
            software = img.info.get("Software", "")
            if any(kw.lower() in software.lower() for kw in ai_keywords):
                issues.append(f"AI software tag: {software}")

        is_clean = len(issues) == 0

        if is_clean:
            logger.debug("Image %s is clean - no AI markers", image_path.name)
        else:
            logger.warning(
                "Image %s has AI markers: %s",
                image_path.name,
                ", ".join(issues),
            )

        return is_clean, issues

    except Exception as e:
        logger.error("Failed to validate metadata for %s: %s", image_path, e)
        raise MetadataError(f"Failed to validate metadata: {e}") from e


def get_image_metadata(image_path: Path) -> dict[str, str]:
    """Get all metadata from an image for inspection.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary of metadata key-value pairs

    Raises:
        MetadataError: If PIL is not available or reading fails
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise MetadataError(
            "Pillow (PIL) is required for metadata reading. "
            "Install with: pip install Pillow"
        ) from e

    try:
        with Image.open(image_path) as img:
            return {str(k): str(v) for k, v in img.info.items()}
    except Exception as e:
        logger.error("Failed to read metadata from %s: %s", image_path, e)
        raise MetadataError(f"Failed to read metadata: {e}") from e
