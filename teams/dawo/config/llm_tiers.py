"""LLM tier configuration and resolution for DAWO agents.

This module provides the tier resolution system that maps task types to
appropriate LLM models, with support for per-agent overrides.

Architecture Compliance:
- Configuration is injected via constructor (NEVER loads files directly)
- Team Builder is responsible for loading config and injecting it
- Agents receive resolved TierConfig, not tier names

Usage:
    config = load_tier_config()  # Team Builder loads
    resolver = LLMTierResolver(config)
    tier = resolver.resolve_tier("eu_compliance_checker", TaskType.GENERATE)
    # tier.model_id = "claude-sonnet-4-5-20250929"
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskType(Enum):
    """Task types that map to default LLM tiers.

    Each task type has a default tier assignment:
    - SCAN: High-volume research, source discovery (haiku)
    - GENERATE: Content creation, compliance checking (sonnet)
    - STRATEGIZE: Complex planning, multi-step reasoning (opus)
    """

    SCAN = "scan"
    GENERATE = "generate"
    STRATEGIZE = "strategize"


class TierName(Enum):
    """Available LLM tier names.

    Tiers correspond to Claude model capabilities:
    - HAIKU: Fast, cost-optimized for high-volume tasks
    - SONNET: Balanced quality and cost for most tasks
    - OPUS: Maximum capability for complex reasoning
    """

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


@dataclass(frozen=True)
class TierConfig:
    """Resolved tier configuration for an agent.

    Contains all information needed by an agent to use its assigned LLM.

    Attributes:
        tier_name: The tier enum value (HAIKU, SONNET, OPUS)
        model_id: The actual Claude model ID string for API calls
        description: Human-readable description of tier use cases
        is_override: True if this came from agent_overrides, not default
        override_reason: Explanation for override (only if is_override=True)
    """

    tier_name: TierName
    model_id: str
    description: str
    is_override: bool = False
    override_reason: Optional[str] = None


@dataclass(frozen=True)
class AgentOverride:
    """Per-agent tier override configuration.

    Used when a specific agent needs a different tier than the
    default for its task type.

    Attributes:
        tier: The tier to use instead of the default
        reason: Explanation for why this override exists
    """

    tier: TierName
    reason: str


@dataclass(frozen=True)
class LLMTierConfig:
    """Complete LLM tier configuration loaded from JSON.

    This is the data structure that Team Builder loads from
    config/dawo_llm_tiers.json and injects into LLMTierResolver.

    Attributes:
        version: Configuration version string
        model_versions: Mapping of tier names to actual model IDs
        default_tiers: Mapping of task types to default tier names
        tier_descriptions: Human-readable descriptions for each tier
        agent_overrides: Per-agent tier overrides
    """

    version: str
    model_versions: dict[str, str]  # tier_name -> model_id
    default_tiers: dict[str, str]  # task_type -> tier_name
    tier_descriptions: dict[str, str]
    agent_overrides: dict[str, AgentOverride]


class LLMTierResolver:
    """Resolves LLM model tier for agents based on task type and overrides.

    Configuration is injected via constructor - NEVER loads files directly.
    Team Builder is responsible for loading and injecting config.

    Resolution order:
    1. Check agent_overrides for specific agent name
    2. Fall back to default_tiers by task_type

    Example:
        config = load_tier_config()  # Team Builder loads
        resolver = LLMTierResolver(config)
        tier = resolver.resolve_tier("eu_compliance_checker", TaskType.GENERATE)
        # Use tier.model_id for API calls
    """

    def __init__(self, config: LLMTierConfig) -> None:
        """Initialize resolver with injected configuration.

        Args:
            config: LLMTierConfig loaded by Team Builder

        Raises:
            ValueError: If configuration is invalid (e.g., missing model versions)
        """
        self._config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration on initialization.

        Raises:
            ValueError: If any default tier references a tier not in model_versions
        """
        for task_type, tier_name in self._config.default_tiers.items():
            if tier_name not in self._config.model_versions:
                raise ValueError(
                    f"Default tier '{tier_name}' for task '{task_type}' "
                    f"not in model_versions"
                )

    def resolve_tier(self, agent_name: str, task_type: TaskType) -> TierConfig:
        """Resolve the LLM tier for an agent.

        Resolution order:
        1. Check agent_overrides for specific agent
        2. Fall back to default_tiers by task_type

        Args:
            agent_name: The registered name of the agent
            task_type: The type of task (SCAN, GENERATE, STRATEGIZE)

        Returns:
            TierConfig with resolved tier details including model_id
        """
        # Check for agent-specific override
        if agent_name in self._config.agent_overrides:
            override = self._config.agent_overrides[agent_name]
            tier_name = override.tier.value
            return TierConfig(
                tier_name=override.tier,
                model_id=self._config.model_versions[tier_name],
                description=self._config.tier_descriptions.get(tier_name, ""),
                is_override=True,
                override_reason=override.reason,
            )

        # Fall back to default tier for task type
        tier_name = self._config.default_tiers[task_type.value]
        return TierConfig(
            tier_name=TierName(tier_name),
            model_id=self._config.model_versions[tier_name],
            description=self._config.tier_descriptions.get(tier_name, ""),
            is_override=False,
        )

    def get_model_id(self, tier_name: TierName) -> str:
        """Get the actual model ID for a tier name.

        Args:
            tier_name: The tier enum value

        Returns:
            The Claude model ID string for API calls
        """
        return self._config.model_versions[tier_name.value]

    def get_all_tiers(self) -> dict[str, TierConfig]:
        """Get all available tiers with their configurations.

        Returns:
            Dictionary mapping tier names to TierConfig objects
        """
        return {
            tier_name: TierConfig(
                tier_name=TierName(tier_name),
                model_id=model_id,
                description=self._config.tier_descriptions.get(tier_name, ""),
            )
            for tier_name, model_id in self._config.model_versions.items()
        }
