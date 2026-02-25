"""Evidence Collection Configuration (Story 6-8, Task 1).

Frozen dataclass for evidence collection settings.
Loaded via dependency injection from config/dawo_evidence_collection.json.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceCollectionConfig:
    """Configuration for evidence screenshot collection.

    Attributes:
        enabled: Whether evidence collection is active.
        batch_size: Max violations to process per run.
        viewport_width: Browser viewport width in pixels.
        viewport_height: Browser viewport height in pixels.
        timeout_seconds: Page load timeout in seconds.
        max_concurrent_captures: Semaphore limit for concurrent pages.
        full_page: Whether to capture full scrollable page.
        screenshot_format: Image format ('png' or 'jpeg').
        storage_base_path: Base directory for screenshot storage.
        chromium_args: Command-line args for Chromium launch.
        instagram_embed_template: URL template for Instagram embeds.
        timestamp_banner_enabled: Whether to inject timestamp overlay.
        wait_until: Playwright page.goto wait strategy.
    """

    enabled: bool = True
    batch_size: int = 20
    viewport_width: int = 1280
    viewport_height: int = 900
    timeout_seconds: int = 30
    max_concurrent_captures: int = 3
    full_page: bool = True
    screenshot_format: str = "png"
    storage_base_path: str = "evidence/screenshots"
    chromium_args: list[str] = field(
        default_factory=lambda: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    instagram_embed_template: str = "https://www.instagram.com/p/{shortcode}/embed/"
    timestamp_banner_enabled: bool = True
    wait_until: str = "networkidle"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.viewport_width <= 0:
            raise ValueError("viewport_width must be positive")
        if self.viewport_height <= 0:
            raise ValueError("viewport_height must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not (1 <= self.max_concurrent_captures <= 10):
            raise ValueError("max_concurrent_captures must be between 1 and 10")
        if self.screenshot_format not in ("png", "jpeg"):
            raise ValueError("screenshot_format must be 'png' or 'jpeg'")
        if not self.storage_base_path:
            raise ValueError("storage_base_path must not be empty")


def build_evidence_collection_config(data: dict) -> EvidenceCollectionConfig:
    """Build EvidenceCollectionConfig from a JSON-compatible dict.

    Args:
        data: Configuration dictionary (e.g., from JSON file).

    Returns:
        Validated EvidenceCollectionConfig instance.
    """
    return EvidenceCollectionConfig(
        enabled=data.get("enabled", True),
        batch_size=data.get("batch_size", 20),
        viewport_width=data.get("viewport_width", 1280),
        viewport_height=data.get("viewport_height", 900),
        timeout_seconds=data.get("timeout_seconds", 30),
        max_concurrent_captures=data.get("max_concurrent_captures", 3),
        full_page=data.get("full_page", True),
        screenshot_format=data.get("screenshot_format", "png"),
        storage_base_path=data.get("storage_base_path", "evidence/screenshots"),
        chromium_args=data.get(
            "chromium_args",
            ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        ),
        instagram_embed_template=data.get(
            "instagram_embed_template",
            "https://www.instagram.com/p/{shortcode}/embed/",
        ),
        timestamp_banner_enabled=data.get("timestamp_banner_enabled", True),
        wait_until=data.get("wait_until", "networkidle"),
    )


__all__ = [
    "EvidenceCollectionConfig",
    "build_evidence_collection_config",
]
