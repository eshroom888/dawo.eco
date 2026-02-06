"""Config loading utility for Team Builder.

This module provides functions for loading LLM tier configuration from JSON.
These functions are for Team Builder use ONLY - individual agents should
NEVER import or call these directly.

Architecture Compliance:
- Team Builder loads config using these utilities
- Team Builder injects loaded config into LLMTierResolver
- Agents receive LLMTierResolver instance, never load config themselves
"""

import json
from pathlib import Path
from typing import Optional

from .llm_tiers import AgentOverride, LLMTierConfig, TierName


class LLMTierConfigError(Exception):
    """Error loading or parsing LLM tier configuration."""

    pass


def load_llm_tier_config(config_path: Optional[Path] = None) -> LLMTierConfig:
    """Load LLM tier configuration from JSON file.

    This function is for Team Builder use ONLY.
    Individual agents should NEVER call this directly.

    Args:
        config_path: Path to config file. Defaults to config/dawo_llm_tiers.json

    Returns:
        LLMTierConfig ready for injection into LLMTierResolver

    Raises:
        FileNotFoundError: If config file does not exist
        json.JSONDecodeError: If config file is not valid JSON
        KeyError: If required fields are missing from config
        ValueError: If agent override specifies invalid tier name
    """
    if config_path is None:
        config_path = Path("config/dawo_llm_tiers.json")

    # Load JSON with helpful error context
    try:
        with open(config_path, encoding="utf-8") as f:
            raw_config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"LLM tier config not found at '{config_path}'. "
            f"Ensure config/dawo_llm_tiers.json exists in project root."
        )
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in LLM tier config '{config_path}': {e.msg}",
            e.doc,
            e.pos,
        )

    # Validate required fields
    required_fields = ["model_versions", "default_tiers"]
    for field in required_fields:
        if field not in raw_config:
            raise KeyError(
                f"Missing required field '{field}' in LLM tier config. "
                f"Required fields: {required_fields}"
            )

    # Parse agent overrides with validation
    overrides: dict[str, AgentOverride] = {}
    for agent_name, override_data in raw_config.get("agent_overrides", {}).items():
        tier_value = override_data.get("tier")
        if tier_value is None:
            raise KeyError(
                f"Agent override '{agent_name}' missing required 'tier' field"
            )
        try:
            tier = TierName(tier_value)
        except ValueError:
            valid_tiers = [t.value for t in TierName]
            raise ValueError(
                f"Invalid tier '{tier_value}' for agent override '{agent_name}'. "
                f"Valid tiers: {valid_tiers}"
            )
        overrides[agent_name] = AgentOverride(
            tier=tier,
            reason=override_data.get("reason", "No reason specified"),
        )

    return LLMTierConfig(
        version=raw_config.get("version", "unknown"),
        model_versions=raw_config["model_versions"],
        default_tiers=raw_config["default_tiers"],
        tier_descriptions=raw_config.get("tier_descriptions", {}),
        agent_overrides=overrides,
    )
