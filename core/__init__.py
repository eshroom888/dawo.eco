"""Core module for DAWO.ECO platform integration.

Provides base classes and utilities for database models, configuration,
and shared platform functionality.

Note: This module provides DAWO.ECO specific implementations. When running
on the full IMAGO.ECO platform, these may be replaced by platform equivalents.
"""

from .models import Base

__all__ = [
    "Base",
]
