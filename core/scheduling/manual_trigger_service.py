"""Manual trigger service for on-demand agent/team execution.

Story 7-7, Task 1.1: ManualTriggerService business logic.
Story 7-7, Task 3.1: TEAM_DEFINITIONS registry.
Story 7-7, Task 4.1: PendingTriggerStore for queue-after-current.

Usage:
    from core.scheduling.manual_trigger_service import ManualTriggerService

    service = ManualTriggerService(repository, config)
    result = await service.trigger_agent("health_claims_monitor")
"""

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from core.scheduling.dtos import (
    PendingTrigger,
    TeamDTO,
    TeamTriggerResult,
    TriggerableAgentDTO,
    TriggerResult,
)
from core.scheduling.models import ScheduleChangeLog
from core.scheduling.schedule_repository import AgentScheduleRepository

if TYPE_CHECKING:
    from core.config import AgentSchedulerConfig

logger = logging.getLogger(__name__)


# Story 7-7, Task 3.1: Team definitions (static, not DB-stored)
TEAM_DEFINITIONS: dict[str, dict] = {
    "regulatory_monitors": {
        "display_name": "Regulatory Monitors",
        "description": "All regulatory scanning agents",
        "agents": ["health_claims_monitor", "novel_food_monitor", "mattilsynet_monitor"],
    },
    "analytics_pipeline": {
        "display_name": "Analytics Pipeline",
        "description": "Full analytics chain: attribution → scoring → feedback",
        "agents": ["shopify_attribution_poll", "post_publish_scoring", "feedback_loop"],
    },
    "content_research": {
        "display_name": "Content Research",
        "description": "Research scanners for content sources",
        "agents": ["competitor_scanner", "lead_scanner"],
    },
    "all_scanners": {
        "display_name": "All Scanners",
        "description": "Run all scanner agents in dependency order",
        "agents": [
            "health_claims_monitor", "novel_food_monitor", "mattilsynet_monitor",
            "competitor_scanner", "lead_scanner",
            "shopify_attribution_poll", "post_publish_scoring", "feedback_loop",
        ],
    },
}


def validate_team_definitions() -> None:
    """Validate all team agent names exist in AGENT_RUNNERS.

    Story 7-7, Task 3.2: Fail-fast validation.
    Called at startup (not import time) to avoid circular deps.

    Raises:
        ValueError: If any team references an unknown agent.
    """
    runners = _get_agent_runners()
    for team_name, team_def in TEAM_DEFINITIONS.items():
        for agent in team_def["agents"]:
            if agent not in runners:
                raise ValueError(
                    f"Team '{team_name}' references unknown agent '{agent}' "
                    f"(not in AGENT_RUNNERS). Valid agents: {sorted(runners.keys())}"
                )


# Story 7-7, Task 4.1: In-memory pending trigger store
class PendingTriggerStore:
    """Ephemeral in-memory store for pending manual triggers.

    Stores triggers for agents that are currently running.
    When the agent completes, the pending trigger is popped and re-enqueued.

    Thread-safe: asyncio is single-threaded, no lock needed.
    """

    def __init__(self) -> None:
        """Initialize empty pending triggers dict."""
        self._pending: dict[str, PendingTrigger] = {}

    def add(
        self,
        agent_name: str,
        triggered_by: str,
        config_overrides: dict | None = None,
    ) -> PendingTrigger:
        """Add a pending trigger for an agent.

        Args:
            agent_name: Agent to trigger after current run
            triggered_by: Who requested the trigger
            config_overrides: Optional runtime config overrides

        Returns:
            Created PendingTrigger.
        """
        trigger = PendingTrigger(
            agent_name=agent_name,
            triggered_by=triggered_by,
            queued_at=datetime.now(UTC),
            config_overrides=config_overrides,
        )
        self._pending[agent_name] = trigger
        logger.info("Pending trigger added for %s by %s", agent_name, triggered_by)
        return trigger

    def pop(self, agent_name: str) -> PendingTrigger | None:
        """Remove and return pending trigger for an agent.

        Args:
            agent_name: Agent to check

        Returns:
            PendingTrigger if exists, None otherwise.
        """
        return self._pending.pop(agent_name, None)

    def get(self, agent_name: str) -> PendingTrigger | None:
        """Peek at pending trigger without removing.

        Args:
            agent_name: Agent to check

        Returns:
            PendingTrigger if exists, None otherwise.
        """
        return self._pending.get(agent_name)

    def was_triggered(self, agent_name: str) -> bool:
        """Check if agent has a pending manual trigger.

        Story 7-8, Task 5.2: Non-destructive check for trigger_type detection.

        Args:
            agent_name: Agent to check

        Returns:
            True if a pending trigger exists for the agent.
        """
        return agent_name in self._pending


