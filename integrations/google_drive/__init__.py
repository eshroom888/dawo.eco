"""Google Drive integration module.

Provides asset storage and retrieval for generated content.
"""

from integrations.google_drive.client import (
    GoogleDriveClient,
    GoogleDriveClientProtocol,
    DriveAsset,
    AssetType,
)

__all__ = [
    "GoogleDriveClient",
    "GoogleDriveClientProtocol",
    "DriveAsset",
    "AssetType",
]
