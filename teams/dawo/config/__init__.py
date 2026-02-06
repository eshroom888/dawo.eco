"""DAWO team configuration module.

This package provides LLM tier configuration and resolution for DAWO agents.

Exports for general use:
- LLMTierResolver: Resolves LLM model tier for agents
- LLMTierConfig: Complete tier configuration data structure
- TierConfig: Resolved tier configuration for an agent
- TaskType: Enum of task types (SCAN, GENERATE, STRATEGIZE)
- TierName: Enum of tier names (HAIKU, SONNET, OPUS)
- AgentOverride: Per-agent tier override configuration

Exports for Team Builder only:
- load_llm_tier_config: Load configuration from JSON file

Architecture Compliance:
- LLMTierResolver accepts config via constructor (dependency injection)
- Only Team Builder should use load_llm_tier_config
- Individual agents should NEVER load config files directly
"""

from .llm_tiers import (
    AgentOverride,
    LLMTierConfig,
    LLMTierResolver,
    TaskType,
    TierConfig,
    TierName,
)
from .loader import load_llm_tier_config, LLMTierConfigError

__all__ = [
    # Core resolver
    "LLMTierResolver",
    # Data structures
    "LLMTierConfig",
    "TierConfig",
    "AgentOverride",
    # Enums
    "TaskType",
    "TierName",
    # Loader (Team Builder only)
    "load_llm_tier_config",
    # Errors
    "LLMTierConfigError",
]
