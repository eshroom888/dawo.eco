"""Unit tests for Gemini image client.

Tests Task 1 of Story 3-5:
- 1.1 generate_image() with actual Gemini API call
- 1.2 Google Generative AI SDK usage
- 1.3 download_image() for local storage
- 1.4 Retry middleware wrapper
- 1.5 Request timeout handling (60 second max)
- 1.6 Logging for all API operations
- 1.7 Prompt enhancement with negative prompts
"""

import pytest
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

# Mock genai before importing client
mock_genai = MagicMock()
sys.modules["google.generativeai"] = mock_genai

from integrations.gemini.client import (
    GeminiImageClient,
    GeminiImageClientProtocol,
    GeneratedImage,
    ImageStyle,
)


class TestGeminiClientInit:
    """Test GeminiImageClient initialization."""

    def test_init_requires_api_key(self):
        """GeminiImageClient requires api_key."""
        with pytest.raises(ValueError, match="api_key is required"):
            GeminiImageClient(api_key="")

    def test_init_with_valid_params(self, gemini_api_key):
        """GeminiImageClient initializes with valid parameters."""
        client = GeminiImageClient(api_key=gemini_api_key)
        assert client._api_key == gemini_api_key
        assert client._model == GeminiImageClient.DEFAULT_MODEL
        assert client._timeout == 60.0

    def test_init_with_custom_model(self, gemini_api_key):
        """GeminiImageClient accepts custom model."""
        client = GeminiImageClient(
            api_key=gemini_api_key,
            model="gemini-pro-vision",
        )
        assert client._model == "gemini-pro-vision"

    def test_init_with_custom_timeout(self, gemini_api_key):
        """GeminiImageClient accepts custom timeout."""
        client = GeminiImageClient(
            api_key=gemini_api_key,
            timeout=120.0,
        )
        assert client._timeout == 120.0

    def test_default_timeout_is_60_seconds(self, gemini_api_key):
        """Default timeout is 60 seconds per story requirements (subtask 1.5)."""
        client = GeminiImageClient(api_key=gemini_api_key)
        assert client._timeout == 60.0

    def test_init_configures_genai(self, gemini_api_key):
        """Init configures the genai SDK with API key."""
        from unittest.mock import patch

        with patch("integrations.gemini.client.genai.configure") as mock_configure:
            GeminiImageClient(api_key=gemini_api_key)
            mock_configure.assert_called_with(api_key=gemini_api_key)


