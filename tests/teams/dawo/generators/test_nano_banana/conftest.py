"""Test fixtures for Nano Banana generator tests."""

import pytest
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Mock genai before imports
mock_genai = MagicMock()
sys.modules["google.generativeai"] = mock_genai

from teams.dawo.middleware.retry import RetryConfig

from teams.dawo.generators.nano_banana.schemas import (
    ImageGenerationRequest,
    ImageStyleType,
    ContentFormat,
)


@pytest.fixture
def mock_gemini_client(tmp_path):
    """Mock GeminiImageClient for generator tests.

    Creates a real temp file so metadata stripping works correctly.
    """
    from integrations.gemini import GeneratedImage, ImageStyle
    from PIL import Image

    # Create a real temp PNG file for metadata operations
    temp_image_path = tmp_path / "gemini_output.png"
    img = Image.new("RGB", (1080, 1080), color="blue")
    img.save(temp_image_path, format="PNG")

    client = AsyncMock()

    # Mock generate_image to return real path
    mock_image = GeneratedImage(
        id="gen_123",
        prompt="Nordic minimalist aesthetic...",
        style=ImageStyle.NORDIC,
        image_url=str(temp_image_path),
        local_path=temp_image_path,
        width=1080,
        height=1080,
        created_at=datetime.now(timezone.utc),
    )
    client.generate_image.return_value = mock_image

    # download_image should copy to requested path and return it
    async def mock_download(_image, output_path):
        """Mock download that creates a real file."""
        import shutil
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(temp_image_path, output_path)
        return output_path

    client.download_image.side_effect = mock_download

    return client


@pytest.fixture
def mock_drive_client():
    """Mock GoogleDriveClient for asset upload tests."""
    from integrations.google_drive import DriveAsset

    client = AsyncMock()

    mock_asset = DriveAsset(
        id="drive_456",
        name="20260207_wellness_test_gen123.png",
        folder_id="folder_789",
        web_view_link="https://drive.google.com/file/d/drive_456",
        download_link="https://drive.google.com/uc?id=drive_456",
        mime_type="image/png",
        created_at=datetime.now(timezone.utc),
        metadata={},
    )
    client.upload_asset.return_value = mock_asset

    return client


@pytest.fixture
def sample_generation_request():
    """Sample generation request for tests."""
    return ImageGenerationRequest(
        content_id="content_789",
        topic="morning wellness routine with natural light",
        style=ImageStyleType.WELLNESS,
        content_format=ContentFormat.FEED_SQUARE,
        brand_keywords=["peaceful", "natural", "Norwegian"],
        width=1080,
        height=1080,
    )


@pytest.fixture
def sample_image_bytes():
    """Sample PNG image bytes for tests."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
