"""Integration tests for Google Drive client.

These tests require real Google Drive API credentials and are skipped
unless GOOGLE_DRIVE_INTEGRATION_TEST=1 environment variable is set.

To run integration tests:
    GOOGLE_DRIVE_INTEGRATION_TEST=1 pytest tests/integrations/test_google_drive/test_integration.py -v

Required environment variables:
    - GOOGLE_DRIVE_CREDENTIALS_PATH: Path to service account JSON
    - GOOGLE_DRIVE_ROOT_FOLDER_ID: (Optional) Root folder ID for tests
"""

import os
import pytest
from pathlib import Path

from integrations.google_drive.client import (
    GoogleDriveClient,
    AssetType,
    DriveAsset,
)

# Skip all tests in this module unless integration test env var is set
pytestmark = pytest.mark.skipif(
    os.environ.get("GOOGLE_DRIVE_INTEGRATION_TEST") != "1",
    reason="Integration tests disabled. Set GOOGLE_DRIVE_INTEGRATION_TEST=1 to run.",
)


@pytest.fixture
def credentials_path():
    """Get credentials path from environment."""
    path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_PATH")
    if not path:
        pytest.skip("GOOGLE_DRIVE_CREDENTIALS_PATH not set")
    if not Path(path).exists():
        pytest.skip(f"Credentials file not found: {path}")
    return path


@pytest.fixture
def root_folder_id():
    """Get optional root folder ID from environment."""
    return os.environ.get("GOOGLE_DRIVE_ROOT_FOLDER_ID")


@pytest.fixture
async def drive_client(credentials_path, root_folder_id):
    """Create real Google Drive client for integration tests."""
    client = GoogleDriveClient(
        credentials_path=credentials_path,
        root_folder_id=root_folder_id,
    )
    return client


@pytest.fixture
def sample_test_image(tmp_path):
    """Create a sample PNG image for upload tests."""
    image_file = tmp_path / "integration_test_image.png"
    # Minimal valid PNG
    png_data = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk header
        b"\x00\x00\x00\x01"  # Width: 1
        b"\x00\x00\x00\x01"  # Height: 1
        b"\x08\x02"  # Bit depth: 8, Color type: 2 (RGB)
        b"\x00\x00\x00"  # Compression, filter, interlace
        b"\x90wS\xde"  # CRC
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"  # IDAT
        b"\x00\x00\x00\x00IEND\xaeB`\x82"  # IEND
    )
    image_file.write_bytes(png_data)
    return image_file


class TestIntegrationFolderCreation:
    """Test folder creation on real Google Drive."""

    @pytest.mark.asyncio
    async def test_folder_structure_created_on_first_upload(
        self, drive_client, sample_test_image
    ):
        """Folder structure is created automatically on first upload."""
        # This will trigger _ensure_folder_structure
        result = await drive_client.upload_asset(
            file_path=sample_test_image,
            asset_type=AssetType.AI_IMAGE,
            metadata={"topic": "integration_test", "quality_score": 7.5},
        )

        # Verify structure was created
        assert drive_client._initialized is True
        assert AssetType.AI_IMAGE in drive_client._folder_ids
        assert AssetType.BRANDED_GRAPHIC in drive_client._folder_ids
        assert AssetType.ARCHIVE in drive_client._folder_ids

        # Cleanup: Delete the uploaded file
        service = drive_client._authenticate()
        service.files().delete(fileId=result.id).execute()


class TestIntegrationUpload:
    """Test file upload to real Google Drive."""

    @pytest.mark.asyncio
    async def test_upload_and_retrieve(self, drive_client, sample_test_image):
        """Upload a file and retrieve it by ID."""
        # Upload
        uploaded = await drive_client.upload_asset(
            file_path=sample_test_image,
            asset_type=AssetType.AI_IMAGE,
            metadata={
                "topic": "integration_test",
                "quality_score": 8.0,
                "prompt": "Test prompt for integration",
            },
        )

        assert isinstance(uploaded, DriveAsset)
        assert uploaded.id is not None
        assert uploaded.web_view_link != ""
        assert uploaded.mime_type == "image/png"

        # Retrieve
        retrieved = await drive_client.get_asset(uploaded.id)

        assert retrieved is not None
        assert retrieved.id == uploaded.id
        assert retrieved.name == uploaded.name

        # Cleanup
        service = drive_client._authenticate()
        service.files().delete(fileId=uploaded.id).execute()

    @pytest.mark.asyncio
    async def test_upload_metadata_stored(self, drive_client, sample_test_image):
        """Upload stores and retrieves metadata correctly."""
        uploaded = await drive_client.upload_asset(
            file_path=sample_test_image,
            asset_type=AssetType.BRANDED_GRAPHIC,
            metadata={
                "topic": "metadata_test",
                "quality_score": 9.5,
                "template_id": "template_abc123",
            },
        )

        # Retrieve and check metadata
        retrieved = await drive_client.get_asset(uploaded.id)

        assert retrieved is not None
        assert "quality_score" in retrieved.metadata
        assert retrieved.metadata["quality_score"] == "9.5"
        assert retrieved.metadata["template_id"] == "template_abc123"

        # Cleanup
        service = drive_client._authenticate()
        service.files().delete(fileId=uploaded.id).execute()


class TestIntegrationArchive:
    """Test archive workflow on real Google Drive."""

    @pytest.mark.asyncio
    async def test_move_to_archive_workflow(self, drive_client, sample_test_image):
        """Complete archive workflow: upload, move to archive, verify."""
        # Step 1: Upload to Generated folder
        uploaded = await drive_client.upload_asset(
            file_path=sample_test_image,
            asset_type=AssetType.AI_IMAGE,
            metadata={"topic": "archive_test", "quality_score": 8.0},
        )

        original_folder = uploaded.folder_id
        assert original_folder == drive_client._folder_ids[AssetType.AI_IMAGE]

        # Step 2: Move to archive with performance data
        archived = await drive_client.move_to_archive(
            file_id=uploaded.id,
            performance_data={
                "engagement_rate": 0.05,
                "conversions": 25,
                "impressions": 1000,
            },
        )

        # Verify moved to archive folder
        assert archived.folder_id == drive_client._folder_ids[AssetType.ARCHIVE]
        assert archived.id == uploaded.id

        # Verify performance data preserved
        assert archived.metadata["performance"]["engagement_rate"] == 0.05
        assert archived.metadata["performance"]["conversions"] == 25

        # Step 3: Retrieve and verify
        retrieved = await drive_client.get_asset(archived.id)
        assert retrieved is not None
        assert "archived_at" in retrieved.metadata

        # Cleanup
        service = drive_client._authenticate()
        service.files().delete(fileId=archived.id).execute()


class TestIntegrationErrorHandling:
    """Test error handling with real API."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, drive_client):
        """get_asset returns None for nonexistent file."""
        result = await drive_client.get_asset("nonexistent_file_id_12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_upload_nonexistent_file(self, drive_client):
        """upload_asset raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            await drive_client.upload_asset(
                file_path=Path("/nonexistent/path/file.png"),
                asset_type=AssetType.AI_IMAGE,
                metadata={},
            )
