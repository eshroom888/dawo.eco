"""Orshot Graphics Renderer Agent.

Generates branded graphics using Orshot API with Canva templates.
Stores generated assets to Google Drive with quality scoring.

Configuration is received via dependency injection - NEVER loads config directly.

The renderer follows the Content Generator Framework:
1. Check usage limits before proceeding
2. Select appropriate template for content type
3. Build and inject template variables
4. Generate graphic via Orshot API
5. Download and upload to Google Drive
6. Calculate quality score
7. Return result with asset details
"""

import logging
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from integrations.orshot import (
    OrshotClientProtocol,
    OrshotTemplate,
    GeneratedGraphic,
)
from integrations.google_drive import (
    GoogleDriveClientProtocol,
    AssetType,
    DriveAsset,
)

from .schemas import RenderRequest, RenderResult, ContentType
from .templates import (
    get_target_dimensions,
    validate_template_dimensions,
    select_template_for_content,
    is_template_for_content_type,
)

logger = logging.getLogger(__name__)


# Usage tracker protocol - will be implemented in Task 5
@runtime_checkable
class UsageTrackerProtocol(Protocol):
    """Protocol for usage tracking.

    Tracks monthly Orshot render usage against tier limits.
    """

    async def can_render(self) -> bool:
        """Check if rendering is allowed within usage limits."""
        ...

    async def get_usage(self) -> int:
        """Get current month's render count."""
        ...

    async def increment(self) -> tuple[int, bool, bool]:
        """Increment usage count.

        Returns:
            Tuple of (new_count, is_warning, is_limit_reached)
        """
        ...


@runtime_checkable
class OrshotRendererProtocol(Protocol):
    """Protocol defining the Orshot renderer interface.

    Any class implementing this protocol can be used for graphics rendering.
    Enables easy mocking and alternative implementations.
    """

    async def render(self, request: RenderRequest) -> RenderResult:
        """Render a branded graphic.

        Args:
            request: Render request with content and template details

        Returns:
            RenderResult with graphic URLs and quality info
        """
        ...


class UsageLimitExceeded(Exception):
    """Raised when monthly render limit is reached."""

    pass


