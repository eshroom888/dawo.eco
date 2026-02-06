"""Tests for LLM tier configuration and resolution.

Tests verify:
- Default task-type to tier mapping (AC #1)
- Per-agent override resolution (AC #3)
- Override precedence over defaults (AC #3)
- Config injection pattern, NOT direct file loading (AC #2)
- Validation of configuration
"""

import pytest
from teams.dawo.config import (
    LLMTierResolver,
    LLMTierConfig,
    TierConfig,
    TaskType,
    TierName,
    AgentOverride,
)


@pytest.fixture
def valid_config() -> LLMTierConfig:
    """Create a valid LLM tier configuration for testing."""
    return LLMTierConfig(
        version="2026-02",
        model_versions={
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-5-20250929",
            "opus": "claude-opus-4-6",
        },
        default_tiers={
            "scan": "haiku",
            "generate": "sonnet",
            "strategize": "opus",
        },
        tier_descriptions={
            "haiku": "High-volume research, fast classification, source discovery.",
            "sonnet": "Content creation, compliance checking, judgment tasks.",
            "opus": "Complex planning, multi-step reasoning, strategic decisions.",
        },
        agent_overrides={},
    )


@pytest.fixture
def config_with_override() -> LLMTierConfig:
    """Create config with agent-specific override."""
    return LLMTierConfig(
        version="2026-02",
        model_versions={
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-5-20250929",
            "opus": "claude-opus-4-6",
        },
        default_tiers={
            "scan": "haiku",
            "generate": "sonnet",
            "strategize": "opus",
        },
        tier_descriptions={
            "haiku": "High-volume research.",
            "sonnet": "Content creation.",
            "opus": "Complex planning.",
        },
        agent_overrides={
            "special_agent": AgentOverride(
                tier=TierName.OPUS,
                reason="Requires complex reasoning beyond default",
            ),
        },
    )


@pytest.fixture
def resolver(valid_config: LLMTierConfig) -> LLMTierResolver:
    """Create resolver with valid config."""
    return LLMTierResolver(valid_config)


@pytest.fixture
def resolver_with_override(config_with_override: LLMTierConfig) -> LLMTierResolver:
    """Create resolver with override config."""
    return LLMTierResolver(config_with_override)


class TestDefaultTierResolution:
    """Test default task-type to tier mapping (AC #1)."""

    def test_scan_resolves_to_haiku(self, resolver: LLMTierResolver) -> None:
        """Scan tasks should resolve to haiku tier."""
        tier = resolver.resolve_tier("any_scanner", TaskType.SCAN)
        assert tier.tier_name == TierName.HAIKU

    def test_generate_resolves_to_sonnet(self, resolver: LLMTierResolver) -> None:
        """Generate tasks should resolve to sonnet tier."""
        tier = resolver.resolve_tier("any_generator", TaskType.GENERATE)
        assert tier.tier_name == TierName.SONNET

    def test_strategize_resolves_to_opus(self, resolver: LLMTierResolver) -> None:
        """Strategize tasks should resolve to opus tier."""
        tier = resolver.resolve_tier("any_orchestrator", TaskType.STRATEGIZE)
        assert tier.tier_name == TierName.OPUS

    def test_returns_correct_model_id_for_haiku(
        self, resolver: LLMTierResolver
    ) -> None:
        """Should return the correct Claude model ID for haiku tier."""
        tier = resolver.resolve_tier("scanner", TaskType.SCAN)
        assert tier.model_id == "claude-haiku-4-5-20251001"

    def test_returns_correct_model_id_for_sonnet(
        self, resolver: LLMTierResolver
    ) -> None:
        """Should return the correct Claude model ID for sonnet tier."""
        tier = resolver.resolve_tier("generator", TaskType.GENERATE)
        assert tier.model_id == "claude-sonnet-4-5-20250929"

    def test_returns_correct_model_id_for_opus(
        self, resolver: LLMTierResolver
    ) -> None:
        """Should return the correct Claude model ID for opus tier."""
        tier = resolver.resolve_tier("orchestrator", TaskType.STRATEGIZE)
        assert tier.model_id == "claude-opus-4-6"

    def test_returns_tier_description(self, resolver: LLMTierResolver) -> None:
        """Should include tier description in result."""
        tier = resolver.resolve_tier("scanner", TaskType.SCAN)
        assert "research" in tier.description.lower()

    def test_default_is_not_override(self, resolver: LLMTierResolver) -> None:
        """Default resolution should not be marked as override."""
        tier = resolver.resolve_tier("any_agent", TaskType.GENERATE)
        assert tier.is_override is False
        assert tier.override_reason is None


