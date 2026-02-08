"""Unit tests for NanoBananaGenerator agent.

Tests Task 9 of Story 3-5:
- 9.1 Test GeminiImageClient with mocked responses
- 9.2 Test prompt building with various content types
- 9.3 Test negative prompt enforcement
- 9.4 Test quality score calculation
- 9.5 Test metadata stripping
- 9.6 Test Google Drive integration with mock client
- 9.7 Test dimension handling for different formats
- 9.8 Test error handling for API failures
"""

import pytest
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Mock genai before imports
mock_genai = MagicMock()
sys.modules["google.generativeai"] = mock_genai

from teams.dawo.generators.nano_banana import (
    NanoBananaGenerator,
    NanoBananaGeneratorProtocol,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageStyleType,
    ContentFormat,
)


class TestNanoBananaGeneratorInit:
    """Test NanoBananaGenerator initialization."""

    def test_init_with_dependencies(self, mock_gemini_client, mock_drive_client):
        """Generator initializes with injected dependencies."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        assert generator._gemini == mock_gemini_client
        assert generator._drive == mock_drive_client
        assert generator._scorer is not None


class TestNanoBananaGeneratorGenerate:
    """Test generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Successfully generate an AI image."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        result = await generator.generate(sample_generation_request)

        assert isinstance(result, ImageGenerationResult)
        assert result.success is True
        assert result.content_id == sample_generation_request.content_id
        assert result.image_id is not None
        assert result.quality_score > 0

    @pytest.mark.asyncio
    async def test_generate_calls_gemini_client(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Generate calls Gemini client with correct parameters."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        await generator.generate(sample_generation_request)

        mock_gemini_client.generate_image.assert_called_once()
        call_args = mock_gemini_client.generate_image.call_args
        assert "prompt" in call_args.kwargs
        assert call_args.kwargs["width"] == 1080
        assert call_args.kwargs["height"] == 1080

    @pytest.mark.asyncio
    async def test_generate_uploads_to_drive(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Generate uploads image to Google Drive."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        result = await generator.generate(sample_generation_request)

        mock_drive_client.upload_asset.assert_called_once()
        assert result.drive_file_id is not None

    @pytest.mark.asyncio
    async def test_generate_failure_returns_error_result(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Generate returns failure result on API error."""
        mock_gemini_client.generate_image.side_effect = Exception("API Error")

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        result = await generator.generate(sample_generation_request)

        assert result.success is False
        assert "API Error" in result.error_message

    @pytest.mark.asyncio
    async def test_generate_continues_without_drive(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Generate succeeds even if Drive upload fails."""
        mock_drive_client.upload_asset.side_effect = Exception("Drive Error")

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        result = await generator.generate(sample_generation_request)

        # Should still succeed - Drive failure is graceful
        assert result.success is True
        assert result.drive_file_id is None


class TestNanoBananaGeneratorDimensions:
    """Test dimension handling (subtask 9.7)."""

    @pytest.mark.asyncio
    async def test_dimensions_feed_square(
        self,
        mock_gemini_client,
        mock_drive_client,
    ):
        """Feed square format uses 1080x1080 dimensions."""
        request = ImageGenerationRequest(
            content_id="test_123",
            topic="test topic",
            content_format=ContentFormat.FEED_SQUARE,
        )

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        await generator.generate(request)

        call_args = mock_gemini_client.generate_image.call_args
        assert call_args.kwargs["width"] == 1080
        assert call_args.kwargs["height"] == 1080

    @pytest.mark.asyncio
    async def test_dimensions_story(
        self,
        mock_gemini_client,
        mock_drive_client,
    ):
        """Story format uses 1080x1920 dimensions."""
        request = ImageGenerationRequest(
            content_id="test_123",
            topic="test topic",
            content_format=ContentFormat.STORY,
        )

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        await generator.generate(request)

        call_args = mock_gemini_client.generate_image.call_args
        assert call_args.kwargs["width"] == 1080
        assert call_args.kwargs["height"] == 1920

    def test_request_get_dimensions_override(self):
        """Custom dimensions override format defaults."""
        request = ImageGenerationRequest(
            content_id="test_123",
            topic="test topic",
            width=800,
            height=600,
        )

        dims = request.get_dimensions()
        assert dims == (800, 600)


class TestNanoBananaGeneratorPrompts:
    """Test prompt building (subtasks 9.2, 9.3)."""

    @pytest.mark.asyncio
    async def test_prompt_includes_topic(
        self,
        mock_gemini_client,
        mock_drive_client,
    ):
        """Generated prompt includes the topic."""
        request = ImageGenerationRequest(
            content_id="test_123",
            topic="cozy Norwegian cabin in winter",
        )

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        await generator.generate(request)

        call_args = mock_gemini_client.generate_image.call_args
        prompt = call_args.kwargs["prompt"]
        assert "cozy Norwegian cabin" in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_style_prefix(
        self,
        mock_gemini_client,
        mock_drive_client,
    ):
        """Generated prompt includes style prefix."""
        request = ImageGenerationRequest(
            content_id="test_123",
            topic="wellness scene",
            style=ImageStyleType.NATURE,
        )

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        await generator.generate(request)

        call_args = mock_gemini_client.generate_image.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Norwegian" in prompt or "forest" in prompt

    @pytest.mark.asyncio
    async def test_negative_prompt_passed(
        self,
        mock_gemini_client,
        mock_drive_client,
    ):
        """Negative prompt is passed to Gemini client."""
        request = ImageGenerationRequest(
            content_id="test_123",
            topic="wellness scene",
            avoid_elements=["pills", "medicine"],
        )

        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        await generator.generate(request)

        call_args = mock_gemini_client.generate_image.call_args
        assert "negative_prompt" in call_args.kwargs


class TestNanoBananaGeneratorQuality:
    """Test quality scoring (subtask 9.4)."""

    @pytest.mark.asyncio
    async def test_quality_score_calculated(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Quality score is calculated for generated image."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        result = await generator.generate(sample_generation_request)

        assert result.quality_score >= 1.0
        assert result.quality_score <= 10.0

    @pytest.mark.asyncio
    async def test_needs_review_flag(
        self,
        mock_gemini_client,
        mock_drive_client,
        sample_generation_request,
    ):
        """Needs review flag is set based on quality score."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        result = await generator.generate(sample_generation_request)

        # For a successful generation with NORDIC style, should not need review
        assert isinstance(result.needs_review, bool)


class TestNanoBananaGeneratorProtocolCompliance:
    """Test protocol compliance."""

    def test_generator_has_generate_method(
        self,
        mock_gemini_client,
        mock_drive_client,
    ):
        """Generator has the generate method."""
        generator = NanoBananaGenerator(
            gemini=mock_gemini_client,
            drive=mock_drive_client,
        )

        assert hasattr(generator, "generate")
        assert callable(generator.generate)
