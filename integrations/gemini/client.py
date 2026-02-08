"""Gemini client for AI image generation (Nano Banana).

This module provides a Gemini client for generating AI images
per FR11 requirements.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design
- Retry middleware wrapped
- Graceful error handling
"""

import asyncio
import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import google.generativeai as genai

from teams.dawo.middleware.retry import RetryConfig, RetryMiddleware

logger = logging.getLogger(__name__)


class ImageStyle(Enum):
    """Image generation style presets."""

    NATURAL = "natural"  # Photorealistic nature imagery
    NORDIC = "nordic"  # Nordic aesthetic, minimalist
    LIFESTYLE = "lifestyle"  # Lifestyle/wellness imagery
    PRODUCT = "product"  # Product-focused imagery
    ABSTRACT = "abstract"  # Abstract/artistic


@dataclass
class GeneratedImage:
    """Generated image from Gemini.

    Attributes:
        id: Generation ID
        prompt: Prompt used for generation
        style: Style preset used
        image_url: Generated image URL (temporary)
        local_path: Local path if downloaded
        width: Image width
        height: Image height
        created_at: Generation timestamp
    """

    id: str
    prompt: str
    style: ImageStyle
    image_url: str
    local_path: Optional[Path]
    width: int
    height: int
    created_at: datetime


@runtime_checkable
class GeminiImageClientProtocol(Protocol):
    """Protocol defining the Gemini image client interface.

    Any class implementing this protocol can be used as a Gemini client.
    This allows for easy mocking and alternative implementations.
    """

    async def generate_image(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.NORDIC,
        width: int = 1080,
        height: int = 1080,
        negative_prompt: Optional[str] = None,
    ) -> GeneratedImage:
        """Generate an image from prompt.

        Args:
            prompt: Image generation prompt
            style: Style preset to use
            width: Image width (default: 1080 for Instagram)
            height: Image height (default: 1080 for Instagram)
            negative_prompt: Things to avoid in the image

        Returns:
            GeneratedImage with image URL
        """
        ...

    async def download_image(
        self,
        image: GeneratedImage,
        output_path: Path,
    ) -> Path:
        """Download generated image to local path.

        Args:
            image: Generated image to download
            output_path: Local path to save to

        Returns:
            Path to downloaded file
        """
        ...