class TestAgentOverrides:
    """Test per-agent override resolution (AC #3)."""

    def test_override_takes_precedence(
        self, resolver_with_override: LLMTierResolver
    ) -> None:
        """Agent override should take precedence over task-type default."""
        # special_agent has override to opus, but we pass SCAN task type
        tier = resolver_with_override.resolve_tier("special_agent", TaskType.SCAN)
        assert tier.tier_name == TierName.OPUS  # Override, not HAIKU from scan default

    def test_override_includes_reason(
        self, resolver_with_override: LLMTierResolver
    ) -> None:
        """Override result should include the reason."""
        tier = resolver_with_override.resolve_tier("special_agent", TaskType.SCAN)
        assert tier.override_reason is not None
        assert "complex reasoning" in tier.override_reason.lower()

    def test_is_override_flag_set(
        self, resolver_with_override: LLMTierResolver
    ) -> None:
        """Override result should have is_override flag set."""
        tier = resolver_with_override.resolve_tier("special_agent", TaskType.SCAN)
        assert tier.is_override is True

    def test_unknown_agent_uses_default(
        self, resolver_with_override: LLMTierResolver
    ) -> None:
        """Unknown agent (not in overrides) should use task-type default."""
        tier = resolver_with_override.resolve_tier("unknown_agent", TaskType.GENERATE)
        assert tier.tier_name == TierName.SONNET
        assert tier.is_override is False


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_tier_in_defaults_raises(self) -> None:
        """Should raise error if default tier references invalid tier name."""
        invalid_config = LLMTierConfig(
            version="1.0",
            model_versions={"haiku": "model-1"},
            default_tiers={"scan": "nonexistent_tier"},  # Invalid!
            tier_descriptions={},
            agent_overrides={},
        )
        with pytest.raises(ValueError, match="not in model_versions"):
            LLMTierResolver(invalid_config)

    def test_missing_tier_in_model_versions_raises(self) -> None:
        """Should raise error if default tier has no model version."""
        invalid_config = LLMTierConfig(
            version="1.0",
            model_versions={"haiku": "model-1"},  # Missing sonnet
            default_tiers={"scan": "haiku", "generate": "sonnet"},  # sonnet not in model_versions
            tier_descriptions={},
            agent_overrides={},
        )
        with pytest.raises(ValueError):
            LLMTierResolver(invalid_config)

    def test_valid_config_passes(self, valid_config: LLMTierConfig) -> None:
        """Valid configuration should not raise errors."""
        resolver = LLMTierResolver(valid_config)
        assert resolver is not None


class TestConfigInjection:
    """Test dependency injection pattern (AC #2)."""

    def test_accepts_config_via_constructor(self, valid_config: LLMTierConfig) -> None:
        """Resolver should accept config via constructor (dependency injection)."""
        resolver = LLMTierResolver(valid_config)
        assert resolver is not None

    def test_no_direct_file_loading(self) -> None:
        """LLMTierResolver should NOT load files directly.

        This test verifies that LLMTierResolver constructor only accepts
        LLMTierConfig, not file paths. File loading is Team Builder's job.
        """
        # LLMTierResolver constructor signature only accepts LLMTierConfig
        # This is verified by type hints and the fact that passing a string
        # would cause a type error or attribute error
        import inspect
        sig = inspect.signature(LLMTierResolver.__init__)
        params = list(sig.parameters.keys())
        # Should only have 'self' and 'config' parameters
        assert params == ["self", "config"]


