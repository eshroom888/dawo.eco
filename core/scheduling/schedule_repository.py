"""Agent schedule repository for CRUD operations.

Story 7-6, Task 3.1: Repository pattern with AsyncSession injection.

Usage:
    from core.scheduling.schedule_repository import AgentScheduleRepository

    repo = AgentScheduleRepository(session)
    schedules = await repo.get_all()
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.scheduling.models import AgentSchedule, ScheduleChangeLog

logger = logging.getLogger(__name__)


class AgentScheduleRepository:
    """Repository for agent schedule persistence.

    Accepts AsyncSession via constructor injection.
    Uses merge for upsert behavior.
    Batch queries to prevent N+1.

    Attributes:
        _session: Async SQLAlchemy session
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def get_all(self) -> list[AgentSchedule]:
        """Get all agent schedules ordered by next_run_at.

        Returns:
            List of all AgentSchedule records.
        """
        result = await self._session.execute(
            select(AgentSchedule).order_by(AgentSchedule.next_run_at)
        )
        return list(result.scalars().all())

    async def get_by_agent_name(self, name: str) -> AgentSchedule | None:
        """Get a single schedule by agent_name.

        Args:
            name: Unique agent identifier

        Returns:
            AgentSchedule if found, None otherwise.
        """
        result = await self._session.execute(
            select(AgentSchedule).where(AgentSchedule.agent_name == name)
        )
        return result.scalar_one_or_none()

    async def get_enabled(self) -> list[AgentSchedule]:
        """Get only enabled schedules.

        Returns:
            List of enabled AgentSchedule records.
        """
        result = await self._session.execute(
            select(AgentSchedule)
            .where(AgentSchedule.enabled == True)  # noqa: E712
            .order_by(AgentSchedule.next_run_at)
        )
        return list(result.scalars().all())

    async def get_due_schedules(self, now: datetime) -> list[AgentSchedule]:
        """Get schedules that are due for execution.

        Due = enabled AND next_run_at <= now AND not currently running.

        Args:
            now: Current UTC timestamp

        Returns:
            List of due AgentSchedule records.
        """
        result = await self._session.execute(
            select(AgentSchedule)
            .where(
                AgentSchedule.enabled == True,  # noqa: E712
                AgentSchedule.next_run_at <= now,
                or_(
                    AgentSchedule.last_run_status != "running",
                    AgentSchedule.last_run_status.is_(None),
                ),
            )
            .order_by(AgentSchedule.next_run_at)
        )
        return list(result.scalars().all())

    async def save(self, schedule: AgentSchedule) -> AgentSchedule:
        """Insert or update an agent schedule.

        Uses merge for upsert behavior (INSERT or UPDATE).

        Args:
            schedule: AgentSchedule to persist

        Returns:
            Persisted AgentSchedule instance.
        """
        merged = await self._session.merge(schedule)
        await self._session.flush()
        logger.info("Saved schedule: agent_name=%s", schedule.agent_name)
        return merged

    async def update_run_status(
        self,
        agent_name: str,
        status: str,
        duration: float | None,
        summary: dict | None,
        next_run: datetime | None,
    ) -> bool:
        """Update execution status for an agent.

        Args:
            agent_name: Agent to update
            status: New run status ("success", "failed", "incomplete", "running")
            duration: Run duration in seconds
            summary: Run result summary dict
            next_run: Next scheduled execution time

        Returns:
            True if agent was found and updated, False if not found.
        """
        result = await self._session.execute(
            select(AgentSchedule).where(AgentSchedule.agent_name == agent_name)
        )
        schedule = result.scalar_one_or_none()

        if schedule is None:
            logger.warning("Cannot update run status: agent %s not found", agent_name)
            return False

        schedule.last_run_status = status
        schedule.last_run_duration_seconds = duration
        schedule.last_run_summary = summary
        if next_run is not None:
            schedule.next_run_at = next_run
        await self._session.flush()
        return True

    async def save_change_log(self, log: ScheduleChangeLog) -> None:
        """Save an audit trail entry.

        Args:
            log: ScheduleChangeLog to persist
        """
        self._session.add(log)
        await self._session.flush()

    async def get_change_logs(
        self,
        agent_name: str,
        limit: int = 50,
    ) -> list[ScheduleChangeLog]:
        """Get change logs for an agent.

        Args:
            agent_name: Agent to query
            limit: Maximum entries to return (default 50)

        Returns:
            List of ScheduleChangeLog records, newest first.
        """
        result = await self._session.execute(
            select(ScheduleChangeLog)
            .where(ScheduleChangeLog.agent_name == agent_name)
            .order_by(desc(ScheduleChangeLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total schedules.

        Used for seeding check: if 0, seed defaults.

        Returns:
            Number of AgentSchedule records.
        """
        result = await self._session.execute(
            select(func.count(AgentSchedule.id))
        )
        return result.scalar_one()


__all__ = [
    "AgentScheduleRepository",
]