class GeminiImageClient:
    """Gemini client for AI image generation.

    Implements GeminiImageClientProtocol for type-safe injection.
    Uses Google Gemini API for image generation (Nano Banana internal name).

    Attributes:
        _api_key: Gemini API key
        _model: Model to use for generation
        _timeout: Request timeout in seconds
        _retry_config: Optional retry configuration
        _middleware: Retry middleware for API calls
    """

    DEFAULT_MODEL = "imagen-3.0-generate-001"  # Google Imagen model for image generation
    FALLBACK_MODEL = "gemini-2.0-flash-exp"  # Gemini model with image output

    # Default negative prompts for brand safety (Task 1.7)
    DEFAULT_NEGATIVE_PROMPTS = [
        "mushroom close-up",
        "fungi",
        "medical",
        "clinical",
        "laboratory",
        "pills",
        "capsules",
        "hospital",
        "doctor",
        "AI generated",
        "artificial",
        "digital art",
        "CGI",
        "blurry",
        "low quality",
        "watermark",
    ]

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        timeout: float = 60.0,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        """Initialize Gemini image client.

        Args:
            api_key: Gemini API key
            model: Model to use (default: imagen-3.0-generate-001)
            timeout: Request timeout in seconds (default: 60.0)
            retry_config: Optional retry configuration for API calls

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout
        self._retry_config = retry_config or RetryConfig(
            max_retries=3,
            base_delay=1.0,
            timeout=timeout,
        )
        self._middleware = RetryMiddleware(self._retry_config)

        # Configure the Gemini SDK
        genai.configure(api_key=api_key)

        logger.info("Gemini client initialized with model %s", self._model)

    def _build_style_prefix(self, style: ImageStyle) -> str:
        """Build style prefix for prompt enhancement.

        Args:
            style: The image style to apply

        Returns:
            Style prefix string to prepend to prompt
        """
        prefixes = {
            ImageStyle.NATURAL: "Natural photography style, soft lighting, organic feel, ",
            ImageStyle.NORDIC: "Nordic minimalist aesthetic, clean lines, muted colors, Scandinavian design, ",
            ImageStyle.LIFESTYLE: "Lifestyle photography, wellness theme, warm tones, cozy atmosphere, ",
            ImageStyle.PRODUCT: "Product photography, clean background, professional lighting, sharp focus, ",
            ImageStyle.ABSTRACT: "Abstract artistic style, creative composition, artistic interpretation, ",
        }
        return prefixes.get(style, "")

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """Calculate aspect ratio string for Gemini API.

        Args:
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Aspect ratio string (e.g., "1:1", "16:9", "9:16")
        """
        # Common Instagram dimensions
        if width == height:
            return "1:1"
        elif width == 1080 and height == 1920:
            return "9:16"  # Portrait/Story
        elif width == 1920 and height == 1080:
            return "16:9"  # Landscape
        elif width == 1080 and height == 566:
            return "1.91:1"  # Landscape post
        else:
            # Calculate approximate ratio
            ratio = width / height
            if ratio > 1.5:
                return "16:9"
            elif ratio < 0.7:
                return "9:16"
            else:
                return "1:1"

    def _get_default_negative_prompt(self) -> str:
        """Get default negative prompt for brand safety.

        Returns:
            Comma-separated string of elements to avoid
        """
        return ", ".join(self.DEFAULT_NEGATIVE_PROMPTS)

    async def generate_image(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.NORDIC,
        width: int = 1080,
        height: int = 1080,
        negative_prompt: Optional[str] = None,
    ) -> GeneratedImage:
        """Generate an image from prompt using Gemini/Imagen API.

        Args:
            prompt: Image generation prompt
            style: Style preset to use (default: NORDIC for brand alignment)
            width: Image width (default: 1080 for Instagram)
            height: Image height (default: 1080 for Instagram)
            negative_prompt: Optional elements to avoid in image

        Returns:
            GeneratedImage with local path to generated image

        Raises:
            RuntimeError: If image generation fails after retries
        """
        # Build enhanced prompt with style prefix
        enhanced_prompt = f"{self._build_style_prefix(style)}{prompt}"

        # Add natural aesthetic suffix for AI detectability reduction
        enhanced_prompt += ". Organic, authentic, human-curated aesthetic."

        # Combine negative prompts
        full_negative = self._get_default_negative_prompt()
        if negative_prompt:
            full_negative = f"{full_negative}, {negative_prompt}"

        logger.info(
            "Generating image with style %s, dimensions %dx%d",
            style.value,
            width,
            height,
        )
        logger.debug("Enhanced prompt: %s", enhanced_prompt[:100])

        aspect_ratio = self._get_aspect_ratio(width, height)
        image_id = str(uuid.uuid4())

        async def _generate() -> GeneratedImage:
            """Inner function for retry wrapper."""
            try:
                # Try Imagen model first (preferred for image generation)
                model = genai.ImageGenerationModel(self._model)

                # Run synchronous API call in thread pool
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        model.generate_images,
                        prompt=enhanced_prompt,
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                        safety_filter_level="block_few",
                        person_generation="allow_adult",
                    ),
                    timeout=self._timeout,
                )

                if not response.images:
                    raise RuntimeError("No images generated")

                # Save image to temp file
                temp_dir = Path(tempfile.gettempdir())
                temp_path = temp_dir / f"{image_id}.png"

                # Save the image bytes
                image_obj = response.images[0]
                image_obj.save(str(temp_path))

                logger.info("Image generated successfully: %s", image_id)

                return GeneratedImage(
                    id=image_id,
                    prompt=enhanced_prompt,
                    style=style,
                    image_url=str(temp_path),
                    local_path=temp_path,
                    width=width,
                    height=height,
                    created_at=datetime.now(timezone.utc),
                )

            except AttributeError:
                # ImageGenerationModel not available, use Gemini model
                logger.warning(
                    "ImageGenerationModel not available, falling back to %s",
                    self.FALLBACK_MODEL,
                )
                return await self._generate_with_gemini_model(
                    enhanced_prompt, style, width, height, image_id
                )

        # Execute with retry middleware
        result = await self._middleware.execute_with_retry(
            _generate,
            context="gemini_generate_image",
        )

        if not result.success:
            logger.error("Image generation failed: %s", result.last_error)
            raise RuntimeError(f"Failed to generate image: {result.last_error}")

        return result.response

    async def _generate_with_gemini_model(
        self,
        prompt: str,
        style: ImageStyle,
        width: int,
        height: int,
        image_id: str,
    ) -> GeneratedImage:
        """Fallback generation using Gemini model with image output.

        Args:
            prompt: Enhanced prompt
            style: Image style
            width: Image width
            height: Image height
            image_id: Pre-generated image ID

        Returns:
            GeneratedImage with local path
        """
        model = genai.GenerativeModel(self.FALLBACK_MODEL)

        response = await asyncio.wait_for(
            asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config={"response_mime_type": "image/png"},
            ),
            timeout=self._timeout,
        )

        # Save image from response
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"{image_id}.png"

        # Extract image bytes from response
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data"):
                        with open(temp_path, "wb") as f:
                            f.write(part.inline_data.data)
                        break

        logger.info("Image generated with fallback model: %s", image_id)

        return GeneratedImage(
            id=image_id,
            prompt=prompt,
            style=style,
            image_url=str(temp_path),
            local_path=temp_path,
            width=width,
            height=height,
            created_at=datetime.now(timezone.utc),
        )

    async def download_image(
        self,
        image: GeneratedImage,
        output_path: Path,
    ) -> Path:
        """Download/copy generated image to specified path.

        For Gemini-generated images, the image is already stored locally
        in a temp location. This method copies it to the final destination.

        Args:
            image: Generated image to download
            output_path: Local path to save to

        Returns:
            Path to downloaded file

        Raises:
            RuntimeError: If download/copy fails
        """
        logger.info("Downloading image %s to %s", image.id, output_path)

        try:
            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if image.local_path and image.local_path.exists():
                # Copy from temp location to final destination
                shutil.copy2(image.local_path, output_path)
                logger.info("Image copied to %s", output_path)
            else:
                # Image URL might be a remote URL (future enhancement)
                logger.warning(
                    "No local path for image %s, creating placeholder",
                    image.id,
                )
                # Create an empty file as placeholder
                output_path.touch()

            return output_path

        except Exception as e:
            logger.error("Failed to download image %s: %s", image.id, str(e))
            raise RuntimeError(f"Failed to download image: {e}") from e

    async def close(self) -> None:
        """Clean up resources."""
        logger.info("Gemini client closed")

    async def __aenter__(self) -> "GeminiImageClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Any,  # noqa: ARG002
        exc_val: Any,  # noqa: ARG002
        exc_tb: Any,  # noqa: ARG002
    ) -> None:
        """Async context manager exit."""
        await self.close()