# Module-level singleton — shared across async requests
pending_trigger_store = PendingTriggerStore()


def _get_agent_runners() -> dict:
    """Lazy import of AGENT_RUNNERS to avoid circular dependencies.

    Returns:
        AGENT_RUNNERS dict from jobs.py.
    """
    from core.scheduling.jobs import AGENT_RUNNERS

    return AGENT_RUNNERS


class ManualTriggerService:
    """Service for manual agent/team triggering.

    Validates agent names against AGENT_RUNNERS registry,
    checks running status, and manages audit logging.
    Does NOT enqueue ARQ jobs — returns result for router to enqueue.

    Attributes:
        _repository: AgentScheduleRepository for status checks/updates
        _config: AgentSchedulerConfig for settings
    """

    def __init__(
        self,
        repository: AgentScheduleRepository,
        config: "AgentSchedulerConfig",
    ) -> None:
        """Initialize service.

        Args:
            repository: AgentScheduleRepository instance
            config: AgentSchedulerConfig instance
        """
        self._repository = repository
        self._config = config

    async def trigger_agent(
        self,
        agent_name: str,
        triggered_by: str = "operator",
        config_overrides: dict | None = None,
    ) -> TriggerResult:
        """Trigger an agent for immediate execution.

        Validates against AGENT_RUNNERS, checks if running,
        updates status, and logs overrides if provided.

        Args:
            agent_name: Agent to trigger (must be in AGENT_RUNNERS)
            triggered_by: Who triggered ("operator" default)
            config_overrides: Optional runtime config overrides

        Returns:
            TriggerResult with status and metadata.
        """
        now = datetime.now(UTC)
        runners = _get_agent_runners()

        # Validate against registry (whitelist only)
        if agent_name not in runners:
            return TriggerResult(
                agent_name=agent_name,
                status="not_found",
                job_id=None,
                triggered_at=now,
                triggered_by=triggered_by,
                message=f"Agent '{agent_name}' not found in runner registry",
            )

        # Check if currently running
        schedule = await self._repository.get_by_agent_name(agent_name)
        if schedule is not None and schedule.last_run_status == "running":
            return TriggerResult(
                agent_name=agent_name,
                status="already_running",
                job_id=None,
                triggered_at=now,
                triggered_by=triggered_by,
                message=f"Agent '{agent_name}' is already running",
            )

        # Mark as running in DB
        await self._repository.update_run_status(
            agent_name=agent_name,
            status="running",
            duration=None,
            summary=None,
            next_run=None,
        )

        # Log config overrides in audit trail
        if config_overrides:
            log = ScheduleChangeLog(
                agent_name=agent_name,
                field_changed="manual_trigger",
                old_value=None,
                new_value=json.dumps(config_overrides),
                changed_by=triggered_by,
            )
            await self._repository.save_change_log(log)

        return TriggerResult(
            agent_name=agent_name,
            status="queued",
            job_id=None,  # Set by router after ARQ enqueue
            triggered_at=now,
            triggered_by=triggered_by,
            config_overrides=config_overrides,
            message=f"Agent '{agent_name}' triggered for immediate execution",
        )

    async def trigger_team(
        self,
        team_name: str,
        triggered_by: str = "operator",
    ) -> TeamTriggerResult:
        """Trigger all agents in a team in dependency order.

        Args:
            team_name: Team to trigger (must be in TEAM_DEFINITIONS)
            triggered_by: Who triggered ("operator" default)

        Returns:
            TeamTriggerResult with per-agent results.
        """
        team_def = TEAM_DEFINITIONS.get(team_name)
        if team_def is None:
            return TeamTriggerResult(
                team_name=team_name,
                agent_results=[],
                total=0,
                queued=0,
                skipped_running=0,
                failed=0,
            )

        agent_results: list[TriggerResult] = []
        queued = 0
        skipped_running = 0
        failed = 0

        for agent in team_def["agents"]:
            result = await self.trigger_agent(agent, triggered_by=triggered_by)
            agent_results.append(result)

            if result.status == "queued":
                queued += 1
            elif result.status == "already_running":
                skipped_running += 1
            else:
                failed += 1

        return TeamTriggerResult(
            team_name=team_name,
            agent_results=agent_results,
            total=len(team_def["agents"]),
            queued=queued,
            skipped_running=skipped_running,
            failed=failed,
        )

    async def queue_after_current(
        self,
        agent_name: str,
        triggered_by: str = "operator",
        config_overrides: dict | None = None,
    ) -> TriggerResult:
        """Queue a trigger for after the current run completes.

        For already-running agents: marks as pending in in-memory store.
        Returns 'not_running' if agent is not currently executing.

        Args:
            agent_name: Agent to queue
            triggered_by: Who requested
            config_overrides: Optional runtime config overrides

        Returns:
            TriggerResult with queued or not_running status.
        """
        now = datetime.now(UTC)
        runners = _get_agent_runners()

        if agent_name not in runners:
            return TriggerResult(
                agent_name=agent_name,
                status="not_found",
                job_id=None,
                triggered_at=now,
                triggered_by=triggered_by,
                message=f"Agent '{agent_name}' not found in runner registry",
            )

        # Verify agent is actually running before queueing
        schedule = await self._repository.get_by_agent_name(agent_name)
        if schedule is None or schedule.last_run_status != "running":
            return TriggerResult(
                agent_name=agent_name,
                status="not_running",
                job_id=None,
                triggered_at=now,
                triggered_by=triggered_by,
                message=f"Agent '{agent_name}' is not currently running. Use trigger instead.",
            )

        pending_trigger_store.add(
            agent_name=agent_name,
            triggered_by=triggered_by,
            config_overrides=config_overrides,
        )

        return TriggerResult(
            agent_name=agent_name,
            status="queued",
            job_id=None,
            triggered_at=now,
            triggered_by=triggered_by,
            config_overrides=config_overrides,
            message=f"Agent '{agent_name}' queued for execution after current run completes",
        )

    async def get_triggerable_agents(self) -> list[TriggerableAgentDTO]:
        """Get all triggerable agents with enriched schedule data.

        Fetches all schedules in one query (no N+1), merges with
        AGENT_RUNNERS registry to produce enriched list.

        Returns:
            List of TriggerableAgentDTO for all registered agents.
        """
        runners = _get_agent_runners()

        # Single query — no N+1
        all_schedules = await self._repository.get_all()
        schedule_map = {s.agent_name: s for s in all_schedules}

        agents: list[TriggerableAgentDTO] = []
        for agent_name in runners:
            schedule = schedule_map.get(agent_name)

            if schedule is not None:
                agents.append(TriggerableAgentDTO(
                    agent_name=agent_name,
                    display_name=schedule.display_name or agent_name,
                    description=schedule.description,
                    last_run_status=schedule.last_run_status,
                    last_run_at=schedule.last_run_at,
                    last_run_duration_seconds=schedule.last_run_duration_seconds,
                    is_running=schedule.last_run_status == "running",
                    schedule_cron=schedule.schedule_cron,
                    next_scheduled_run=schedule.next_run_at,
                ))
            else:
                agents.append(TriggerableAgentDTO(
                    agent_name=agent_name,
                    display_name=agent_name,
                ))

        return agents

    async def get_teams(self) -> list[TeamDTO]:
        """Get all defined teams.

        Returns:
            List of TeamDTO from TEAM_DEFINITIONS.
        """
        return [
            TeamDTO(
                team_name=name,
                display_name=defn["display_name"],
                agents=defn["agents"],
                description=defn["description"],
            )
            for name, defn in TEAM_DEFINITIONS.items()
        ]


__all__ = [
    "ManualTriggerService",
    "TEAM_DEFINITIONS",
    "validate_team_definitions",
    "PendingTriggerStore",
    "pending_trigger_store",
]
