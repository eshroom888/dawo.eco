"""Test fixtures for Orshot integration tests."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.middleware.retry import RetryConfig, RetryResult


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
def mock_http_client():
    """Mock HTTP client for Orshot tests."""
    client = AsyncMock()
    return client


@pytest.fixture
def templates_list_response():
    """API response for listing templates."""
    return {
        "success": True,
        "data": [
            {
                "id": "tpl_abc123",
                "name": "DAWO Instagram Feed",
                "canvaId": "canva_xyz789",
                "modifications": {
                    "headline": {"type": "text", "required": True},
                    "product_name": {"type": "text", "required": True},
                    "date": {"type": "text", "required": False},
                },
                "width": 1080,
                "height": 1080,
            },
            {
                "id": "tpl_def456",
                "name": "DAWO Story Template",
                "canvaId": "canva_uvw321",
                "modifications": {
                    "headline": {"type": "text", "required": True},
                },
                "width": 1080,
                "height": 1920,
            },
        ],
        "pagination": {
            "total": 2,
            "page": 1,
            "limit": 10,
        },
    }


@pytest.fixture
def generate_graphic_response():
    """API response for generating a graphic."""
    return {
        "success": True,
        "data": {
            "id": "gen_789xyz",
            "templateId": "tpl_abc123",
            "imageUrl": "https://cdn.orshot.com/renders/gen_789xyz.png",
            "format": "png",
            "width": 1080,
            "height": 1080,
            "createdAt": "2026-02-07T12:00:00Z",
        },
    }


@pytest.fixture
def template_not_found_response():
    """API response when template is not found."""
    return {
        "success": False,
        "error": {
            "code": "TEMPLATE_NOT_FOUND",
            "message": "Template with ID 'invalid_id' not found",
        },
    }


@pytest.fixture
def rate_limit_response():
    """API response for rate limit exceeded."""
    return {
        "success": False,
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded. Retry after 60 seconds.",
        },
    }


@pytest.fixture
def sample_image_bytes():
    """Sample PNG image bytes for download tests."""
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
    return tmp_path / "test_graphic.png"
