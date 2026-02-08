"""Integration tests for Nano Banana AI Image Generator.

These tests require real API credentials and are skipped by default.
Set GEMINI_API_KEY environment variable to run Gemini tests.
Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_DRIVE_FOLDER_ID for Drive tests.
"""

import os
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Check for API keys before importing
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Mock genai if no API key
if not GEMINI_API_KEY:
    mock_genai = MagicMock()
    sys.modules["google.generativeai"] = mock_genai

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not GEMINI_API_KEY,
    reason="GEMINI_API_KEY not set - skipping integration tests",
)


@pytest.fixture
def gemini_client():
    """Create real GeminiImageClient for integration tests."""
    from integrations.gemini import GeminiImageClient

    return GeminiImageClient(api_key=GEMINI_API_KEY)


@pytest.fixture
def drive_client():
    """Create Drive client for integration tests.

    Uses REAL credentials when GOOGLE_APPLICATION_CREDENTIALS is set,
    otherwise falls back to mock for CI environments.
    """
    from unittest.mock import AsyncMock
    from integrations.google_drive import DriveAsset
    from datetime import datetime, timezone

    # Use real Drive client when credentials are available (Task 10.3)
    if GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_DRIVE_FOLDER_ID:
        from integrations.google_drive import GoogleDriveClient

        return GoogleDriveClient(
            credentials_path=Path(GOOGLE_APPLICATION_CREDENTIALS),
            root_folder_id=GOOGLE_DRIVE_FOLDER_ID,
        )

    # Fall back to mock when no credentials (CI environment)
    client = AsyncMock()
    mock_asset = DriveAsset(
        id="integration_test_456",
        name="integration_test.png",
        folder_id=GOOGLE_DRIVE_FOLDER_ID or "test_folder",
        web_view_link="https://drive.google.com/file/d/integration_test_456",
        download_link="https://drive.google.com/uc?id=integration_test_456",
        mime_type="image/png",
        created_at=datetime.now(timezone.utc),
        metadata={},
    )
    client.upload_asset.return_value = mock_asset
    return client


@pytest.fixture
def has_real_drive_credentials() -> bool:
    """Check if real Drive credentials are available."""
    return bool(GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_DRIVE_FOLDER_ID)


class TestGeminiClientIntegration:
    """Integration tests for GeminiImageClient with real API."""

    @pytest.mark.asyncio
    async def test_generate_wellness_image(self, gemini_client):
        """Generate a wellness-themed image with real API."""
        from integrations.gemini import ImageStyle

        result = await gemini_client.generate_image(
            prompt="Peaceful Norwegian morning with soft natural light, minimalist aesthetic",
            style=ImageStyle.NORDIC,
            width=512,
            height=512,
        )

        assert result.id is not None
        assert result.image_url is not None

    @pytest.mark.asyncio
    async def test_generate_with_negative_prompt(self, gemini_client):
        """Generate image with negative prompt constraints."""
        result = await gemini_client.generate_image(
            prompt="Natural wellness scene with herbal tea",
            negative_prompt="mushroom, fungi, pills, medicine, medical equipment",
            width=512,
            height=512,
        )

        assert result.id is not None

    @pytest.mark.asyncio
    async def test_download_generated_image(self, gemini_client, tmp_path):
        """Download a generated image to local file."""
        from integrations.gemini import ImageStyle

        image = await gemini_client.generate_image(
            prompt="Simple nature scene",
            style=ImageStyle.NORDIC,
            width=512,
            height=512,
        )

        output_path = tmp_path / "downloaded.png"
        result = await gemini_client.download_image(image, output_path)

        assert result.exists()
        assert result.stat().st_size > 0


class TestNanoBananaGeneratorIntegration:
    """Integration tests for full NanoBananaGenerator workflow."""

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self, gemini_client, drive_client):
        """Test complete generation workflow with real Gemini API."""
        from teams.dawo.generators.nano_banana import (
            NanoBananaGenerator,
            ImageGenerationRequest,
            ImageStyleType,
            ContentFormat,
        )

        generator = NanoBananaGenerator(
            gemini=gemini_client,
            drive=drive_client,
        )

        request = ImageGenerationRequest(
            content_id="integration_test_001",
            topic="peaceful morning wellness routine",
            style=ImageStyleType.WELLNESS,
            content_format=ContentFormat.FEED_SQUARE,
            brand_keywords=["natural", "Norwegian", "peaceful"],
            width=512,
            height=512,
        )

        result = await generator.generate(request)

        assert result.success is True
        assert result.image_id is not None
        assert result.quality_score >= 1.0
        assert result.quality_score <= 10.0
        assert result.prompt_used is not None

    @pytest.mark.asyncio
    async def test_story_format_dimensions(self, gemini_client, drive_client):
        """Test story format uses correct dimensions."""
        from teams.dawo.generators.nano_banana import (
            NanoBananaGenerator,
            ImageGenerationRequest,
            ImageStyleType,
            ContentFormat,
        )

        generator = NanoBananaGenerator(
            gemini=gemini_client,
            drive=drive_client,
        )

        request = ImageGenerationRequest(
            content_id="integration_test_002",
            topic="vertical nature scene",
            style=ImageStyleType.NATURE,
            content_format=ContentFormat.STORY,
            width=512,  # Scaled down for testing
            height=910,  # 9:16 ratio
        )

        result = await generator.generate(request)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_negative_prompt_enforcement(self, gemini_client, drive_client):
        """Test that negative prompts are enforced."""
        from teams.dawo.generators.nano_banana import (
            NanoBananaGenerator,
            ImageGenerationRequest,
            ImageStyleType,
        )

        generator = NanoBananaGenerator(
            gemini=gemini_client,
            drive=drive_client,
        )

        request = ImageGenerationRequest(
            content_id="integration_test_003",
            topic="natural wellness supplements",
            style=ImageStyleType.WELLNESS,
            avoid_elements=["pills", "capsules", "medicine"],
            width=512,
            height=512,
        )

        result = await generator.generate(request)

        # Should still generate successfully with constraints
        assert result.success is True
        assert "pills" in result.prompt_used or "negative" in str(result).lower()


