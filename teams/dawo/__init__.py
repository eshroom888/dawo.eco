"""DAWO Agent Team - AI agents for DAWO.ECO content platform.

This module provides the agent team for DAWO.ECO, organized by capability:
    - scanners/: Research and discovery agents (scan tier)
    - generators/: Content creation agents (generate tier)
    - validators/: Compliance and quality agents (generate tier)
    - orchestrators/: Team coordination agents (strategize tier)

All agents are registered in team_spec.py and discovered by Team Builder.

Usage:
    from teams.dawo import AGENTS

    # Team Builder will use AGENTS list for dynamic composition
    # Agents are resolved by capability via AgentRegistry
"""

from .team_spec import AGENTS

# Capability subdirectory imports (agents added as implemented)
from . import scanners
from . import generators
from . import validators
from . import orchestrators

__all__ = [
    "AGENTS",
    "scanners",
    "generators",
    "validators",
    "orchestrators",
]
