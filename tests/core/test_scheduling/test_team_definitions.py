"""Tests for TEAM_DEFINITIONS registry and validation.

Story 7-7, Task 3.3: Team definition tests.
Target: 5+ tests.
"""

import pytest

from core.scheduling.manual_trigger_service import (
    TEAM_DEFINITIONS,
    validate_team_definitions,
)
from core.scheduling.jobs import AGENT_RUNNERS


class TestTeamDefinitions:
    """Tests for TEAM_DEFINITIONS constant."""

    def test_all_teams_have_required_keys(self):
        """Every team has display_name, description, agents."""
        for team_name, team_def in TEAM_DEFINITIONS.items():
            assert "display_name" in team_def, f"Team '{team_name}' missing display_name"
            assert "description" in team_def, f"Team '{team_name}' missing description"
            assert "agents" in team_def, f"Team '{team_name}' missing agents"
            assert len(team_def["agents"]) > 0, f"Team '{team_name}' has empty agents list"

    def test_all_team_agents_exist_in_runner_registry(self):
        """Every agent referenced by a team exists in AGENT_RUNNERS."""
        for team_name, team_def in TEAM_DEFINITIONS.items():
            for agent in team_def["agents"]:
                assert agent in AGENT_RUNNERS, (
                    f"Team '{team_name}' references unknown agent '{agent}'"
                )

    def test_expected_teams_exist(self):
        """Expected team names are defined."""
        assert "regulatory_monitors" in TEAM_DEFINITIONS
        assert "analytics_pipeline" in TEAM_DEFINITIONS
        assert "content_research" in TEAM_DEFINITIONS
        assert "all_scanners" in TEAM_DEFINITIONS

    def test_all_scanners_contains_all_agents(self):
        """all_scanners team includes all 8 registered agents."""
        all_scanner_agents = TEAM_DEFINITIONS["all_scanners"]["agents"]
        for agent_name in AGENT_RUNNERS:
            assert agent_name in all_scanner_agents, (
                f"Agent '{agent_name}' missing from all_scanners team"
            )

    def test_no_duplicate_agents_in_team(self):
        """No team has duplicate agent entries."""
        for team_name, team_def in TEAM_DEFINITIONS.items():
            agents = team_def["agents"]
            assert len(agents) == len(set(agents)), (
                f"Team '{team_name}' has duplicate agents"
            )


class TestValidateTeamDefinitions:
    """Tests for validate_team_definitions function."""

    def test_validation_passes_for_current_definitions(self):
        """Current TEAM_DEFINITIONS pass validation."""
        validate_team_definitions()  # Should not raise

    def test_validation_fails_for_unknown_agent(self, monkeypatch):
        """Validation raises ValueError if team references unknown agent."""
        bad_teams = {
            "bad_team": {
                "display_name": "Bad Team",
                "description": "Has invalid agent",
                "agents": ["nonexistent_agent"],
            },
        }
        monkeypatch.setattr(
            "core.scheduling.manual_trigger_service.TEAM_DEFINITIONS",
            bad_teams,
        )

        with pytest.raises(ValueError, match="nonexistent_agent"):
            validate_team_definitions()