class TestTierEnums:
    """Test enum type safety."""

    def test_task_type_values(self) -> None:
        """TaskType enum should have correct values."""
        assert TaskType.SCAN.value == "scan"
        assert TaskType.GENERATE.value == "generate"
        assert TaskType.STRATEGIZE.value == "strategize"

    def test_tier_name_values(self) -> None:
        """TierName enum should have correct values."""
        assert TierName.HAIKU.value == "haiku"
        assert TierName.SONNET.value == "sonnet"
        assert TierName.OPUS.value == "opus"

    def test_enum_string_conversion(self) -> None:
        """Enums should convert to/from strings correctly."""
        assert TaskType("scan") == TaskType.SCAN
        assert TierName("opus") == TierName.OPUS


class TestModelIdRetrieval:
    """Test model ID retrieval functionality."""

    def test_get_model_id_for_haiku(self, resolver: LLMTierResolver) -> None:
        """Should return model ID for haiku tier."""
        model_id = resolver.get_model_id(TierName.HAIKU)
        assert model_id == "claude-haiku-4-5-20251001"

    def test_get_model_id_for_sonnet(self, resolver: LLMTierResolver) -> None:
        """Should return model ID for sonnet tier."""
        model_id = resolver.get_model_id(TierName.SONNET)
        assert model_id == "claude-sonnet-4-5-20250929"

    def test_get_model_id_for_opus(self, resolver: LLMTierResolver) -> None:
        """Should return model ID for opus tier."""
        model_id = resolver.get_model_id(TierName.OPUS)
        assert model_id == "claude-opus-4-6"


class TestGetAllTiers:
    """Test retrieval of all tier configurations."""

    def test_get_all_tiers_returns_all(self, resolver: LLMTierResolver) -> None:
        """Should return all available tiers."""
        all_tiers = resolver.get_all_tiers()
        assert "haiku" in all_tiers
        assert "sonnet" in all_tiers
        assert "opus" in all_tiers

    def test_get_all_tiers_contains_tier_config(
        self, resolver: LLMTierResolver
    ) -> None:
        """Each tier should be a TierConfig instance."""
        all_tiers = resolver.get_all_tiers()
        for tier_name, tier_config in all_tiers.items():
            assert isinstance(tier_config, TierConfig)
            assert tier_config.model_id is not None


# =============================================================================
# LOADER TESTS (Added by code review)
# =============================================================================

from pathlib import Path
import json
from teams.dawo.config import load_llm_tier_config


