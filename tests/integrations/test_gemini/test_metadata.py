"""Unit tests for metadata stripping utilities.

Tests Task 9.5 of Story 3-5:
- Test metadata stripping with PIL
- Test validation of AI markers
- Test error handling when PIL unavailable
"""

import pytest
from pathlib import Path
from PIL import Image

from integrations.gemini.metadata import (
    strip_ai_metadata,
    validate_no_ai_markers,
    get_image_metadata,
    MetadataError,
)


@pytest.fixture
def sample_png_with_metadata(tmp_path: Path) -> Path:
    """Create a sample PNG with metadata."""
    img = Image.new("RGB", (100, 100), color="blue")

    # Add some metadata via PNG info
    from PIL import PngImagePlugin

    meta = PngImagePlugin.PngInfo()
    meta.add_text("Software", "Test Generator")
    meta.add_text("Description", "A test image")

    path = tmp_path / "with_metadata.png"
    img.save(path, pnginfo=meta)
    return path


@pytest.fixture
def sample_png_with_ai_markers(tmp_path: Path) -> Path:
    """Create a sample PNG with AI generation markers."""
    img = Image.new("RGB", (100, 100), color="red")

    from PIL import PngImagePlugin

    meta = PngImagePlugin.PngInfo()
    meta.add_text("Software", "Gemini AI Image Generator")
    meta.add_text("Generator", "AI generated content")
    meta.add_text("Comment", "Created with artificial intelligence")

    path = tmp_path / "ai_generated.png"
    img.save(path, pnginfo=meta)
    return path


@pytest.fixture
def clean_png(tmp_path: Path) -> Path:
    """Create a clean PNG without metadata."""
    img = Image.new("RGB", (100, 100), color="green")
    path = tmp_path / "clean.png"
    img.save(path)
    return path


class TestStripAiMetadata:
    """Test strip_ai_metadata function."""

    def test_strips_metadata_from_image(
        self,
        sample_png_with_metadata: Path,
    ):
        """Metadata is stripped from image."""
        # Verify metadata exists before
        with Image.open(sample_png_with_metadata) as img:
            assert len(img.info) > 0, "Test image should have metadata"

        # Strip metadata
        result = strip_ai_metadata(sample_png_with_metadata)

        # Verify metadata is gone
        with Image.open(result) as img:
            # PNG info should be empty or minimal after stripping
            # Note: Some basic info like mode may persist
            assert "Software" not in img.info
            assert "Description" not in img.info

    def test_strips_ai_markers(
        self,
        sample_png_with_ai_markers: Path,
    ):
        """AI generation markers are stripped."""
        result = strip_ai_metadata(sample_png_with_ai_markers)

        with Image.open(result) as img:
            # All AI-related metadata should be gone
            info_str = str(img.info).lower()
            assert "ai" not in info_str
            assert "gemini" not in info_str
            assert "generated" not in info_str

    def test_returns_output_path(
        self,
        sample_png_with_metadata: Path,
    ):
        """Returns the path to the cleaned image."""
        result = strip_ai_metadata(sample_png_with_metadata)

        assert result == sample_png_with_metadata
        assert result.exists()

    def test_custom_output_path(
        self,
        sample_png_with_metadata: Path,
        tmp_path: Path,
    ):
        """Can write to custom output path."""
        output = tmp_path / "output" / "cleaned.png"

        result = strip_ai_metadata(sample_png_with_metadata, output)

        assert result == output
        assert output.exists()
        # Original should still exist
        assert sample_png_with_metadata.exists()

    def test_preserves_image_content(
        self,
        sample_png_with_metadata: Path,
    ):
        """Image content is preserved after stripping."""
        # Get original dimensions
        with Image.open(sample_png_with_metadata) as img:
            original_size = img.size
            original_mode = img.mode

        strip_ai_metadata(sample_png_with_metadata)

        # Verify dimensions preserved
        with Image.open(sample_png_with_metadata) as img:
            assert img.size == original_size
            assert img.mode == original_mode

    def test_raises_on_invalid_file(self, tmp_path: Path):
        """Raises MetadataError for invalid image file."""
        invalid_file = tmp_path / "not_an_image.txt"
        invalid_file.write_text("This is not an image")

        with pytest.raises(MetadataError):
            strip_ai_metadata(invalid_file)

    def test_raises_on_missing_file(self, tmp_path: Path):
        """Raises MetadataError for missing file."""
        missing = tmp_path / "does_not_exist.png"

        with pytest.raises(MetadataError):
            strip_ai_metadata(missing)


