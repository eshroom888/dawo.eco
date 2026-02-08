"""Orshot client for branded graphics generation.

This module provides an Orshot client for generating branded graphics
using Canva templates per FR10 requirements.

Architecture Compliance:
- Configuration injected via constructor
- Async-first design
- RetryableHttpClient for all API calls (retry middleware wrapped)
- Graceful error handling with logging
- 60 second timeout per story requirements
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from teams.dawo.middleware.retry import RetryConfig, RetryResult
from teams.dawo.middleware.http_client import RetryableHttpClient

logger = logging.getLogger(__name__)


@dataclass
class OrshotTemplate:
    """Orshot template imported from Canva.

    Attributes:
        id: Template ID in Orshot
        name: Template name
        canva_id: Original Canva template ID
        variables: List of variable names that can be injected
        dimensions: Image dimensions (width, height)
    """

    id: str
    name: str
    canva_id: str
    variables: list[str]
    dimensions: tuple[int, int]


@dataclass
class GeneratedGraphic:
    """Generated graphic from Orshot.

    Attributes:
        id: Generation ID
        template_id: Template used
        image_url: Generated image URL
        local_path: Local path if downloaded
        variables_used: Variables injected into template
        created_at: Generation timestamp
    """

    id: str
    template_id: str
    image_url: str
    local_path: Optional[Path]
    variables_used: dict[str, str]
    created_at: datetime


@runtime_checkable
class OrshotClientProtocol(Protocol):
    """Protocol defining the Orshot client interface.

    Any class implementing this protocol can be used as an Orshot client.
    This allows for easy mocking and alternative implementations.
    """

    async def list_templates(self) -> list[OrshotTemplate]:
        """List available templates.

        Returns:
            List of available templates
        """
        ...

    async def generate_graphic(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> GeneratedGraphic:
        """Generate a graphic from template.

        Args:
            template_id: Template ID to use
            variables: Variable values to inject

        Returns:
            GeneratedGraphic with image URL
        """
        ...

    async def download_graphic(
        self,
        graphic: GeneratedGraphic,
        output_path: Path,
    ) -> Path:
        """Download generated graphic to local path.

        Args:
            graphic: Generated graphic to download
            output_path: Local path to save to

        Returns:
            Path to downloaded file
        """
        ...


class OrshotClient:
    """Orshot client for branded graphics generation.

    Implements OrshotClientProtocol for type-safe injection.
    All API calls are wrapped with retry middleware for resilience.

    Attributes:
        _api_key: Orshot API key
        _base_url: Orshot API base URL
        _timeout: Request timeout in seconds
        _http_client: RetryableHttpClient for API calls
    """

    DEFAULT_BASE_URL = "https://api.orshot.com/v1"
    DEFAULT_TIMEOUT = 60.0  # Per story requirements

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        """Initialize Orshot client.

        Args:
            api_key: Orshot API key
            base_url: API base URL (default: https://api.orshot.com/v1)
            timeout: Request timeout in seconds (default: 60.0)
            retry_config: Retry configuration (uses defaults if None)

        Raises:
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._base_url = base_url or self.DEFAULT_BASE_URL
        self._timeout = timeout
        self._retry_config = retry_config or RetryConfig(timeout=timeout)

        # Initialize HTTP client with retry middleware
        self._http_client = RetryableHttpClient(
            config=self._retry_config,
            api_name="orshot",
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Orshot API requests.

        Returns:
            Dictionary with Authorization and Content-Type headers.
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _parse_template(self, data: dict[str, Any]) -> OrshotTemplate:
        """Parse API response into OrshotTemplate.

        Args:
            data: Template data from API response

        Returns:
            OrshotTemplate dataclass
        """
        # Extract variable names from modifications object
        modifications = data.get("modifications", {})
        variables = list(modifications.keys())

        return OrshotTemplate(
            id=data.get("id", ""),
            name=data.get("name", ""),
            canva_id=data.get("canvaId", ""),
            variables=variables,
            dimensions=(
                data.get("width", 0),
                data.get("height", 0),
            ),
        )

    async def list_templates(self) -> list[OrshotTemplate]:
        """List available templates.

        Returns:
            List of available templates. Empty list on API failure
            (graceful degradation).
        """
        result: RetryResult = await self._http_client.get(
            f"{self._base_url}/studio-templates-list",
            headers=self._get_headers(),
        )

        if not result.success:
            logger.error(
                "Failed to list Orshot templates after %d attempts: %s",
                result.attempts,
                result.last_error,
            )
            return []

        try:
            data = result.response.json()
            templates_data = data.get("data", [])
            return [self._parse_template(t) for t in templates_data]
        except Exception as e:
            logger.error("Failed to parse templates response: %s", e)
            return []

    async def generate_graphic(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> GeneratedGraphic:
        """Generate a graphic from template.

        Args:
            template_id: Template ID to use
            variables: Variable values to inject (headline, product_name, date, etc.)

        Returns:
            GeneratedGraphic with image URL

        Raises:
            ValueError: If template is not found
            RuntimeError: If generation fails after retries
        """
        payload = {
            "templateId": template_id,
            "modifications": variables,
            "response": {
                "format": "png",
                "type": "url",
            },
        }

        result: RetryResult = await self._http_client.post(
            f"{self._base_url}/generate/images",
            headers=self._get_headers(),
            json=payload,
        )

        if not result.success:
            # Check for template not found error
            if result.response:
                try:
                    error_data = result.response.json()
                    error_code = error_data.get("error", {}).get("code", "")
                    if error_code == "TEMPLATE_NOT_FOUND":
                        raise ValueError(f"Template '{template_id}' not found")
                except AttributeError:
                    # JSON parsing failed or malformed response - continue to RuntimeError
                    pass
                except ValueError as ve:
                    # Re-raise ValueError for template not found
                    if "not found" in str(ve):
                        raise
                    # JSON decode error - continue to RuntimeError

            error_msg = f"Failed to generate graphic after {result.attempts} attempts: {result.last_error}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            data = result.response.json()
            graphic_data = data.get("data", {})

            # Parse created_at timestamp
            created_str = graphic_data.get("createdAt", "")
            if created_str:
                # Handle ISO format with Z suffix
                created_at = datetime.fromisoformat(
                    created_str.replace("Z", "+00:00")
                )
            else:
                created_at = datetime.now(timezone.utc)

            return GeneratedGraphic(
                id=graphic_data.get("id", ""),
                template_id=graphic_data.get("templateId", template_id),
                image_url=graphic_data.get("imageUrl", ""),
                local_path=None,
                variables_used=variables,
                created_at=created_at,
            )
        except Exception as e:
            error_msg = f"Failed to parse graphic response: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def download_graphic(
        self,
        graphic: GeneratedGraphic,
        output_path: Path,
    ) -> Path:
        """Download generated graphic to local path.

        Args:
            graphic: Generated graphic to download
            output_path: Local path to save to

        Returns:
            Path to downloaded file

        Raises:
            RuntimeError: If download fails after retries
        """
        if not graphic.image_url:
            raise RuntimeError("Cannot download graphic: no image URL")

        result: RetryResult = await self._http_client.get(
            graphic.image_url,
            headers={},  # No auth needed for CDN URLs
        )

        if not result.success:
            error_msg = f"Failed to download graphic {graphic.id}: {result.last_error}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write image content to file
            output_path.write_bytes(result.response.content)

            logger.info("Downloaded graphic %s to %s", graphic.id, output_path)
            return output_path
        except Exception as e:
            error_msg = f"Failed to save graphic to {output_path}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http_client.close()

    async def __aenter__(self) -> "OrshotClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        try:
            await self.close()
        except Exception as e:
            logger.warning("Error closing Orshot client: %s", e)
