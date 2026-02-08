"""Unit tests for Google Drive client."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import re

from integrations.google_drive.client import (
    GoogleDriveClient,
    GoogleDriveClientProtocol,
    DriveAsset,
    AssetType,
    ASSET_TYPE_FOLDER_NAMES,
)
from teams.dawo.middleware.retry import RetryConfig, RetryResult


class TestGoogleDriveClientInit:
    """Test GoogleDriveClient initialization."""

    def test_init_requires_credentials_path(self):
        """GoogleDriveClient requires credentials_path."""
        with pytest.raises(ValueError, match="credentials_path is required"):
            GoogleDriveClient(credentials_path="")

    def test_init_with_valid_params(self, fake_credentials_file, retry_config):
        """GoogleDriveClient initializes with valid parameters."""
        with patch(
            "integrations.google_drive.client.service_account.Credentials.from_service_account_file"
        ):
            with patch("integrations.google_drive.client.build"):
                client = GoogleDriveClient(
                    credentials_path=fake_credentials_file,
                    retry_config=retry_config,
                )
                assert client._credentials_path == fake_credentials_file
                assert client._initialized is False
                assert client._folder_ids == {}

    def test_init_with_root_folder_id(self, fake_credentials_file):
        """GoogleDriveClient accepts optional root_folder_id."""
        with patch(
            "integrations.google_drive.client.service_account.Credentials.from_service_account_file"
        ):
            with patch("integrations.google_drive.client.build"):
                client = GoogleDriveClient(
                    credentials_path=fake_credentials_file,
                    root_folder_id="custom_root_123",
                )
                assert client._root_folder_id == "custom_root_123"

    def test_default_retry_config(self, fake_credentials_file):
        """Default retry config is applied when not provided."""
        with patch(
            "integrations.google_drive.client.service_account.Credentials.from_service_account_file"
        ):
            with patch("integrations.google_drive.client.build"):
                client = GoogleDriveClient(
                    credentials_path=fake_credentials_file,
                )
                assert client._retry_config.max_retries == 3
                assert client._retry_config.base_delay == 1.0


class TestFilenameGeneration:
    """Test _generate_filename method."""

    def test_filename_pattern(self, google_drive_client):
        """Filename follows pattern: {date}_{type}_{topic}_{id}.{ext}"""
        filename = google_drive_client._generate_filename(
            AssetType.AI_IMAGE,
            "lion's mane",
            "png",
        )

        # Pattern: YYYYMMDD_generated_sanitizedtopic_8charhex.png
        pattern = r"^\d{8}_generated_[a-z0-9]+_[a-f0-9]{8}\.png$"
        assert re.match(pattern, filename), f"Filename {filename} doesn't match pattern"

    def test_filename_sanitizes_topic(self, google_drive_client):
        """Topic is sanitized: lowercase, alphanumeric only."""
        filename = google_drive_client._generate_filename(
            AssetType.BRANDED_GRAPHIC,
            "Lion's Mane! @#$%",
            "jpg",
        )

        # Should only contain lowercase alphanumeric
        assert "Lion" not in filename
        assert "!" not in filename
        assert "lionsmane" in filename

    def test_filename_limits_topic_length(self, google_drive_client):
        """Topic is truncated to 30 characters."""
        long_topic = "a" * 50
        filename = google_drive_client._generate_filename(
            AssetType.AI_IMAGE,
            long_topic,
            "png",
        )

        # Extract topic from filename
        parts = filename.split("_")
        topic_part = parts[2]  # {date}_{type}_{topic}_{id}.{ext}
        assert len(topic_part) <= 30

    def test_filename_empty_topic_defaults(self, google_drive_client):
        """Empty topic defaults to 'content'."""
        filename = google_drive_client._generate_filename(
            AssetType.AI_IMAGE,
            "!@#$%",  # Only special chars, becomes empty
            "png",
        )

        assert "_content_" in filename

    def test_filename_has_unique_id(self, google_drive_client):
        """Each filename has unique 8-char ID."""
        filename1 = google_drive_client._generate_filename(
            AssetType.AI_IMAGE, "test", "png"
        )
        filename2 = google_drive_client._generate_filename(
            AssetType.AI_IMAGE, "test", "png"
        )

        # Extract IDs
        id1 = filename1.split("_")[-1].split(".")[0]
        id2 = filename2.split("_")[-1].split(".")[0]

        assert id1 != id2

    def test_filename_asset_types(self, google_drive_client):
        """Different asset types produce correct type prefix."""
        for asset_type in AssetType:
            filename = google_drive_client._generate_filename(
                asset_type, "test", "png"
            )
            assert f"_{asset_type.value}_" in filename


class TestFolderStructure:
    """Test folder structure creation."""

    @pytest.mark.asyncio
    async def test_ensure_folder_structure_creates_folders(
        self, google_drive_client, mock_drive_service
    ):
        """_ensure_folder_structure creates all required folders."""
        # Mock folder creation responses
        folder_ids = {
            "DAWO.ECO": "id_dawo_eco",
            "Assets": "id_assets",
            "Generated": "id_generated",
            "Orshot": "id_orshot",
            "Archive": "id_archive",
        }

        call_count = 0

        def create_side_effect(**kwargs):
            nonlocal call_count
            body = kwargs.get("body", {})
            name = body.get("name", f"folder_{call_count}")
            result = MagicMock()
            result.execute.return_value = {"id": folder_ids.get(name, f"id_{call_count}")}
            call_count += 1
            return result

        mock_drive_service.files().create.side_effect = create_side_effect

        await google_drive_client._ensure_folder_structure()

        assert google_drive_client._initialized is True
        assert len(google_drive_client._folder_ids) == 3  # Generated, Orshot, Archive

    @pytest.mark.asyncio
    async def test_ensure_folder_structure_only_once(
        self, google_drive_client, mock_drive_service
    ):
        """Folder structure is only created once."""
        mock_drive_service.files().create().execute.return_value = {"id": "folder_123"}

        await google_drive_client._ensure_folder_structure()
        call_count_after_first = mock_drive_service.files().create.call_count

        await google_drive_client._ensure_folder_structure()
        call_count_after_second = mock_drive_service.files().create.call_count

        assert call_count_after_first == call_count_after_second

    @pytest.mark.asyncio
    async def test_find_or_create_folder_finds_existing(
        self, fake_credentials_file, retry_config
    ):
        """_find_or_create_folder returns existing folder ID when folder exists."""
        mock_service = MagicMock()

        # Track if create was called
        create_called = False

        def mock_create(**kwargs):
            nonlocal create_called
            create_called = True
            result = MagicMock()
            result.execute.return_value = {"id": "new_folder"}
            return result

        # Mock list to return existing folder
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "existing_folder_id", "name": "TestFolder"}]
        }
        mock_service.files().create = mock_create

        with patch(
            "integrations.google_drive.client.service_account.Credentials.from_service_account_file"
        ):
            with patch(
                "integrations.google_drive.client.build", return_value=mock_service
            ):
                client = GoogleDriveClient(
                    credentials_path=fake_credentials_file,
                    retry_config=retry_config,
                )
                client._service = mock_service

                folder_id = await client._find_or_create_folder("TestFolder")

        assert folder_id == "existing_folder_id"
        # create should not be called when folder exists
        assert create_called is False


class TestUploadAsset:
    """Test upload_asset method."""

    @pytest.mark.asyncio
    async def test_upload_asset_success(
        self,
        google_drive_client,
        mock_drive_service,
        sample_image_file,
        mock_file_upload_response,
    ):
        """Successfully upload an asset."""
        # Pre-initialize folder structure
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {
            AssetType.AI_IMAGE: "folder_generated",
            AssetType.BRANDED_GRAPHIC: "folder_orshot",
            AssetType.ARCHIVE: "folder_archive",
        }

        mock_drive_service.files().create().execute.return_value = mock_file_upload_response

        result = await google_drive_client.upload_asset(
            file_path=sample_image_file,
            asset_type=AssetType.AI_IMAGE,
            metadata={"topic": "lion's mane", "quality_score": 8.5},
        )

        assert isinstance(result, DriveAsset)
        assert result.id == "file_id_abc123"
        assert result.folder_id == "folder_generated"
        assert result.mime_type == "image/png"

    @pytest.mark.asyncio
    async def test_upload_asset_routes_to_correct_folder(
        self,
        google_drive_client,
        mock_drive_service,
        sample_image_file,
        mock_file_upload_response,
    ):
        """Upload routes to correct folder based on AssetType."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {
            AssetType.AI_IMAGE: "folder_generated",
            AssetType.BRANDED_GRAPHIC: "folder_orshot",
            AssetType.ARCHIVE: "folder_archive",
        }

        mock_drive_service.files().create().execute.return_value = mock_file_upload_response

        # Test each asset type
        for asset_type, expected_folder in [
            (AssetType.AI_IMAGE, "folder_generated"),
            (AssetType.BRANDED_GRAPHIC, "folder_orshot"),
        ]:
            result = await google_drive_client.upload_asset(
                file_path=sample_image_file,
                asset_type=asset_type,
                metadata={"topic": "test"},
            )
            assert result.folder_id == expected_folder

    @pytest.mark.asyncio
    async def test_upload_asset_stores_metadata(
        self,
        google_drive_client,
        mock_drive_service,
        sample_image_file,
        mock_file_upload_response,
    ):
        """Upload stores metadata as file properties."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {AssetType.AI_IMAGE: "folder_generated"}

        captured_body = None

        def capture_create(**kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("body", {})
            result = MagicMock()
            result.execute.return_value = mock_file_upload_response
            return result

        mock_drive_service.files().create.side_effect = capture_create

        await google_drive_client.upload_asset(
            file_path=sample_image_file,
            asset_type=AssetType.AI_IMAGE,
            metadata={
                "topic": "test",
                "quality_score": 9.0,
                "prompt": "A stunning mushroom",
                "template_id": "template_123",
            },
        )

        assert captured_body is not None
        assert "properties" in captured_body
        assert captured_body["properties"]["quality_score"] == "9.0"
        assert captured_body["properties"]["template_id"] == "template_123"

    @pytest.mark.asyncio
    async def test_upload_asset_file_not_found(self, google_drive_client):
        """Upload raises FileNotFoundError for missing file."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {AssetType.AI_IMAGE: "folder_generated"}

        with pytest.raises(FileNotFoundError, match="File not found"):
            await google_drive_client.upload_asset(
                file_path=Path("/nonexistent/file.png"),
                asset_type=AssetType.AI_IMAGE,
                metadata={},
            )

    @pytest.mark.asyncio
    async def test_upload_asset_truncates_long_prompt(
        self,
        google_drive_client,
        mock_drive_service,
        sample_image_file,
        mock_file_upload_response,
    ):
        """Upload truncates prompt to 500 chars."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {AssetType.AI_IMAGE: "folder_generated"}

        captured_body = None

        def capture_create(**kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("body", {})
            result = MagicMock()
            result.execute.return_value = mock_file_upload_response
            return result

        mock_drive_service.files().create.side_effect = capture_create

        long_prompt = "x" * 1000

        await google_drive_client.upload_asset(
            file_path=sample_image_file,
            asset_type=AssetType.AI_IMAGE,
            metadata={"topic": "test", "prompt": long_prompt},
        )

        assert len(captured_body["properties"]["prompt"]) == 500


class TestGetAsset:
    """Test get_asset method."""

    @pytest.mark.asyncio
    async def test_get_asset_success(
        self, google_drive_client, mock_drive_service, mock_file_get_response
    ):
        """Successfully retrieve an asset by ID."""
        mock_drive_service.files().get().execute.return_value = mock_file_get_response

        result = await google_drive_client.get_asset("file_id_abc123")

        assert result is not None
        assert result.id == "file_id_abc123"
        assert result.folder_id == "folder_generated"
        assert result.metadata["quality_score"] == "8.5"

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, google_drive_client, mock_drive_service):
        """Return None when asset not found."""
        # Simulate retry result with 404 error
        google_drive_client._retry_middleware = MagicMock()
        google_drive_client._retry_middleware.execute_with_retry = AsyncMock(
            return_value=RetryResult(
                success=False,
                attempts=1,
                last_error="404 File not found",
            )
        )

        result = await google_drive_client.get_asset("nonexistent_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_asset_parses_metadata(
        self, google_drive_client, mock_drive_service
    ):
        """Get asset correctly parses custom properties."""
        mock_drive_service.files().get().execute.return_value = {
            "id": "file_123",
            "name": "test.png",
            "parents": ["folder_123"],
            "webViewLink": "https://link",
            "webContentLink": "https://download",
            "mimeType": "image/png",
            "createdTime": "2026-02-07T12:00:00.000Z",
            "properties": {
                "generation_date": "2026-02-07T12:00:00+00:00",
                "quality_score": "8.5",
                "prompt": "test prompt",
            },
        }

        result = await google_drive_client.get_asset("file_123")

        assert result.metadata["quality_score"] == "8.5"
        assert result.metadata["prompt"] == "test prompt"


class TestMoveToArchive:
    """Test move_to_archive method."""

    @pytest.mark.asyncio
    async def test_move_to_archive_success(
        self, google_drive_client, mock_drive_service
    ):
        """Successfully move asset to archive."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {
            AssetType.AI_IMAGE: "folder_generated",
            AssetType.BRANDED_GRAPHIC: "folder_orshot",
            AssetType.ARCHIVE: "folder_archive",
        }

        # Mock get file
        mock_drive_service.files().get().execute.return_value = {
            "id": "file_123",
            "name": "test.png",
            "parents": ["folder_generated"],
            "mimeType": "image/png",
            "createdTime": "2026-02-07T12:00:00.000Z",
            "properties": {"quality_score": "8.5"},
        }

        # Mock update
        mock_drive_service.files().update().execute.return_value = {
            "id": "file_123",
            "name": "test.png",
            "webViewLink": "https://link",
            "webContentLink": "https://download",
            "mimeType": "image/png",
            "createdTime": "2026-02-07T12:00:00.000Z",
            "properties": {
                "quality_score": "8.5",
                "archived_at": "2026-02-07T14:00:00+00:00",
                "engagement_rate": "0.05",
            },
        }

        result = await google_drive_client.move_to_archive(
            file_id="file_123",
            performance_data={"engagement_rate": 0.05, "conversions": 10},
        )

        assert result.folder_id == "folder_archive"
        assert result.metadata["performance"]["engagement_rate"] == 0.05

    @pytest.mark.asyncio
    async def test_move_to_archive_preserves_metadata(
        self, google_drive_client, mock_drive_service
    ):
        """Move preserves original metadata and adds performance."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {AssetType.ARCHIVE: "folder_archive"}

        captured_body = None

        def capture_update(**kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("body", {})
            result = MagicMock()
            result.execute.return_value = {
                "id": "file_123",
                "name": "test.png",
                "webViewLink": "",
                "webContentLink": "",
                "mimeType": "image/png",
                "createdTime": "2026-02-07T12:00:00.000Z",
                "properties": {},
            }
            return result

        mock_drive_service.files().get().execute.return_value = {
            "id": "file_123",
            "name": "test.png",
            "parents": ["old_folder"],
            "mimeType": "image/png",
            "createdTime": "2026-02-07T12:00:00.000Z",
            "properties": {"original_prop": "value"},
        }
        mock_drive_service.files().update.side_effect = capture_update

        await google_drive_client.move_to_archive(
            file_id="file_123",
            performance_data={"engagement_rate": 0.05},
        )

        assert captured_body is not None
        props = captured_body["properties"]
        assert props["original_prop"] == "value"
        assert "archived_at" in props
        assert props["engagement_rate"] == "0.05"


class TestRetryBehavior:
    """Test retry behavior with mocked failures."""

    @pytest.mark.asyncio
    async def test_retry_on_api_failure(
        self, google_drive_client, mock_drive_service, sample_image_file
    ):
        """Verify retry attempts are made on API failure."""
        google_drive_client._initialized = True
        google_drive_client._folder_ids = {AssetType.AI_IMAGE: "folder_generated"}

        # Mock retry middleware to return failure
        google_drive_client._retry_middleware = MagicMock()
        google_drive_client._retry_middleware.execute_with_retry = AsyncMock(
            return_value=RetryResult(
                success=False,
                attempts=3,
                last_error="Connection timeout",
                is_incomplete=True,
            )
        )

        with pytest.raises(RuntimeError, match="Failed to upload"):
            await google_drive_client.upload_asset(
                file_path=sample_image_file,
                asset_type=AssetType.AI_IMAGE,
                metadata={},
            )


class TestAssetTypeMapping:
    """Test AssetType enum and folder mapping."""

    def test_asset_type_values(self):
        """AssetType values match expected strings."""
        assert AssetType.AI_IMAGE.value == "generated"
        assert AssetType.BRANDED_GRAPHIC.value == "orshot"
        assert AssetType.ARCHIVE.value == "archive"

    def test_folder_name_mapping(self):
        """ASSET_TYPE_FOLDER_NAMES maps correctly."""
        assert ASSET_TYPE_FOLDER_NAMES[AssetType.AI_IMAGE] == "Generated"
        assert ASSET_TYPE_FOLDER_NAMES[AssetType.BRANDED_GRAPHIC] == "Orshot"
        assert ASSET_TYPE_FOLDER_NAMES[AssetType.ARCHIVE] == "Archive"


class TestDriveAssetDataclass:
    """Test DriveAsset dataclass."""

    def test_drive_asset_creation(self):
        """DriveAsset can be created with all fields."""
        asset = DriveAsset(
            id="file_123",
            name="test.png",
            folder_id="folder_123",
            web_view_link="https://view",
            download_link="https://download",
            mime_type="image/png",
            created_at=datetime(2026, 2, 7, 12, 0, 0, tzinfo=timezone.utc),
            metadata={"quality_score": 8.5},
        )

        assert asset.id == "file_123"
        assert asset.metadata["quality_score"] == 8.5


class TestProtocolCompliance:
    """Test GoogleDriveClientProtocol compliance."""

    def test_client_implements_protocol(self, google_drive_client):
        """GoogleDriveClient implements GoogleDriveClientProtocol."""
        assert isinstance(google_drive_client, GoogleDriveClientProtocol)

    def test_protocol_methods_exist(self, google_drive_client):
        """Client has all protocol methods."""
        assert hasattr(google_drive_client, "upload_asset")
        assert hasattr(google_drive_client, "get_asset")
        assert hasattr(google_drive_client, "move_to_archive")
        assert callable(google_drive_client.upload_asset)
        assert callable(google_drive_client.get_asset)
        assert callable(google_drive_client.move_to_archive)