class TestValidateNoAiMarkers:
    """Test validate_no_ai_markers function."""

    def test_clean_image_passes(self, clean_png: Path):
        """Clean image with no markers passes validation."""
        is_clean, issues = validate_no_ai_markers(clean_png)

        assert is_clean is True
        assert len(issues) == 0

    def test_detects_ai_software_tag(
        self,
        sample_png_with_ai_markers: Path,
    ):
        """Detects AI markers in Software tag."""
        is_clean, issues = validate_no_ai_markers(sample_png_with_ai_markers)

        assert is_clean is False
        assert len(issues) > 0
        # Should detect Gemini or AI in the markers
        issues_str = " ".join(issues).lower()
        assert "gemini" in issues_str or "ai" in issues_str

    def test_detects_various_ai_keywords(self, tmp_path: Path):
        """Detects various AI generation keywords."""
        ai_keywords = [
            "DALL-E",
            "Midjourney",
            "Stable Diffusion",
            "neural network",
        ]

        for keyword in ai_keywords:
            # Create image with this keyword
            img = Image.new("RGB", (50, 50), color="white")
            from PIL import PngImagePlugin

            meta = PngImagePlugin.PngInfo()
            meta.add_text("Generator", keyword)

            path = tmp_path / f"test_{keyword.replace(' ', '_')}.png"
            img.save(path, pnginfo=meta)

            is_clean, issues = validate_no_ai_markers(path)

            assert is_clean is False, f"Should detect '{keyword}'"

    def test_returns_specific_issues(
        self,
        sample_png_with_ai_markers: Path,
    ):
        """Returns specific issue descriptions."""
        is_clean, issues = validate_no_ai_markers(sample_png_with_ai_markers)

        assert len(issues) > 0
        # Issues should be descriptive
        for issue in issues:
            assert len(issue) > 5  # Not empty or trivial

    def test_raises_on_invalid_file(self, tmp_path: Path):
        """Raises MetadataError for invalid image file."""
        invalid_file = tmp_path / "not_an_image.txt"
        invalid_file.write_text("This is not an image")

        with pytest.raises(MetadataError):
            validate_no_ai_markers(invalid_file)


class TestGetImageMetadata:
    """Test get_image_metadata function."""

    def test_returns_metadata_dict(
        self,
        sample_png_with_metadata: Path,
    ):
        """Returns dictionary of metadata."""
        metadata = get_image_metadata(sample_png_with_metadata)

        assert isinstance(metadata, dict)
        assert "Software" in metadata or "Description" in metadata

    def test_empty_for_clean_image(self, clean_png: Path):
        """Returns minimal metadata for clean image."""
        metadata = get_image_metadata(clean_png)

        # Should be empty or have only basic info
        assert isinstance(metadata, dict)

    def test_raises_on_invalid_file(self, tmp_path: Path):
        """Raises MetadataError for invalid file."""
        invalid_file = tmp_path / "not_an_image.txt"
        invalid_file.write_text("Not an image")

        with pytest.raises(MetadataError):
            get_image_metadata(invalid_file)


class TestMetadataIntegration:
    """Integration tests for metadata workflow."""

    def test_strip_then_validate_workflow(
        self,
        sample_png_with_ai_markers: Path,
    ):
        """Full workflow: strip then validate."""
        # Image starts with AI markers
        is_clean_before, _ = validate_no_ai_markers(sample_png_with_ai_markers)
        assert is_clean_before is False

        # Strip the markers
        strip_ai_metadata(sample_png_with_ai_markers)

        # Now should be clean
        is_clean_after, issues = validate_no_ai_markers(sample_png_with_ai_markers)
        assert is_clean_after is True, f"Should be clean after stripping: {issues}"