class TestLoaderFunction:
    """Test load_llm_tier_config function (H1: was untested)."""

    def test_load_from_valid_json_file(self, tmp_path: Path) -> None:
        """Should successfully load config from valid JSON file."""
        config_data = {
            "version": "test-1.0",
            "model_versions": {
                "haiku": "test-haiku-model",
                "sonnet": "test-sonnet-model",
                "opus": "test-opus-model",
            },
            "default_tiers": {
                "scan": "haiku",
                "generate": "sonnet",
                "strategize": "opus",
            },
            "tier_descriptions": {
                "haiku": "Test haiku description",
                "sonnet": "Test sonnet description",
                "opus": "Test opus description",
            },
            "agent_overrides": {},
        }
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_llm_tier_config(config_file)

        assert result.version == "test-1.0"
        assert result.model_versions["haiku"] == "test-haiku-model"
        assert result.default_tiers["scan"] == "haiku"

    def test_load_parses_agent_overrides(self, tmp_path: Path) -> None:
        """Should correctly parse agent overrides from JSON."""
        config_data = {
            "version": "1.0",
            "model_versions": {"haiku": "m1", "sonnet": "m2", "opus": "m3"},
            "default_tiers": {"scan": "haiku", "generate": "sonnet", "strategize": "opus"},
            "tier_descriptions": {},
            "agent_overrides": {
                "special_agent": {
                    "tier": "opus",
                    "reason": "Needs complex reasoning",
                }
            },
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_llm_tier_config(config_file)

        assert "special_agent" in result.agent_overrides
        assert result.agent_overrides["special_agent"].tier == TierName.OPUS
        assert result.agent_overrides["special_agent"].reason == "Needs complex reasoning"

    def test_load_handles_missing_optional_fields(self, tmp_path: Path) -> None:
        """Should handle missing optional fields gracefully."""
        config_data = {
            "model_versions": {"haiku": "m1"},
            "default_tiers": {"scan": "haiku"},
            # Missing: version, tier_descriptions, agent_overrides
        }
        config_file = tmp_path / "minimal.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_llm_tier_config(config_file)

        assert result.version == "unknown"
        assert result.tier_descriptions == {}
        assert result.agent_overrides == {}

    def test_load_raises_file_not_found_with_helpful_message(self) -> None:
        """Should raise FileNotFoundError with helpful message."""
        with pytest.raises(FileNotFoundError, match="LLM tier config not found"):
            load_llm_tier_config(Path("/nonexistent/path/config.json"))

    def test_load_raises_json_decode_error(self, tmp_path: Path) -> None:
        """Should raise JSONDecodeError for invalid JSON."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_llm_tier_config(config_file)

    def test_load_raises_key_error_for_missing_required(self, tmp_path: Path) -> None:
        """Should raise KeyError with helpful message for missing required fields."""
        config_data = {"version": "1.0"}  # Missing model_versions and default_tiers
        config_file = tmp_path / "incomplete.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(KeyError, match="Missing required field"):
            load_llm_tier_config(config_file)

    def test_load_override_missing_reason_uses_default(self, tmp_path: Path) -> None:
        """Should use default reason when override reason is missing."""
        config_data = {
            "model_versions": {"opus": "m1"},
            "default_tiers": {"scan": "opus"},
            "agent_overrides": {
                "agent_no_reason": {"tier": "opus"}  # No reason field
            },
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_llm_tier_config(config_file)

        assert result.agent_overrides["agent_no_reason"].reason == "No reason specified"


class TestLoaderInvalidOverrideTier:
    """Test error handling for invalid tier in agent override (M1)."""

    def test_invalid_tier_in_override_raises_value_error(self, tmp_path: Path) -> None:
        """Should raise ValueError with helpful message for invalid tier."""
        config_data = {
            "model_versions": {"haiku": "m1"},
            "default_tiers": {"scan": "haiku"},
            "agent_overrides": {
                "bad_agent": {"tier": "invalid_tier_name", "reason": "test"}
            },
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid tier 'invalid_tier_name'"):
            load_llm_tier_config(config_file)

    def test_missing_tier_in_override_raises_key_error(self, tmp_path: Path) -> None:
        """Should raise KeyError when override is missing tier field."""
        config_data = {
            "model_versions": {"haiku": "m1"},
            "default_tiers": {"scan": "haiku"},
            "agent_overrides": {
                "bad_agent": {"reason": "test"}  # Missing 'tier' field
            },
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with pytest.raises(KeyError, match="missing required 'tier' field"):
            load_llm_tier_config(config_file)


class TestActualConfigFileIntegration:
    """Integration test for actual config/dawo_llm_tiers.json (H2)."""

    def test_actual_config_file_loads_successfully(self) -> None:
        """The actual config file should load without errors."""
        config_path = Path("config/dawo_llm_tiers.json")
        if not config_path.exists():
            pytest.skip("Config file not found - run from project root")

        config = load_llm_tier_config(config_path)

        # Verify expected structure
        assert config.version is not None
        assert "haiku" in config.model_versions
        assert "sonnet" in config.model_versions
        assert "opus" in config.model_versions
        assert config.default_tiers["scan"] == "haiku"
        assert config.default_tiers["generate"] == "sonnet"
        assert config.default_tiers["strategize"] == "opus"

    def test_actual_config_creates_valid_resolver(self) -> None:
        """The actual config should create a working resolver."""
        config_path = Path("config/dawo_llm_tiers.json")
        if not config_path.exists():
            pytest.skip("Config file not found - run from project root")

        config = load_llm_tier_config(config_path)
        resolver = LLMTierResolver(config)

        # Verify resolver works
        tier = resolver.resolve_tier("any_agent", TaskType.GENERATE)
        assert tier.tier_name == TierName.SONNET
        assert "sonnet" in tier.model_id.lower()
