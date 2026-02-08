"""Constants for Asset Usage Tracking.

Defines folder paths, weight configurations, and thresholds.
"""

# Google Drive folder structure (from project-context.md)
ASSET_FOLDERS: dict[str, str] = {
    "generated": "DAWO.ECO/Assets/Generated/",     # Nano Banana AI images
    "orshot": "DAWO.ECO/Assets/Orshot/",           # Branded graphics
    "archive": "DAWO.ECO/Assets/Archive/",         # Used assets + performance
}

# Default unused days threshold for suggestions
DEFAULT_UNUSED_DAYS_THRESHOLD: int = 30