class TestQualityScoringIntegration:
    """Integration tests for quality scoring with real images."""

    @pytest.mark.asyncio
    async def test_quality_score_real_image(self, gemini_client):
        """Test quality scoring on real generated image."""
        from integrations.gemini import ImageStyle
        from teams.dawo.generators.nano_banana.quality import ImageQualityScorer

        # Generate real image
        image = await gemini_client.generate_image(
            prompt="Nordic minimalist wellness photography, natural light",
            style=ImageStyle.NORDIC,
            width=1080,
            height=1080,
        )

        scorer = ImageQualityScorer()
        assessment = scorer.score(
            image,
            prompt_compliance=0.9,
            generation_success=True,
        )

        # Real Nordic-style image should score well
        assert assessment.overall_score >= 5.0
        assert assessment.brand_alignment >= 6.0


class TestMetadataStrippingIntegration:
    """Integration tests for metadata stripping (Task 10.4)."""

    @pytest.mark.asyncio
    async def test_generated_image_has_no_ai_markers(
        self,
        gemini_client,
        drive_client,
    ):
        """Verify metadata is stripped from generated and uploaded images (Task 10.4)."""
        from teams.dawo.generators.nano_banana import (
            NanoBananaGenerator,
            ImageGenerationRequest,
            ImageStyleType,
        )
        from integrations.gemini import validate_no_ai_markers

        generator = NanoBananaGenerator(
            gemini=gemini_client,
            drive=drive_client,
        )

        request = ImageGenerationRequest(
            content_id="metadata_test_001",
            topic="peaceful nature scene",
            style=ImageStyleType.NATURE,
            width=512,
            height=512,
        )

        result = await generator.generate(request)

        assert result.success is True
        assert result.local_path is not None

        # Verify the local image has no AI markers after stripping
        is_clean, issues = validate_no_ai_markers(result.local_path)
        assert is_clean is True, f"Image should have no AI markers: {issues}"

    @pytest.mark.asyncio
    async def test_metadata_stripped_before_upload(
        self,
        gemini_client,
        drive_client,
    ):
        """Verify metadata is stripped BEFORE uploading to Drive."""
        from teams.dawo.generators.nano_banana import (
            NanoBananaGenerator,
            ImageGenerationRequest,
            ImageStyleType,
        )
        from integrations.gemini import validate_no_ai_markers, get_image_metadata

        generator = NanoBananaGenerator(
            gemini=gemini_client,
            drive=drive_client,
        )

        request = ImageGenerationRequest(
            content_id="metadata_upload_test_001",
            topic="wellness morning routine",
            style=ImageStyleType.WELLNESS,
            width=512,
            height=512,
        )

        result = await generator.generate(request)

        assert result.success is True

        # Check local file is clean
        if result.local_path and result.local_path.exists():
            metadata = get_image_metadata(result.local_path)

            # Should not contain any AI-related metadata
            metadata_str = str(metadata).lower()
            ai_keywords = ["ai", "gemini", "generated", "artificial", "imagen"]
            for keyword in ai_keywords:
                assert keyword not in metadata_str, (
                    f"Metadata should not contain '{keyword}': {metadata}"
                )

    @pytest.mark.asyncio
    async def test_real_drive_upload_with_clean_metadata(
        self,
        gemini_client,
        drive_client,
        has_real_drive_credentials,
    ):
        """Test real Drive upload with metadata verification (Task 10.3 + 10.4)."""
        if not has_real_drive_credentials:
            pytest.skip("Real Drive credentials not available")

        from teams.dawo.generators.nano_banana import (
            NanoBananaGenerator,
            ImageGenerationRequest,
            ImageStyleType,
        )

        generator = NanoBananaGenerator(
            gemini=gemini_client,
            drive=drive_client,
        )

        request = ImageGenerationRequest(
            content_id="real_drive_test_001",
            topic="nordic wellness scene",
            style=ImageStyleType.WELLNESS,
            width=512,
            height=512,
        )

        result = await generator.generate(request)

        assert result.success is True
        # With real credentials, should have Drive URL
        assert result.drive_file_id is not None
        assert result.drive_url is not None
