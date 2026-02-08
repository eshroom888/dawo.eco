"""Google Drive client for asset storage.

This module provides a Google Drive client for storing and retrieving
generated assets per FR47 requirements.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design
- Automatic folder structure creation
- All API calls wrapped with retry middleware
- Graceful error handling

Folder Structure:
- DAWO.ECO/Assets/Generated/ - AI images (Nano Banana)
- DAWO.ECO/Assets/Orshot/ - Branded graphics
- DAWO.ECO/Assets/Archive/ - Used assets with performance data
"""

import asyncio
import logging
import mimetypes
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload

from teams.dawo.middleware.retry import RetryConfig, RetryMiddleware, RetryResult

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Asset type classification for folder routing."""

    AI_IMAGE = "generated"  # Nano Banana AI images
    BRANDED_GRAPHIC = "orshot"  # Orshot branded graphics
    ARCHIVE = "archive"  # Used assets with performance data


# Mapping of AssetType to folder names
ASSET_TYPE_FOLDER_NAMES: dict[AssetType, str] = {
    AssetType.AI_IMAGE: "Generated",
    AssetType.BRANDED_GRAPHIC: "Orshot",
    AssetType.ARCHIVE: "Archive",
}


@dataclass
class DriveAsset:
    """Asset stored in Google Drive.

    Attributes:
        id: Google Drive file ID
        name: File name
        folder_id: Parent folder ID
        web_view_link: Web view URL
        download_link: Direct download URL
        mime_type: MIME type
        created_at: Creation timestamp
        metadata: Additional metadata (prompt, template, quality_score)
    """

    id: str
    name: str
    folder_id: str
    web_view_link: str
    download_link: str
    mime_type: str
    created_at: datetime
    metadata: dict[str, Any]


@runtime_checkable
class GoogleDriveClientProtocol(Protocol):
    """Protocol defining the Google Drive client interface.

    Any class implementing this protocol can be used as a Drive client.
    This allows for easy mocking and alternative implementations.
    """

    async def upload_asset(
        self,
        file_path: Path,
        asset_type: AssetType,
        metadata: dict[str, Any],
    ) -> DriveAsset:
        """Upload an asset to Google Drive.

        Args:
            file_path: Local path to the file
            asset_type: Type of asset (determines folder)
            metadata: Asset metadata (prompt, template, quality_score)

        Returns:
            DriveAsset with file info and links
        """
        ...

    async def get_asset(self, file_id: str) -> Optional[DriveAsset]:
        """Get asset by file ID.

        Args:
            file_id: Google Drive file ID

        Returns:
            DriveAsset if found, None otherwise
        """
        ...

    async def move_to_archive(
        self,
        file_id: str,
        performance_data: dict[str, Any],
    ) -> DriveAsset:
        """Move asset to archive with performance data.

        Args:
            file_id: Google Drive file ID
            performance_data: Engagement metrics, quality scores

        Returns:
            Updated DriveAsset in archive folder
        """
        ...


class GoogleDriveClient:
    """Google Drive client for asset storage.

    Implements GoogleDriveClientProtocol for type-safe injection.
    All API calls are wrapped with retry middleware for resilience.

    Attributes:
        _credentials_path: Path to service account JSON
        _root_folder_id: Root folder ID for DAWO.ECO
        _folder_ids: Cached folder IDs by asset type
        _retry_middleware: Retry middleware for API calls
    """

    # Google Drive API scope for file access
    SCOPES: list[str] = ["https://www.googleapis.com/auth/drive.file"]

    # Default retry configuration for Drive API
    DEFAULT_RETRY_CONFIG = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
        timeout=30.0,
        max_rate_limit_wait=300,
    )

    def __init__(
        self,
        credentials_path: str,
        root_folder_id: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        """Initialize Google Drive client.

        Args:
            credentials_path: Path to service account JSON file
            root_folder_id: Optional root folder ID (auto-creates if None)
            retry_config: Optional retry configuration

        Raises:
            ValueError: If credentials_path is empty
        """
        if not credentials_path:
            raise ValueError("credentials_path is required")

        self._credentials_path = credentials_path
        self._root_folder_id = root_folder_id
        self._retry_config = retry_config or self.DEFAULT_RETRY_CONFIG
        self._retry_middleware = RetryMiddleware(self._retry_config)
        self._folder_ids: dict[AssetType, str] = {}
        self._initialized = False
        self._service: Optional[Resource] = None
        self._lock = asyncio.Lock()

    def _authenticate(self) -> Resource:
        """Authenticate and return Drive service.

        Uses service account credentials for server-to-server access.
        Caches the service instance for reuse.

        Returns:
            Google Drive API service resource
        """
        if self._service is not None:
            return self._service

        credentials = service_account.Credentials.from_service_account_file(
            self._credentials_path,
            scopes=self.SCOPES,
        )
        self._service = build("drive", "v3", credentials=credentials)
        logger.info("Google Drive client authenticated successfully")
        return self._service

    async def _execute_api_call(
        self,
        api_call: Any,
        context: str,
    ) -> RetryResult:
        """Execute a Drive API call with retry middleware.

        Wraps synchronous Drive API calls in async execution
        with retry middleware for resilience.

        Args:
            api_call: Prepared API call (result of .execute() chain)
            context: Description for logging

        Returns:
            RetryResult with success/failure and response
        """
        async def execute():
            # Run synchronous API call in thread pool
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, api_call.execute)

        return await self._retry_middleware.execute_with_retry(execute, context)

    async def _find_or_create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> str:
        """Find existing folder or create new one.

        Uses check-then-create pattern to handle race conditions.
        Wrapped with retry middleware for resilience.

        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)

        Returns:
            Folder ID

        Raises:
            RuntimeError: If folder creation fails after retries
        """
        service = self._authenticate()

        # Build query for existing folder
        query = (
            f"name='{name}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )
        if parent_id:
            query += f" and '{parent_id}' in parents"

        # Search for existing folder
        list_call = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
        )

        result = await self._execute_api_call(
            list_call,
            f"find_folder:{name}",
        )

        if result.success and result.response:
            files = result.response.get("files", [])
            if files:
                folder_id = files[0]["id"]
                logger.debug("Found existing folder '%s': %s", name, folder_id)
                return folder_id

        # Create folder if not found
        file_metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        create_call = service.files().create(
            body=file_metadata,
            fields="id",
        )

        create_result = await self._execute_api_call(
            create_call,
            f"create_folder:{name}",
        )

        if create_result.success and create_result.response:
            folder_id = create_result.response["id"]
            logger.info("Created folder '%s': %s", name, folder_id)
            return folder_id

        # Handle failure
        error_msg = f"Failed to create folder '{name}': {create_result.last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def _ensure_folder_structure(self) -> None:
        """Create folder structure if it doesn't exist.

        Folder hierarchy:
        - DAWO.ECO/
          - Assets/
            - Generated/  (AI images from Nano Banana)
            - Orshot/     (Branded graphics)
            - Archive/    (Used assets with performance data)

        Uses lock to prevent concurrent initialization race conditions.
        """
        if self._initialized:
            return

        async with self._lock:
            # Double-check after acquiring lock
            if self._initialized:
                return

            logger.info("Initializing Google Drive folder structure")

            # Create or find root folder (DAWO.ECO)
            root_id = await self._find_or_create_folder(
                "DAWO.ECO",
                parent_id=self._root_folder_id,
            )

            # Create Assets folder
            assets_id = await self._find_or_create_folder("Assets", parent_id=root_id)

            # Create type-specific folders
            for asset_type in AssetType:
                folder_name = ASSET_TYPE_FOLDER_NAMES[asset_type]
                folder_id = await self._find_or_create_folder(
                    folder_name,
                    parent_id=assets_id,
                )
                self._folder_ids[asset_type] = folder_id
                logger.info("Folder %s ready: %s", folder_name, folder_id)

            self._initialized = True
            logger.info("Google Drive folder structure initialized")

    def _generate_filename(
        self,
        asset_type: AssetType,
        topic: str,
        extension: str,
    ) -> str:
        """Generate filename following pattern: {date}_{type}_{topic}_{id}.{ext}

        Sanitizes topic for filename safety.

        Args:
            asset_type: Type of asset
            topic: Content topic (will be sanitized)
            extension: File extension (without dot)

        Returns:
            Safe filename string

        Examples:
            - 20260207_generated_lionsmane_a1b2c3d4.png
            - 20260207_orshot_wellness_e5f6g7h8.jpg
        """
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        # Sanitize topic: lowercase, alphanumeric only, max 30 chars
        safe_topic = re.sub(r"[^a-z0-9]", "", topic.lower())[:30]
        if not safe_topic:
            safe_topic = "content"

        # Generate short unique ID
        short_id = str(uuid.uuid4())[:8]

        return f"{date_str}_{asset_type.value}_{safe_topic}_{short_id}.{extension}"

    async def upload_asset(
        self,
        file_path: Path,
        asset_type: AssetType,
        metadata: dict[str, Any],
    ) -> DriveAsset:
        """Upload an asset to Google Drive.

        Routes to correct folder based on asset_type.
        Stores metadata as custom file properties.

        Args:
            file_path: Local path to the file
            asset_type: Type of asset (determines folder)
            metadata: Asset metadata (prompt, template, quality_score)

        Returns:
            DriveAsset with file info and links

        Raises:
            FileNotFoundError: If file_path doesn't exist
            RuntimeError: If upload fails after retries
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        await self._ensure_folder_structure()

        service = self._authenticate()
        folder_id = self._folder_ids[asset_type]

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        # Generate filename
        topic = metadata.get("topic", "content")
        extension = file_path.suffix.lstrip(".")
        filename = self._generate_filename(asset_type, topic, extension)

        # Prepare metadata as properties
        properties: dict[str, str] = {
            "generation_date": datetime.now(timezone.utc).isoformat(),
            "quality_score": str(metadata.get("quality_score", "")),
        }
        if "prompt" in metadata:
            # Limit property size to 500 chars
            properties["prompt"] = str(metadata["prompt"])[:500]
        if "template_id" in metadata:
            properties["template_id"] = str(metadata["template_id"])

        file_metadata: dict[str, Any] = {
            "name": filename,
            "parents": [folder_id],
            "properties": properties,
        }

        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True,
        )

        create_call = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink, mimeType, createdTime, properties",
        )

        result = await self._execute_api_call(create_call, f"upload:{filename}")

        if result.success and result.response:
            file_data = result.response
            logger.info("Uploaded asset: %s -> %s", file_path.name, file_data["id"])
            return DriveAsset(
                id=file_data["id"],
                name=file_data["name"],
                folder_id=folder_id,
                web_view_link=file_data.get("webViewLink", ""),
                download_link=file_data.get("webContentLink", ""),
                mime_type=file_data["mimeType"],
                created_at=datetime.fromisoformat(
                    file_data["createdTime"].rstrip("Z")
                ).replace(tzinfo=timezone.utc),
                metadata=metadata,
            )

        error_msg = f"Failed to upload asset {file_path}: {result.last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def get_asset(self, file_id: str) -> Optional[DriveAsset]:
        """Get asset by file ID.

        Retrieves file with all metadata and parses custom properties.

        Args:
            file_id: Google Drive file ID

        Returns:
            DriveAsset if found, None otherwise
        """
        service = self._authenticate()

        get_call = service.files().get(
            fileId=file_id,
            fields="id, name, parents, webViewLink, webContentLink, mimeType, createdTime, properties",
        )

        result = await self._execute_api_call(get_call, f"get_asset:{file_id}")

        if not result.success:
            if result.last_error and "404" in str(result.last_error):
                logger.debug("Asset not found: %s", file_id)
            else:
                logger.warning("Failed to get asset %s: %s", file_id, result.last_error)
            return None

        if not result.response:
            return None

        file_data = result.response
        parents = file_data.get("parents", [])
        folder_id = parents[0] if parents else ""
        properties = file_data.get("properties", {})

        return DriveAsset(
            id=file_data["id"],
            name=file_data["name"],
            folder_id=folder_id,
            web_view_link=file_data.get("webViewLink", ""),
            download_link=file_data.get("webContentLink", ""),
            mime_type=file_data["mimeType"],
            created_at=datetime.fromisoformat(
                file_data["createdTime"].rstrip("Z")
            ).replace(tzinfo=timezone.utc),
            metadata=properties,
        )

    async def move_to_archive(
        self,
        file_id: str,
        performance_data: dict[str, Any],
    ) -> DriveAsset:
        """Move asset to archive with performance data.

        Preserves original metadata and appends performance metrics.

        Args:
            file_id: Google Drive file ID
            performance_data: Engagement metrics, conversions, etc.

        Returns:
            Updated DriveAsset in archive folder

        Raises:
            RuntimeError: If file not found or move fails
        """
        await self._ensure_folder_structure()

        service = self._authenticate()
        archive_folder_id = self._folder_ids[AssetType.ARCHIVE]

        # Get current file with metadata
        get_call = service.files().get(
            fileId=file_id,
            fields="id, name, parents, mimeType, createdTime, properties",
        )

        get_result = await self._execute_api_call(get_call, f"get_for_archive:{file_id}")

        if not get_result.success or not get_result.response:
            error_msg = f"Failed to get file for archive: {file_id}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        current = get_result.response

        # Build updated properties
        existing_props = current.get("properties", {})
        updated_props = {
            **existing_props,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "engagement_rate": str(performance_data.get("engagement_rate", "")),
            "conversions": str(performance_data.get("conversions", "")),
        }

        # Move to archive folder (remove from current parents, add to archive)
        current_parents = current.get("parents", [])

        update_call = service.files().update(
            fileId=file_id,
            addParents=archive_folder_id,
            removeParents=",".join(current_parents),
            body={"properties": updated_props},
            fields="id, name, webViewLink, webContentLink, mimeType, createdTime, properties",
        )

        update_result = await self._execute_api_call(
            update_call,
            f"move_to_archive:{file_id}",
        )

        if update_result.success and update_result.response:
            file_data = update_result.response
            logger.info("Moved asset to archive: %s", file_id)
            return DriveAsset(
                id=file_data["id"],
                name=file_data["name"],
                folder_id=archive_folder_id,
                web_view_link=file_data.get("webViewLink", ""),
                download_link=file_data.get("webContentLink", ""),
                mime_type=file_data["mimeType"],
                created_at=datetime.fromisoformat(
                    file_data["createdTime"].rstrip("Z")
                ).replace(tzinfo=timezone.utc),
                metadata={**existing_props, "performance": performance_data},
            )

        error_msg = f"Failed to move asset to archive: {file_id}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
