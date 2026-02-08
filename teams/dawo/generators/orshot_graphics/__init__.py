"""Orshot Graphics Generator - Branded graphic generation for DAWO.

This module provides Orshot-powered branded graphics generation
using Canva templates with dynamic content injection.

Exports:
    OrshotRenderer: Main graphics renderer agent class
    OrshotRendererProtocol: Protocol for renderer interface (testability)
    UsageTrackerProtocol: Protocol for usage tracking (testability)
    UsageLimitExceeded: Exception raised when monthly limit reached
    RenderRequest: Input dataclass for graphics generation
    RenderResult: Output dataclass with graphic and quality info
    ContentType: Content type enum for template selection
    InstagramFormat: Instagram dimension constants
    Dimensions: Named tuple for width/height
    get_target_dimensions: Get target dimensions for content type
    validate_template_dimensions: Check template dimensions match target
    select_template_for_content: Auto-select best template for content type
    is_template_for_content_type: Check if template matches content type
"""

from .agent import (
    OrshotRenderer,
    OrshotRendererProtocol,
    UsageTrackerProtocol,
    UsageLimitExceeded,
)
from .schemas import (
    RenderRequest,
    RenderResult,
    ContentType,
)
from .templates import (
    InstagramFormat,
    Dimensions,
    get_target_dimensions,
    validate_template_dimensions,
    select_template_for_content,
    is_template_for_content_type,
)

__all__: list[str] = [
    # Core agent
    "OrshotRenderer",
    # Protocols
    "OrshotRendererProtocol",
    "UsageTrackerProtocol",
    # Exceptions
    "UsageLimitExceeded",
    # Data classes
    "RenderRequest",
    "RenderResult",
    # Enums and types
    "ContentType",
    "InstagramFormat",
    "Dimensions",
    # Template utilities
    "get_target_dimensions",
    "validate_template_dimensions",
    "select_template_for_content",
    "is_template_for_content_type",
]
