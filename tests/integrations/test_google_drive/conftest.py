"""Test fixtures for Google Drive integration tests."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from teams.dawo.middleware.retry import RetryConfig, RetryResult


@pytest.fixture
def retry_config():
    """Default retry config for tests (fast execution)."""
    return RetryConfig(
        max_retries=3,
        base_delay=0.01,  # Fast tests
        backoff_multiplier=2.0,
        timeout=5.0,
    )


@pytest.fixture
def mock_drive_service():
    """Mock Google Drive API service for unit tests."""
    service = MagicMock()

    # Default: folder search returns empty (folder doesn't exist)
    service.files().list().execute.return_value = {"files": []}

    # Default: folder creation returns success
    service.files().create().execute.return_value = {
        "id": "mock_folder_id_123",
    }

    return service


@pytest.fixture
def mock_drive_service_with_folders():
    """Mock service with pre-existing folder structure."""
    service = MagicMock()

    # Define folder structure
    folders = {
        "DAWO.ECO": "folder_dawo_eco",
        "Assets": "folder_assets",
        "Generated": "folder_generated",
        "Orshot": "folder_orshot",
        "Archive": "folder_archive",
    }

    def list_side_effect(**kwargs):
        result = MagicMock()
        query = kwargs.get("q", "")

        for name, folder_id in folders.items():
            if f"name='{name}'" in query:
                result.execute.return_value = {
                    "files": [{"id": folder_id, "name": name}]
                }
                return result

        result.execute.return_value = {"files": []}
        return result

    service.files().list.side_effect = list_side_effect

    return service


@pytest.fixture
def mock_file_upload_response():
    """Mock response for successful file upload."""
    return {
        "id": "file_id_abc123",
        "name": "20260207_generated_lionsmane_a1b2c3d4.png",
        "webViewLink": "https://drive.google.com/file/d/file_id_abc123/view",
        "webContentLink": "https://drive.google.com/uc?id=file_id_abc123&export=download",
        "mimeType": "image/png",
        "createdTime": "2026-02-07T12:00:00.000Z",
        "properties": {
            "generation_date": "2026-02-07T12:00:00+00:00",
            "quality_score": "8.5",
            "prompt": "A beautiful lion's mane mushroom",
        },
    }


@pytest.fixture
def mock_file_get_response():
    """Mock response for file get."""
    return {
        "id": "file_id_abc123",
        "name": "20260207_generated_lionsmane_a1b2c3d4.png",
        "parents": ["folder_generated"],
        "webViewLink": "https://drive.google.com/file/d/file_id_abc123/view",
        "webContentLink": "https://drive.google.com/uc?id=file_id_abc123&export=download",
        "mimeType": "image/png",
        "createdTime": "2026-02-07T12:00:00.000Z",
        "properties": {
            "generation_date": "2026-02-07T12:00:00+00:00",
            "quality_score": "8.5",
        },
    }


@pytest.fixture
def sample_image_file(tmp_path):
    """Create a sample image file for upload tests."""
    image_file = tmp_path / "test_image.png"
    # Write minimal PNG header for valid file
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return image_file


@pytest.fixture
def sample_jpg_file(tmp_path):
    """Create a sample JPG file for MIME type tests."""
    jpg_file = tmp_path / "test_image.jpg"
    # Write minimal JPEG header
    jpg_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return jpg_file


@pytest.fixture
def fake_credentials_file(tmp_path):
    """Create a fake service account credentials file."""
    creds_file = tmp_path / "service_account.json"
    creds_file.write_text(
        """{
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA0Z...\\n-----END RSA PRIVATE KEY-----\\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }"""
    )
    return str(creds_file)


@pytest.fixture
def google_drive_client(mock_drive_service, fake_credentials_file, retry_config):
    """GoogleDriveClient with mocked service for unit tests."""
    with patch(
        "integrations.google_drive.client.service_account.Credentials.from_service_account_file"
    ):
        with patch(
            "integrations.google_drive.client.build", return_value=mock_drive_service
        ):
            from integrations.google_drive.client import GoogleDriveClient

            client = GoogleDriveClient(
                credentials_path=fake_credentials_file,
                retry_config=retry_config,
            )
            # Pre-inject the mocked service
            client._service = mock_drive_service
            return client