class OrshotRenderer:
    """Branded graphics renderer using Orshot API.

    Generates graphics from Canva templates with dynamic content injection.
    Stores results to Google Drive with quality scoring.

    CRITICAL: Accept config via dependency injection - NEVER load directly.

    Attributes:
        _orshot: Orshot client for graphics generation
        _drive: Google Drive client for asset storage
        _usage_tracker: Optional usage tracker for limit enforcement
    """

    def __init__(
        self,
        orshot: OrshotClientProtocol,
        drive: GoogleDriveClientProtocol,
        usage_tracker: Optional[UsageTrackerProtocol] = None,
    ) -> None:
        """Initialize the graphics renderer with injected dependencies.

        Args:
            orshot: Orshot client for graphics generation.
                   Injected by Team Builder - NEVER instantiate directly.
            drive: Google Drive client for asset storage.
            usage_tracker: Optional usage tracker for limit enforcement.
                          If not provided, usage is not tracked.
        """
        self._orshot = orshot
        self._drive = drive
        self._usage_tracker = usage_tracker

        logger.info("OrshotRenderer initialized")

    async def render(self, request: RenderRequest) -> RenderResult:
        """Render a branded graphic from a template.

        Follows the Content Generator Framework:
        1. Check usage limits (if tracker provided)
        2. Select template or use specified
        3. Build template variables
        4. Generate graphic via Orshot
        5. Download and upload to Drive
        6. Calculate quality score
        7. Return result

        Args:
            request: Render request with content details

        Returns:
            RenderResult with graphic URLs and quality info
        """
        start_time = time.time()

        try:
            # Step 1: Check usage limits
            usage_count = 0
            usage_warning = False
            if self._usage_tracker:
                if not await self._usage_tracker.can_render():
                    raise UsageLimitExceeded("Monthly render limit reached (3000 renders)")
                usage_count = await self._usage_tracker.get_usage()

            # Step 2: Get template
            template = await self._get_template(request)
            if not template:
                return RenderResult.failure(
                    request.content_id,
                    "No suitable template found for content type",
                )

            # Step 3: Validate dimensions (log warning if mismatch)
            is_valid, dim_msg = validate_template_dimensions(
                template, request.content_type
            )
            if not is_valid:
                logger.warning(
                    "Template dimension warning for %s: %s",
                    request.content_id,
                    dim_msg,
                )

            # Step 4: Build template variables
            variables = self._build_variables(request, template)

            # Step 5: Generate graphic
            graphic = await self._orshot.generate_graphic(
                template_id=template.id,
                variables=variables,
            )

            # Step 6: Download to temp file
            temp_path = await self._download_to_temp(graphic, request)

            # Step 7: Upload to Google Drive
            drive_asset = await self._upload_to_drive(temp_path, request, template)

            # Step 8: Track usage
            if self._usage_tracker:
                usage_count, usage_warning, _ = await self._usage_tracker.increment()

            # Step 9: Calculate quality score
            quality_score = self._calculate_quality(
                template, request, graphic, variables
            )

            # Step 10: Build result
            generation_time_ms = int((time.time() - start_time) * 1000)

            return RenderResult(
                content_id=request.content_id,
                template_id=template.id,
                template_name=template.name,
                image_url=graphic.image_url,
                drive_url=drive_asset.web_view_link if drive_asset else None,
                drive_file_id=drive_asset.id if drive_asset else None,
                local_path=temp_path,
                dimensions=template.dimensions,
                quality_score=quality_score,
                usage_count=usage_count,
                usage_warning=usage_warning,
                generation_time_ms=generation_time_ms,
                success=True,
            )

        except UsageLimitExceeded as e:
            logger.error("Usage limit exceeded: %s", e)
            return RenderResult.failure(request.content_id, str(e))

        except Exception as e:
            logger.error("Render failed for %s: %s", request.content_id, e)
            return RenderResult.failure(request.content_id, str(e))

    async def _get_template(
        self, request: RenderRequest
    ) -> Optional[OrshotTemplate]:
        """Get template for rendering.

        If template_id is specified, fetches that template.
        Otherwise, auto-selects based on content type.

        Args:
            request: Render request

        Returns:
            Selected template, or None if not found
        """
        templates = await self._orshot.list_templates()

        if request.template_id:
            # Find specific template
            for template in templates:
                if template.id == request.template_id:
                    return template
            logger.warning("Specified template not found: %s", request.template_id)
            return None

        # Auto-select based on content type
        return select_template_for_content(templates, request.content_type)

    def _build_variables(
        self,
        request: RenderRequest,
        template: OrshotTemplate,
    ) -> dict[str, str]:
        """Build template variables from request.

        Maps request fields to template variable names.
        Only includes variables the template supports.

        Args:
            request: Render request
            template: Target template

        Returns:
            Dictionary of variable name -> value
        """
        # Map all possible variables
        all_variables = {
            "headline": request.headline,
            "product_name": request.product_name or "",
            "date": request.date_display or "",
            "topic": request.topic,
        }

        # Filter to only include variables the template uses
        variables = {}
        for var_name in template.variables:
            if var_name in all_variables:
                value = all_variables[var_name]
                # Sanitize: limit length and strip
                value = self._sanitize_variable(value)
                variables[var_name] = value

        logger.debug(
            "Built %d variables for template %s: %s",
            len(variables),
            template.id,
            list(variables.keys()),
        )

        return variables

    def _sanitize_variable(self, value: str, max_length: int = 200) -> str:
        """Sanitize a variable value for template injection.

        Args:
            value: Raw value
            max_length: Maximum character length

        Returns:
            Sanitized value
        """
        if not value:
            return ""

        # Strip whitespace
        value = value.strip()

        # Limit length
        if len(value) > max_length:
            value = value[:max_length].rsplit(" ", 1)[0] + "..."

        return value

    async def _download_to_temp(
        self,
        graphic: GeneratedGraphic,
        request: RenderRequest,
    ) -> Path:
        """Download graphic to temporary file.

        Args:
            graphic: Generated graphic
            request: Original request

        Returns:
            Path to downloaded file
        """
        # Generate unique filename
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        short_id = str(uuid.uuid4())[:8]
        safe_topic = "".join(c for c in request.topic.lower() if c.isalnum())[:20]
        filename = f"{date_str}_orshot_{safe_topic}_{short_id}.png"

        # Use system temp directory
        temp_dir = Path(tempfile.gettempdir()) / "dawo_orshot"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / filename

        # Download
        await self._orshot.download_graphic(graphic, temp_path)

        logger.debug("Downloaded graphic to %s", temp_path)
        return temp_path

    async def _upload_to_drive(
        self,
        local_path: Path,
        request: RenderRequest,
        template: OrshotTemplate,
    ) -> Optional[DriveAsset]:
        """Upload graphic to Google Drive.

        Uploads to DAWO.ECO/Assets/Orshot/ folder.

        Args:
            local_path: Path to local file
            request: Original request
            template: Template used

        Returns:
            DriveAsset if successful, None on failure
        """
        try:
            metadata = {
                "content_id": request.content_id,
                "template_id": template.id,
                "template_name": template.name,
                "content_type": request.content_type.value,
                "topic": request.topic,
            }

            asset = await self._drive.upload_asset(
                file_path=local_path,
                asset_type=AssetType.BRANDED_GRAPHIC,
                metadata=metadata,
            )

            logger.info(
                "Uploaded graphic to Drive: %s -> %s",
                local_path.name,
                asset.id,
            )
            return asset

        except Exception as e:
            logger.error(
                "Failed to upload to Drive (keeping local copy): %s", e
            )
            return None

    def _calculate_quality(
        self,
        template: OrshotTemplate,
        request: RenderRequest,
        graphic: GeneratedGraphic,
        variables_used: dict[str, str],
    ) -> float:
        """Calculate render quality score (1-10).

        Factors:
        - Template match for content type (-2 if wrong type)
        - Variable completeness (-1 per missing required)
        - Resolution check (-1 if below minimum)
        - Generation success (-3 if no image URL)

        Args:
            template: Template used
            request: Original request
            graphic: Generated graphic
            variables_used: Variables that were used

        Returns:
            Quality score between 1.0 and 10.0
        """
        score = 10.0

        # Template match (-2 if wrong content type)
        if not is_template_for_content_type(template, request.content_type):
            score -= 2.0
            logger.debug("Quality penalty: template not designed for content type")

        # Variable completeness (-1 per missing required)
        for var_name in template.variables:
            if var_name not in variables_used or not variables_used[var_name]:
                score -= 1.0
                logger.debug("Quality penalty: missing variable %s", var_name)

        # Resolution check (-1 if below minimum)
        min_dim = 1080
        if template.dimensions[0] < min_dim or template.dimensions[1] < min_dim:
            score -= 1.0
            logger.debug("Quality penalty: resolution below minimum")

        # Generation success (-3 if no image URL)
        if not graphic.image_url:
            score -= 3.0
            logger.debug("Quality penalty: no image URL generated")

        final_score = max(1.0, min(10.0, score))

        if final_score < 6.0:
            logger.warning(
                "Low quality render for %s: score=%.1f",
                request.content_id,
                final_score,
            )

        return final_score
