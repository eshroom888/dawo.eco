"""Test fixtures for Gemini integration tests."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock

from teams.dawo.middleware.retry import RetryConfig


@pytest.fixture
def retry_config():
    """Default retry config for tests."""
    return RetryConfig(
        max_retries=3,
        base_delay=0.01,  # Fast tests
        backoff_multiplier=2.0,
        timeout=60.0,
    )


@pytest.fixture
def gemini_api_key():
    """Test API key for Gemini."""
    return "test_gemini_api_key_123"


@pytest.fixture
def sample_prompt():
    """Sample image generation prompt."""
    return "A peaceful Nordic forest scene with morning mist"


@pytest.fixture
def sample_image_bytes():
    """Sample PNG image bytes for tests."""
    # Minimal valid PNG header
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def tmp_output_path(tmp_path):
    """Temporary output path for download tests."""
    return tmp_path / "test_generated.png"


@pytest.fixture
def mock_genai_model():
    """Mock google.generativeai ImageGenerationModel."""
    mock = Mock()
    return mock


@pytest.fixture
def mock_generated_image_response(sample_image_bytes):
    """Mock response from Gemini image generation."""
    mock_image = Mock()
    mock_image._image_bytes = sample_image_bytes
    mock_image.save = Mock()

    mock_response = Mock()
    mock_response.images = [mock_image]
    return mock_response
