"""Agent schedule business logic service.

Story 7-6, Task 4.1: Service layer for schedule management,
dependency checking, and default seeding.

Usage:
    from core.scheduling.schedule_service import AgentScheduleService

    service = AgentScheduleService(repository, config)
    schedules = await service.get_all_schedules()
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Optional

from core.scheduling.cron_utils import (
    calculate_next_run,
    cron_to_human_readable,
    validate_cron_expression,
)
from core.scheduling.dtos import (
    AgentScheduleDTO,
    DependencyWarning,
    ScheduleChangeLogDTO,
    ScheduleUpdateRequest,
)
from core.scheduling.models import AgentSchedule, ScheduleChangeLog
from core.scheduling.schedule_repository import AgentScheduleRepository

if TYPE_CHECKING:
    from core.config import AgentSchedulerConfig

logger = logging.getLogger(__name__)

# Default schedule seed data (from scanner configs + existing ARQ cron jobs)
DEFAULT_SCHEDULES = [
    {
        "agent_name": "health_claims_monitor",
        "display_name": "EU Health Claims Register Monitor",
        "schedule_cron": "0 5 * * 0",
        "timezone": "UTC",
        "config_source": "dawo_health_claims.json",
        "dependencies": [],
    },
    {
        "agent_name": "novel_food_monitor",
        "display_name": "Novel Food Catalogue Monitor",
        "schedule_cron": "30 5 * * 0",
        "timezone": "UTC",
        "config_source": "dawo_novel_food.json",
        "dependencies": [],
    },
    {
        "agent_name": "mattilsynet_monitor",
        "display_name": "Mattilsynet Regulatory Monitor",
        "schedule_cron": "0 7 * * *",
        "timezone": "UTC",
        "config_source": "dawo_mattilsynet.json",
        "dependencies": [],
    },
    {
        "agent_name": "competitor_scanner",
        "display_name": "Competitor Content Scanner",
        "schedule_cron": "0 3 * * *",
        "timezone": "UTC",
        "config_source": "dawo_competitor_scanner.json",
        "dependencies": [],
    },
    {
        "agent_name": "lead_scanner",
        "display_name": "B2B Lead Research Scanner",
        "schedule_cron": "0 7 * * 1",
        "timezone": "Europe/Oslo",
        "config_source": "dawo_lead_scanner.json",
        "dependencies": [],
    },
    {
        "agent_name": "shopify_attribution_poll",
        "display_name": "Shopify Attribution Poll",
        "schedule_cron": "0 * * * *",
        "timezone": "UTC",
        "config_source": "jobs.py",
        "dependencies": [],
    },
    {
        "agent_name": "post_publish_scoring",
        "display_name": "Post-Publish Quality Scoring",
        "schedule_cron": "0 3 * * *",
        "timezone": "UTC",
        "config_source": "jobs.py",
        "dependencies": ["shopify_attribution_poll"],
    },
    {
        "agent_name": "feedback_loop",
        "display_name": "Performance Feedback Loop",
        "schedule_cron": "0 4 * * 0",
        "timezone": "UTC",
        "config_source": "jobs.py",
        "dependencies": ["post_publish_scoring"],
    },
]


class AgentScheduleService:
    """Business logic for agent schedule management.

    Provides schedule CRUD, dependency checking, and default seeding.
    All scheduling is pure computation — no LLM usage.

    Attributes:
        _repository: AgentScheduleRepository for persistence
        _config: AgentSchedulerConfig for settings
    """

    def __init__(self, repository: AgentScheduleRepository, config: "AgentSchedulerConfig") -> None:
        """Initialize service.

        Args:
            repository: AgentScheduleRepository instance
            config: AgentSchedulerConfig instance
        """
        self._repository = repository
        self._config = config

    async def get_all_schedules(self) -> list[AgentScheduleDTO]:
        """Get all agent schedules as enriched DTOs.

        Returns:
            List of AgentScheduleDTO with human-readable cron and computed next_run.
        """
        schedules = await self._repository.get_all()
        return [self._to_dto(s) for s in schedules]

    async def get_schedule(self, agent_name: str) -> AgentScheduleDTO | None:
        """Get a single schedule by agent name.

        Args:
            agent_name: Unique agent identifier

        Returns:
            AgentScheduleDTO if found, None otherwise.
        """
        schedule = await self._repository.get_by_agent_name(agent_name)
        if schedule is None:
            return None
        return self._to_dto(schedule)

    async def update_schedule(
        self,
        agent_name: str,
        updates: ScheduleUpdateRequest,
    ) -> AgentScheduleDTO | None:
        """Update an agent's schedule with audit logging.

        Validates cron expressions, computes new next_run_at,
        and creates audit log entries for each changed field.

        Args:
            agent_name: Agent to update
            updates: Fields to change

        Returns:
            Updated AgentScheduleDTO, or None if agent not found.

        Raises:
            ValueError: If cron expression is invalid.
        """
        schedule = await self._repository.get_by_agent_name(agent_name)
        if schedule is None:
            return None

        # Validate cron if changing
        if updates.schedule_cron is not None:
            if not validate_cron_expression(updates.schedule_cron):
                raise ValueError(
                    f"Invalid cron expression: {updates.schedule_cron}"
                )

        # Track changes for audit
        changes: list[tuple[str, str | None, str]] = []

        if updates.schedule_cron is not None and updates.schedule_cron != schedule.schedule_cron:
            changes.append(("schedule_cron", schedule.schedule_cron, updates.schedule_cron))
            schedule.schedule_cron = updates.schedule_cron

        if updates.timezone is not None and updates.timezone != schedule.timezone:
            changes.append(("timezone", schedule.timezone, updates.timezone))
            schedule.timezone = updates.timezone

        if updates.enabled is not None and updates.enabled != schedule.enabled:
            changes.append(("enabled", str(schedule.enabled), str(updates.enabled)))
            schedule.enabled = updates.enabled

        if updates.display_name is not None and updates.display_name != schedule.display_name:
            changes.append(("display_name", schedule.display_name, updates.display_name))
            schedule.display_name = updates.display_name

        if updates.description is not None and updates.description != schedule.description:
            changes.append(("description", schedule.description, updates.description))
            schedule.description = updates.description

        if updates.dependencies is not None and updates.dependencies != schedule.dependencies:
            changes.append(("dependencies", str(schedule.dependencies), str(updates.dependencies)))
            schedule.dependencies = updates.dependencies

        # Recompute next_run if cron or timezone changed
        if updates.schedule_cron is not None or updates.timezone is not None:
            schedule.next_run_at = calculate_next_run(
                schedule.schedule_cron,
                schedule.timezone,
            )

        schedule.updated_at = datetime.now(UTC)

        # Save audit logs
        for field_name, old_val, new_val in changes:
            log = ScheduleChangeLog(
                agent_name=agent_name,
                field_changed=field_name,
                old_value=old_val,
                new_value=new_val,
            )
            await self._repository.save_change_log(log)

        await self._repository.save(schedule)
        return self._to_dto(schedule)

    async def toggle_enabled(
        self,
        agent_name: str,
        enabled: bool,
    ) -> AgentScheduleDTO | None:
        """Enable or disable an agent schedule.

        Args:
            agent_name: Agent to toggle
            enabled: New enabled state

        Returns:
            Updated AgentScheduleDTO, or None if not found.
        """
        schedule = await self._repository.get_by_agent_name(agent_name)
        if schedule is None:
            return None

        old_value = str(schedule.enabled)
        schedule.enabled = enabled
        schedule.updated_at = datetime.now(UTC)

        log = ScheduleChangeLog(
            agent_name=agent_name,
            field_changed="enabled",
            old_value=old_value,
            new_value=str(enabled),
        )
        await self._repository.save_change_log(log)
        await self._repository.save(schedule)

        return self._to_dto(schedule)

    async def check_dependencies(
        self,
        agent_name: str,
        proposed_cron: str,
        timezone: str,
    ) -> list[DependencyWarning]:
        """Check for scheduling conflicts with dependencies.

        Computes next_run for both agent and dependencies to detect
        if agent runs before its dependency completes.

        Args:
            agent_name: Agent being scheduled
            proposed_cron: Proposed cron expression
            timezone: Proposed timezone

        Returns:
            List of DependencyWarning objects.
        """
        schedule = await self._repository.get_by_agent_name(agent_name)
        if schedule is None or not schedule.dependencies:
            return []

        warnings: list[DependencyWarning] = []
        agent_next_run = calculate_next_run(proposed_cron, timezone)

        for dep_name in schedule.dependencies:
            dep = await self._repository.get_by_agent_name(dep_name)
            if dep is None:
                warnings.append(DependencyWarning(
                    agent_name=agent_name,
                    dependency_name=dep_name,
                    agent_next_run=agent_next_run,
                    dependency_next_run=None,
                    warning_message=f"Dependency '{dep_name}' not found in schedules",
                    severity="warning",
                ))
                continue

            dep_next_run = calculate_next_run(
                dep.schedule_cron,
                dep.timezone,
            )

            # Estimate dep completion using last run duration
            estimated_duration = dep.last_run_duration_seconds or 300.0  # default 5 min
            dep_estimated_end = dep_next_run + timedelta(seconds=estimated_duration)

            # Check if agent would run before dependency completes
            if agent_next_run < dep_estimated_end:
                severity = "critical" if estimated_duration > 3600 else "warning"
                warnings.append(DependencyWarning(
                    agent_name=agent_name,
                    dependency_name=dep_name,
                    agent_next_run=agent_next_run,
                    dependency_next_run=dep_next_run,
                    warning_message=(
                        f"Agent '{agent_name}' scheduled at "
                        f"{agent_next_run.strftime('%H:%M')} may run before "
                        f"dependency '{dep_name}' completes "
                        f"(estimated end: {dep_estimated_end.strftime('%H:%M')})"
                    ),
                    severity=severity,
                ))

        return warnings

    async def get_audit_log(self, agent_name: str, limit: int = 50) -> list[ScheduleChangeLogDTO]:
        """Get change log entries for an agent.

        Args:
            agent_name: Agent to query
            limit: Maximum entries to return

        Returns:
            List of ScheduleChangeLogDTO for serialization.
        """
        logs = await self._repository.get_change_logs(agent_name, limit)
        return [
            ScheduleChangeLogDTO(
                id=str(log.id),
                agent_name=log.agent_name,
                field_changed=log.field_changed,
                old_value=log.old_value,
                new_value=log.new_value,
                changed_by=log.changed_by,
                created_at=log.created_at,
            )
            for log in logs
        ]

    async def seed_defaults(self) -> int:
        """Seed default schedules from scanner configs and existing cron jobs.

        Only seeds if repository is empty (count == 0).
        Computes initial next_run_at for each schedule.

        Returns:
            Number of schedules seeded (0 if already populated).
        """
        count = await self._repository.count()
        if count > 0:
            logger.info("Schedules already exist (%d), skipping seed", count)
            return 0

        seeded = 0
        for defaults in DEFAULT_SCHEDULES:
            schedule = AgentSchedule(
                agent_name=defaults["agent_name"],
                display_name=defaults["display_name"],
                schedule_cron=defaults["schedule_cron"],
                timezone=defaults["timezone"],
                enabled=True,
                config_source=defaults["config_source"],
                dependencies=defaults["dependencies"],
                next_run_at=calculate_next_run(
                    defaults["schedule_cron"],
                    defaults["timezone"],
                ),
            )
            await self._repository.save(schedule)
            seeded += 1

        logger.info("Seeded %d default agent schedules", seeded)
        return seeded

    def _to_dto(self, schedule: AgentSchedule) -> AgentScheduleDTO:
        """Convert model to DTO with computed fields.

        Args:
            schedule: AgentSchedule model instance

        Returns:
            AgentScheduleDTO with human-readable cron and computed next_run.
        """
        return AgentScheduleDTO(
            id=schedule.id,
            agent_name=schedule.agent_name,
            display_name=schedule.display_name,
            description=schedule.description,
            schedule_cron=schedule.schedule_cron,
            cron_human_readable=cron_to_human_readable(schedule.schedule_cron),
            timezone=schedule.timezone or "UTC",
            enabled=schedule.enabled if schedule.enabled is not None else True,
            last_run_at=schedule.last_run_at,
            last_run_status=schedule.last_run_status,
            last_run_duration_seconds=schedule.last_run_duration_seconds,
            next_run_at=schedule.next_run_at,
            dependencies=schedule.dependencies or [],
            config_source=schedule.config_source,
        )


__all__ = [
    "AgentScheduleService",
    "DEFAULT_SCHEDULES",
]
