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

Note: AGENTS import is lazy to avoid circular imports with integrations.
"""


def __getattr__(name: str):
    """Lazy import to avoid circular imports with integrations module."""
    if name == "AGENTS":
        from .team_spec import AGENTS
        return AGENTS
    if name == "SERVICES":
        from .team_spec import SERVICES
        return SERVICES
    if name in ("scanners", "generators", "validators", "orchestrators"):
        import importlib
        return importlib.import_module(f".{name}", __package__)
    raise AttributeError(f"module 'teams.dawo' has no attribute '{name}'")


__all__ = [
    "AGENTS",
    "SERVICES",
    "scanners",
    "generators",
    "validators",
    "orchestrators",
]