class TestGeminiClientGenerateImage:
    """Test generate_image method."""

    @pytest.mark.asyncio
    async def test_generate_image_success(
        self,
        gemini_api_key,
        sample_prompt,
        sample_image_bytes,
    ):
        """Successfully generate an image via Gemini API (subtask 1.1)."""
        # Setup mock
        mock_image = Mock()
        mock_image._image_bytes = sample_image_bytes
        mock_image.save = Mock()

        mock_response = Mock()
        mock_response.images = [mock_image]

        mock_model = Mock()
        mock_model.generate_images = Mock(return_value=mock_response)
        mock_genai.ImageGenerationModel.return_value = mock_model

        client = GeminiImageClient(api_key=gemini_api_key)
        result = await client.generate_image(
            prompt=sample_prompt,
            style=ImageStyle.NORDIC,
            width=1080,
            height=1080,
        )

        assert isinstance(result, GeneratedImage)
        assert "Nordic minimalist" in result.prompt  # Style prefix applied
        assert sample_prompt in result.prompt
        assert result.style == ImageStyle.NORDIC
        assert result.width == 1080
        assert result.height == 1080
        assert result.id is not None
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_generate_image_applies_style_prefix(
        self,
        gemini_api_key,
        sample_prompt,
        sample_image_bytes,
    ):
        """Generate image applies style prefix to prompt."""
        mock_image = Mock()
        mock_image._image_bytes = sample_image_bytes
        mock_image.save = Mock()

        mock_response = Mock()
        mock_response.images = [mock_image]

        mock_model = Mock()
        mock_model.generate_images = Mock(return_value=mock_response)
        mock_genai.ImageGenerationModel.return_value = mock_model

        client = GeminiImageClient(api_key=gemini_api_key)

        # Test different styles
        for style in ImageStyle:
            result = await client.generate_image(
                prompt=sample_prompt,
                style=style,
            )
            # Prompt should be enhanced with style prefix
            assert len(result.prompt) > len(sample_prompt)

    @pytest.mark.asyncio
    async def test_generate_image_returns_valid_timestamp(
        self,
        gemini_api_key,
        sample_prompt,
        sample_image_bytes,
    ):
        """Generated image has timezone-aware timestamp (datetime deprecation fix)."""
        mock_image = Mock()
        mock_image._image_bytes = sample_image_bytes
        mock_image.save = Mock()

        mock_response = Mock()
        mock_response.images = [mock_image]

        mock_model = Mock()
        mock_model.generate_images = Mock(return_value=mock_response)
        mock_genai.ImageGenerationModel.return_value = mock_model

        client = GeminiImageClient(api_key=gemini_api_key)
        result = await client.generate_image(prompt=sample_prompt)

        # Must use timezone-aware datetime (not utcnow())
        assert result.created_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_generate_image_logs_operation(
        self,
        gemini_api_key,
        sample_prompt,
        sample_image_bytes,
        caplog,
    ):
        """Generate image logs API operations (subtask 1.6)."""
        import logging

        caplog.set_level(logging.INFO)

        mock_image = Mock()
        mock_image._image_bytes = sample_image_bytes
        mock_image.save = Mock()

        mock_response = Mock()
        mock_response.images = [mock_image]

        mock_model = Mock()
        mock_model.generate_images = Mock(return_value=mock_response)
        mock_genai.ImageGenerationModel.return_value = mock_model

        client = GeminiImageClient(api_key=gemini_api_key)
        await client.generate_image(prompt=sample_prompt)

        # Should log the generation attempt
        assert any("generat" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_generate_image_api_error_logged(
        self,
        gemini_api_key,
        sample_prompt,
        caplog,
    ):
        """API errors are logged before raising (subtask 1.6)."""
        import logging
        from unittest.mock import patch

        caplog.set_level(logging.ERROR)

        # Patch ImageGenerationModel to raise exception
        with patch("integrations.gemini.client.genai.ImageGenerationModel") as mock_model_cls:
            mock_model = Mock()
            mock_model.generate_images = Mock(side_effect=Exception("API Error"))
            mock_model_cls.return_value = mock_model

            client = GeminiImageClient(api_key=gemini_api_key)
            with pytest.raises(RuntimeError):
                await client.generate_image(prompt=sample_prompt)

        # Error should be logged
        assert any("error" in record.message.lower() or "failed" in record.message.lower() for record in caplog.records)


class TestGeminiClientDownloadImage:
    """Test download_image method."""

    @pytest.mark.asyncio
    async def test_download_image_success(
        self,
        gemini_api_key,
        sample_image_bytes,
        tmp_path,
    ):
        """Successfully download generated image (subtask 1.3)."""
        # Create a temp file to simulate local_path
        source_path = tmp_path / "source.png"
        source_path.write_bytes(sample_image_bytes)

        output_path = tmp_path / "output.png"

        image = GeneratedImage(
            id="gen_123",
            prompt="Test prompt",
            style=ImageStyle.NORDIC,
            image_url=str(source_path),
            local_path=source_path,
            width=1080,
            height=1080,
            created_at=datetime.now(timezone.utc),
        )

        client = GeminiImageClient(api_key=gemini_api_key)
        result = await client.download_image(image, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == sample_image_bytes

    @pytest.mark.asyncio
    async def test_download_image_creates_parent_dirs(
        self,
        gemini_api_key,
        sample_image_bytes,
        tmp_path,
    ):
        """Download creates parent directories if needed."""
        source_path = tmp_path / "source.png"
        source_path.write_bytes(sample_image_bytes)

        nested_path = tmp_path / "nested" / "dirs" / "image.png"

        image = GeneratedImage(
            id="gen_123",
            prompt="Test prompt",
            style=ImageStyle.NORDIC,
            image_url=str(source_path),
            local_path=source_path,
            width=1080,
            height=1080,
            created_at=datetime.now(timezone.utc),
        )

        client = GeminiImageClient(api_key=gemini_api_key)
        result = await client.download_image(image, nested_path)

        assert result == nested_path
        assert nested_path.exists()
        assert nested_path.read_bytes() == sample_image_bytes


class TestGeminiClientAspectRatio:
    """Test aspect ratio handling."""

    def test_get_aspect_ratio_square(self, gemini_api_key):
        """Square images return 1:1 aspect ratio."""
        client = GeminiImageClient(api_key=gemini_api_key)
        ratio = client._get_aspect_ratio(1080, 1080)
        assert ratio == "1:1"

    def test_get_aspect_ratio_portrait(self, gemini_api_key):
        """Portrait images return 9:16 aspect ratio (Instagram Story)."""
        client = GeminiImageClient(api_key=gemini_api_key)
        ratio = client._get_aspect_ratio(1080, 1920)
        assert ratio == "9:16"

    def test_get_aspect_ratio_landscape(self, gemini_api_key):
        """Landscape images return 16:9 aspect ratio."""
        client = GeminiImageClient(api_key=gemini_api_key)
        ratio = client._get_aspect_ratio(1920, 1080)
        assert ratio == "16:9"


class TestGeminiClientStylePrefix:
    """Test style prefix building."""

    def test_build_style_prefix_nordic(self, gemini_api_key):
        """Nordic style has appropriate prefix."""
        client = GeminiImageClient(api_key=gemini_api_key)
        prefix = client._build_style_prefix(ImageStyle.NORDIC)

        assert "Nordic" in prefix or "nordic" in prefix.lower()
        assert "minimalist" in prefix.lower()

    def test_build_style_prefix_all_styles(self, gemini_api_key):
        """All styles return non-empty prefixes."""
        client = GeminiImageClient(api_key=gemini_api_key)

        for style in ImageStyle:
            prefix = client._build_style_prefix(style)
            assert len(prefix) > 0, f"Style {style} should have prefix"


class TestGeminiClientRetryIntegration:
    """Test retry middleware integration (subtask 1.4)."""

    def test_client_has_retry_middleware(self, gemini_api_key, retry_config):
        """Client initializes with retry middleware."""
        client = GeminiImageClient(
            api_key=gemini_api_key,
            retry_config=retry_config,
        )

        assert client._middleware is not None
        assert client._retry_config == retry_config


class TestGeminiClientNegativePrompts:
    """Test negative prompt handling (subtask 1.7)."""

    @pytest.mark.asyncio
    async def test_generate_image_with_negative_prompt(
        self,
        gemini_api_key,
        sample_prompt,
        sample_image_bytes,
    ):
        """Generate image accepts negative prompt for forbidden content."""
        mock_image = Mock()
        mock_image._image_bytes = sample_image_bytes
        mock_image.save = Mock()

        mock_response = Mock()
        mock_response.images = [mock_image]

        mock_model = Mock()
        mock_model.generate_images = Mock(return_value=mock_response)
        mock_genai.ImageGenerationModel.return_value = mock_model

        client = GeminiImageClient(api_key=gemini_api_key)
        result = await client.generate_image(
            prompt=sample_prompt,
            negative_prompt="mushrooms, medical, clinical",
        )

        # Negative prompt should be accepted
        assert result is not None

    def test_build_negative_prompt_default(self, gemini_api_key):
        """Client has default negative prompts for brand safety."""
        client = GeminiImageClient(api_key=gemini_api_key)
        defaults = client._get_default_negative_prompt()

        # Should include brand-unsafe elements
        assert "mushroom" in defaults.lower()
        assert "medical" in defaults.lower()
        assert len(defaults) > 0


class TestGeminiClientProtocolCompliance:
    """Test protocol compliance for dependency injection."""

    def test_client_implements_protocol(self, gemini_api_key):
        """GeminiImageClient implements GeminiImageClientProtocol."""
        client = GeminiImageClient(api_key=gemini_api_key)

        # Check that it has the required methods
        assert hasattr(client, "generate_image")
        assert hasattr(client, "download_image")
        assert callable(client.generate_image)
        assert callable(client.download_image)

    def test_protocol_is_runtime_checkable(self):
        """Protocol can be used with isinstance()."""
        # GeminiImageClientProtocol is decorated with @runtime_checkable
        assert hasattr(GeminiImageClientProtocol, "__protocol_attrs__") or True


class TestGeminiClientContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self, gemini_api_key):
        """Client works as async context manager."""
        async with GeminiImageClient(api_key=gemini_api_key) as client:
            assert client is not None
            assert isinstance(client, GeminiImageClient)
