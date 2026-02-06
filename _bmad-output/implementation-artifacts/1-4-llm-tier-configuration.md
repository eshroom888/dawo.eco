# Story 1.4: LLM Tier Configuration

Status: done

---

## Story

As a **developer**,
I want LLM model selection configured by task type,
So that costs are optimized while maintaining quality where needed.

---

## Acceptance Criteria

1. **Given** the LLM tier configuration exists at `config/dawo_llm_tiers.json`
   **When** an agent is instantiated
   **Then** it receives its model tier based on task type mapping:
   - `scan` tasks → Claude Haiku 4 (low cost, high volume)
   - `generate` tasks → Claude Sonnet 4 (quality, creativity)
   - `strategize` tasks → Claude Opus 4.5 (complex planning)
   **And** individual agents can have per-agent overrides in config

2. **Given** Team Builder composes a team
   **When** it injects configuration into agents
   **Then** each agent receives appropriate model tier
   **And** agents never hardcode model selection

3. **Given** config specifies an override for a specific agent
   **When** that agent is instantiated
   **Then** it uses the override model instead of task-type default

---

## Tasks / Subtasks

- [x] Task 1: Create LLM tier configuration file (AC: #1)
  - [x] 1.1 Create `config/dawo_llm_tiers.json` with full schema
  - [x] 1.2 Define default_tiers mapping: scan→haiku, generate→sonnet, strategize→opus
  - [x] 1.3 Add model_versions section with actual Claude model IDs
  - [x] 1.4 Add agent_overrides section for per-agent customization
  - [x] 1.5 Add tier_descriptions explaining when to use each tier

- [x] Task 2: Create LLM tier resolver module (AC: #1, #2, #3)
  - [x] 2.1 Create `teams/dawo/config/` directory structure
  - [x] 2.2 Create `teams/dawo/config/__init__.py` with exports
  - [x] 2.3 Create `teams/dawo/config/llm_tiers.py` with LLMTierResolver class
  - [x] 2.4 Define TierConfig dataclass with: tier_name, model_id, description
  - [x] 2.5 Define LLMTierConfig dataclass for full configuration
  - [x] 2.6 Implement `resolve_tier(agent_name, task_type)` method
  - [x] 2.7 Implement config loading via dependency injection (NOT direct file load)

- [x] Task 3: Define LLM tier types and enums (AC: #1)
  - [x] 3.1 Define `TaskType` enum: SCAN, GENERATE, STRATEGIZE
  - [x] 3.2 Define `TierName` enum: HAIKU, SONNET, OPUS
  - [x] 3.3 Define `ModelId` type alias for model version strings
  - [x] 3.4 Create type-safe mapping between TaskType and TierName

- [x] Task 4: Implement tier resolution logic (AC: #2, #3)
  - [x] 4.1 Implement default tier lookup by task type
  - [x] 4.2 Implement per-agent override lookup
  - [x] 4.3 Override takes precedence over default
  - [x] 4.4 Return full TierConfig with model_id for agent use
  - [x] 4.5 Add validation for unknown agents/tiers

- [x] Task 5: Update team_spec.py integration (AC: #2)
  - [x] 5.1 Document tier field usage in RegisteredAgent
  - [x] 5.2 Ensure existing agents use tier names (NOT model names)
  - [x] 5.3 Add example showing correct tier reference pattern

- [x] Task 6: Create comprehensive tests
  - [x] 6.1 Test default tier resolution (scan→haiku, generate→sonnet, strategize→opus)
  - [x] 6.2 Test per-agent override resolution
  - [x] 6.3 Test override precedence over default
  - [x] 6.4 Test config injection pattern (not direct file load)
  - [x] 6.5 Test unknown agent handling (returns default for task type)
  - [x] 6.6 Test unknown tier handling (raises clear error)
  - [x] 6.7 Test model version retrieval
  - [x] 6.8 Test config validation (required fields, valid tiers)

---

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source:** [architecture.md#Core-Architectural-Decisions], [project-context.md#LLM-Tier-Assignment]

**Decision from Architecture:**
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **LLM Tiers** | Task-Type Mapping | Default by task (scan→haiku, generate→sonnet, strategize→opus) with per-agent override in settings |

**Critical Rules:**
- ✅ ALL agents receive tier via config injection from Team Builder
- ✅ Use tier names (`scan`, `generate`, `strategize`) in agent registration
- ❌ NEVER hardcode LLM model names like `claude-3-sonnet` in agent code
- ❌ NEVER load config files directly - use injection

### Default Tier Mapping (MUST FOLLOW)

**Source:** [project-context.md#LLM-Tier-Assignment]

| Task Type | Default Tier | Model | Use For |
|-----------|--------------|-------|---------|
| `scan` | haiku | Claude Haiku 4 | High-volume research, source discovery, fast classification |
| `generate` | sonnet | Claude Sonnet 4 | Content writing, compliance checking, judgment tasks |
| `strategize` | opus | Claude Opus 4.5 | Campaign planning, complex decisions, multi-step reasoning |

### Configuration File Schema

**Source:** [architecture.md#Config-Files]

```json
// config/dawo_llm_tiers.json
{
  "version": "2026-02",
  "description": "LLM tier configuration for DAWO agents",

  "model_versions": {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6"
  },

  "default_tiers": {
    "scan": "haiku",
    "generate": "sonnet",
    "strategize": "opus"
  },

  "tier_descriptions": {
    "scan": "High-volume research, fast classification, source discovery. Cost-optimized.",
    "generate": "Content creation, compliance checking, judgment tasks. Quality-focused.",
    "strategize": "Complex planning, multi-step reasoning, strategic decisions. Maximum capability."
  },

  "agent_overrides": {
    "example_agent_name": {
      "tier": "opus",
      "reason": "Requires complex reasoning beyond default"
    }
  }
}
```

### LLM Tier Resolver Implementation

**Source:** [architecture.md#Agent-Registration-Pattern], [project-context.md#Configuration-Loading]

```python
# teams/dawo/config/llm_tiers.py
from typing import Optional, Protocol
from dataclasses import dataclass
from enum import Enum

class TaskType(Enum):
    """Task types that map to default LLM tiers."""
    SCAN = "scan"
    GENERATE = "generate"
    STRATEGIZE = "strategize"

class TierName(Enum):
    """Available LLM tier names."""
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"

@dataclass
class TierConfig:
    """Resolved tier configuration for an agent."""
    tier_name: TierName
    model_id: str
    description: str
    is_override: bool = False
    override_reason: Optional[str] = None

@dataclass
class AgentOverride:
    """Per-agent tier override configuration."""
    tier: TierName
    reason: str

@dataclass
class LLMTierConfig:
    """Complete LLM tier configuration loaded from JSON."""
    version: str
    model_versions: dict[str, str]  # tier_name -> model_id
    default_tiers: dict[str, str]   # task_type -> tier_name
    tier_descriptions: dict[str, str]
    agent_overrides: dict[str, AgentOverride]

class LLMTierResolver:
    """Resolves LLM model tier for agents based on task type and overrides.

    Configuration is injected via constructor - NEVER loads files directly.
    Team Builder is responsible for loading and injecting config.

    Usage:
        config = load_tier_config()  # Team Builder loads
        resolver = LLMTierResolver(config)
        tier = resolver.resolve_tier("eu_compliance_checker", TaskType.GENERATE)
    """

    def __init__(self, config: LLMTierConfig):
        """Accept config via dependency injection - NEVER load directly."""
        self._config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration on initialization."""
        # Ensure all default tiers reference valid tier names
        for task_type, tier_name in self._config.default_tiers.items():
            if tier_name not in self._config.model_versions:
                raise ValueError(f"Default tier '{tier_name}' for task '{task_type}' not in model_versions")

    def resolve_tier(
        self,
        agent_name: str,
        task_type: TaskType
    ) -> TierConfig:
        """Resolve the LLM tier for an agent.

        Resolution order:
        1. Check agent_overrides for specific agent
        2. Fall back to default_tiers by task_type

        Args:
            agent_name: The registered name of the agent
            task_type: The type of task (SCAN, GENERATE, STRATEGIZE)

        Returns:
            TierConfig with resolved tier details
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
                override_reason=override.reason
            )

        # Fall back to default tier for task type
        tier_name = self._config.default_tiers[task_type.value]
        return TierConfig(
            tier_name=TierName(tier_name),
            model_id=self._config.model_versions[tier_name],
            description=self._config.tier_descriptions.get(tier_name, ""),
            is_override=False
        )

    def get_model_id(self, tier_name: TierName) -> str:
        """Get the actual model ID for a tier name."""
        return self._config.model_versions[tier_name.value]

    def get_all_tiers(self) -> dict[str, TierConfig]:
        """Get all available tiers with their configurations."""
        return {
            tier_name: TierConfig(
                tier_name=TierName(tier_name),
                model_id=model_id,
                description=self._config.tier_descriptions.get(tier_name, "")
            )
            for tier_name, model_id in self._config.model_versions.items()
        }
```

### Config Loading Utility (for Team Builder)

**Source:** [project-context.md#Configuration-Loading]

```python
# teams/dawo/config/loader.py
import json
from pathlib import Path
from typing import Optional

from .llm_tiers import LLMTierConfig, AgentOverride, TierName

def load_llm_tier_config(config_path: Optional[Path] = None) -> LLMTierConfig:
    """Load LLM tier configuration from JSON file.

    This function is for Team Builder use ONLY.
    Individual agents should NEVER call this directly.

    Args:
        config_path: Path to config file. Defaults to config/dawo_llm_tiers.json

    Returns:
        LLMTierConfig ready for injection into LLMTierResolver
    """
    if config_path is None:
        config_path = Path("config/dawo_llm_tiers.json")

    with open(config_path) as f:
        raw_config = json.load(f)

    # Parse agent overrides
    overrides = {}
    for agent_name, override_data in raw_config.get("agent_overrides", {}).items():
        overrides[agent_name] = AgentOverride(
            tier=TierName(override_data["tier"]),
            reason=override_data.get("reason", "No reason specified")
        )

    return LLMTierConfig(
        version=raw_config.get("version", "unknown"),
        model_versions=raw_config["model_versions"],
        default_tiers=raw_config["default_tiers"],
        tier_descriptions=raw_config.get("tier_descriptions", {}),
        agent_overrides=overrides
    )
```

### Package Structure (MUST FOLLOW)

**Source:** [architecture.md#Project-Structure]

```
teams/dawo/
├── config/                           # CREATE THIS
│   ├── __init__.py                   # Export LLMTierResolver, types, loader
│   ├── llm_tiers.py                  # LLMTierResolver class, TierConfig, enums
│   └── loader.py                     # Config loading for Team Builder

config/
├── dawo_compliance_rules.json        # Exists (Story 1.2)
├── dawo_brand_profile.json           # Exists (Story 1.3)
└── dawo_llm_tiers.json               # CREATE THIS

tests/teams/dawo/
├── test_validators/                  # Exists
└── test_config/                      # CREATE THIS
    ├── __init__.py
    └── test_llm_tiers.py
```

### Previous Story Learnings (Stories 1.2 and 1.3)

**Source:** [1-3-brand-voice-validator.md#Completion-Notes-List]

**MUST APPLY these learnings:**

1. **Config Injection** - All configuration MUST be injected via constructor. The `LLMTierResolver` accepts `LLMTierConfig` dataclass, not file path.

2. **Complete Exports** - Add ALL types to `__all__` in `__init__.py`:
   - `LLMTierResolver`
   - `LLMTierConfig`
   - `TierConfig`
   - `TaskType`
   - `TierName`
   - `AgentOverride`
   - `load_llm_tier_config` (for Team Builder only)

3. **Enum Pattern** - Use enums for type safety (`TaskType`, `TierName`) rather than raw strings.

4. **Validation on Init** - Validate configuration when resolver is constructed, fail fast on invalid config.

5. **Dataclass Pattern** - Use dataclasses for all configuration structures for type safety and immutability.

### Integration with Existing Agents

**Source:** [team_spec.py]

Current agents already use tier names correctly:
```python
# teams/dawo/team_spec.py (existing, correct pattern)
AGENTS = [
    RegisteredAgent(
        name="eu_compliance_checker",
        agent_class=EUComplianceChecker,
        capabilities=["eu_compliance", "content_validation"],
        tier="generate"  # ✅ Correct: uses tier name
    ),
    RegisteredAgent(
        name="brand_voice_validator",
        agent_class=BrandVoiceValidator,
        capabilities=["brand_voice", "content_validation"],
        tier="generate"  # ✅ Correct: uses tier name
    ),
]
```

The `tier` field in `RegisteredAgent` corresponds to `TaskType` values. Team Builder will use `LLMTierResolver` to get the actual `model_id` at composition time.

### Testing Requirements

**Source:** [architecture.md#Tests]

Create tests in `tests/teams/dawo/test_config/test_llm_tiers.py`:

```python
import pytest
from teams.dawo.config import (
    LLMTierResolver,
    LLMTierConfig,
    TierConfig,
    TaskType,
    TierName,
    AgentOverride
)

class TestDefaultTierResolution:
    """Test default task-type to tier mapping."""

    def test_scan_resolves_to_haiku(self, resolver): ...
    def test_generate_resolves_to_sonnet(self, resolver): ...
    def test_strategize_resolves_to_opus(self, resolver): ...
    def test_returns_correct_model_id(self, resolver): ...
    def test_returns_tier_description(self, resolver): ...

class TestAgentOverrides:
    """Test per-agent override resolution."""

    def test_override_takes_precedence(self, resolver_with_override): ...
    def test_override_includes_reason(self, resolver_with_override): ...
    def test_is_override_flag_set(self, resolver_with_override): ...
    def test_unknown_agent_uses_default(self, resolver): ...

class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_tier_in_defaults_raises(self): ...
    def test_missing_model_version_raises(self): ...
    def test_valid_config_passes(self): ...

class TestConfigInjection:
    """Test dependency injection pattern."""

    def test_accepts_config_via_constructor(self): ...
    def test_no_direct_file_loading(self): ...

class TestTierEnums:
    """Test enum type safety."""

    def test_task_type_values(self): ...
    def test_tier_name_values(self): ...
    def test_enum_string_conversion(self): ...
```

### Technology Stack Context

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Use type hints, dataclasses, enums |
| Claude Models | Haiku 4.5, Sonnet 4.5, Opus 4.6 | Latest model IDs from architecture |
| Config Format | JSON | Consistent with existing config files |
| Testing | pytest | Standard test patterns |

### Anti-Patterns to AVOID (CRITICAL)

**Source:** [architecture.md#Anti-Patterns], [project-context.md#Anti-Patterns]

1. ❌ `model="claude-3-sonnet"` hardcoded → Use tier system
2. ❌ `config = json.load(open(...))` in agents → Use injection
3. ❌ `if task == "compliance": model = "sonnet"` → Use resolver
4. ❌ Tier names in agent code → Agents receive resolved TierConfig

### Project Context Reference

**Source:** [project-context.md]

The LLM Tier Configuration implements the "LLM Tier Assignment" pattern defined in project-context.md. All future agents MUST:
- Declare their task type (`scan`, `generate`, `strategize`) in team_spec.py
- Receive their LLM model via Team Builder injection
- NEVER reference model names directly

---

## References

- [Source: architecture.md#Core-Architectural-Decisions] - LLM tier task-type mapping decision
- [Source: architecture.md#Implementation-Patterns] - Config injection pattern
- [Source: architecture.md#Anti-Patterns] - Hardcoded model anti-pattern
- [Source: project-context.md#LLM-Tier-Assignment] - Tier assignment rules
- [Source: project-context.md#Configuration-Loading] - Dependency injection pattern
- [Source: epics.md#Story-1.4] - Original story requirements
- [Source: 1-3-brand-voice-validator.md] - Previous story learnings

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation proceeded without issues.

### Completion Notes List

1. **Config File Created** - `config/dawo_llm_tiers.json` with full schema including model_versions (haiku, sonnet, opus), default_tiers mapping, tier_descriptions keyed by tier name, and empty agent_overrides section.

2. **LLMTierResolver Module** - Created `teams/dawo/config/` package with:
   - `llm_tiers.py`: LLMTierResolver class, TaskType/TierName enums, TierConfig/LLMTierConfig/AgentOverride dataclasses
   - `loader.py`: load_llm_tier_config() for Team Builder use only
   - `__init__.py`: Complete exports with all public types

3. **Dependency Injection Pattern** - LLMTierResolver accepts LLMTierConfig via constructor. No direct file loading in resolver. Team Builder uses loader.py to load config.

4. **Type Safety** - Used frozen dataclasses and enums for all configuration structures. Validation occurs at resolver construction time.

5. **Override System** - Per-agent overrides take precedence over task-type defaults. Override includes reason field for documentation.

6. **Tier Description Keys Fixed** - Story spec showed tier_descriptions keyed by task type, but implementation uses tier names (haiku, sonnet, opus) for consistency with code lookup. This is the correct approach since `TierConfig.description` is looked up by tier name, not task type. [Code Review: Accepted deviation]

7. **team_spec.py Documentation** - Added comprehensive LLM Tier System documentation showing the task type → tier → model resolution chain.

8. **Test Coverage** - 25 tests covering all ACs: default resolution, override precedence, config injection, validation, enums, model ID retrieval.

9. **Code Review Additions** - Added 11 loader.py tests covering: JSON parsing, file handling, error messages, invalid tier in override, integration with actual config file. Total: 36 tests.

10. **Error Handling Improved** - loader.py now provides helpful error messages for FileNotFoundError, KeyError (missing fields), and ValueError (invalid tier). Added LLMTierConfigError exception.

11. **Type Safety Constants** - Added TIER_SCAN, TIER_GENERATE, TIER_STRATEGIZE constants to team_spec.py for safer tier string usage.

### Change Log

- 2026-02-06: Code Review Fixes (Adversarial Review)
  - Added 11 new tests for loader.py (was 25, now 36 tests)
  - Added integration tests for actual config file
  - Improved loader.py error messages with helpful context
  - Added LLMTierConfigError exception class
  - Added TIER_SCAN/TIER_GENERATE/TIER_STRATEGIZE constants to team_spec.py
  - Updated test_config/__init__.py with proper docstring
  - Full regression suite: 157 tests passing

- 2026-02-06: Implemented LLM tier configuration system (Story 1.4)
  - Created config/dawo_llm_tiers.json with tier mappings
  - Created teams/dawo/config/ module with LLMTierResolver
  - Added 25 unit tests, all passing
  - Full regression suite: 146 tests passing
  - Updated team_spec.py with tier system documentation

### File List

- [x] `config/dawo_llm_tiers.json` - LLM tier configuration with model versions and overrides
- [x] `teams/dawo/config/__init__.py` - Package exports
- [x] `teams/dawo/config/llm_tiers.py` - LLMTierResolver class, TierConfig, TaskType, TierName enums
- [x] `teams/dawo/config/loader.py` - Config loading utility for Team Builder
- [x] `teams/dawo/team_spec.py` - Updated with LLM tier system documentation
- [x] `tests/teams/dawo/test_config/__init__.py` - Test package init
- [x] `tests/teams/dawo/test_config/test_llm_tiers.py` - Comprehensive tests (25 tests)
