"""Execution log repository for CRUD operations.

Story 7-8, Task 3.1: Repository pattern with AsyncSession injection.

Provides CRUD, filtered queries, aggregate stats, and cleanup
for agent execution logs powering the execution dashboard.

Usage:
    from core.scheduling.execution_log_repository import ExecutionLogRepository

    repo = ExecutionLogRepository(session)
    running = await repo.get_running()
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, desc, func, over, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.scheduling.dtos import ExecutionLogFilterDTO
from core.scheduling.models import AgentExecutionLog

logger = logging.getLogger(__name__)


class ExecutionLogRepository:
    """Repository for agent execution log persistence.

    Accepts AsyncSession via constructor injection.
    Uses SQL aggregates for stats (not in-memory Python).
    Uses COUNT window function for filtered+paginated queries.

    Attributes:
        _session: Async SQLAlchemy session
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def create(self, log: AgentExecutionLog) -> AgentExecutionLog:
        """Insert a new execution log entry.

        Args:
            log: AgentExecutionLog to persist

        Returns:
            The persisted AgentExecutionLog instance.
        """
        self._session.add(log)
        await self._session.flush()
        logger.info(
            "Created execution log: agent_name=%s, status=%s",
            log.agent_name,
            log.status,
        )
        return log

    async def update_completion(
        self,
        log_id: UUID,
        status: str,
        duration: float,
        summary: dict | None,
        error_message: str | None,
        error_traceback: str | None,
        log_output: str | None,
        items_processed: int,
    ) -> bool:
        """Update an execution log when execution completes.

        Args:
            log_id: UUID of the execution log to update
            status: Final status (success, failed, incomplete)
            duration: Execution duration in seconds
            summary: Runner result summary dict
            error_message: Error description on failure
            error_traceback: Stack trace on failure
            log_output: Captured log lines
            items_processed: Count of items processed

        Returns:
            True if log was found and updated, False if not found.
        """
        result = await self._session.execute(
            select(AgentExecutionLog).where(AgentExecutionLog.id == log_id)
        )
        log = result.scalar_one_or_none()

        if log is None:
            logger.warning("Cannot update execution log: id=%s not found", log_id)
            return False

        log.status = status
        log.completed_at = datetime.now(UTC)
        log.duration_seconds = duration
        log.summary = summary
        log.error_message = error_message
        log.error_traceback = error_traceback
        log.log_output = log_output
        log.items_processed = items_processed
        await self._session.flush()
        return True

    async def get_by_id(self, log_id: UUID) -> AgentExecutionLog | None:
        """Get a single execution log by ID.

        Args:
            log_id: UUID of the execution log

        Returns:
            AgentExecutionLog if found, None otherwise.
        """
        result = await self._session.execute(
            select(AgentExecutionLog).where(AgentExecutionLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_running(self) -> list[AgentExecutionLog]:
        """Get all currently running executions.

        Returns:
            List of AgentExecutionLog with status='running'.
        """
        result = await self._session.execute(
            select(AgentExecutionLog)
            .where(AgentExecutionLog.status == "running")
            .order_by(desc(AgentExecutionLog.started_at))
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        hours: int = 24,
        status: str | None = None,
        limit: int = 50,
    ) -> list[AgentExecutionLog]:
        """Get recent executions within a time window.

        Args:
            hours: Lookback period in hours (default 24)
            status: Optional status filter
            limit: Maximum results (default 50)

        Returns:
            List of recent AgentExecutionLog records.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        query = (
            select(AgentExecutionLog)
            .where(AgentExecutionLog.started_at >= cutoff)
        )
        if status is not None:
            query = query.where(AgentExecutionLog.status == status)
        query = query.order_by(desc(AgentExecutionLog.started_at)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_filtered(
        self,
        filters: ExecutionLogFilterDTO,
    ) -> tuple[list[AgentExecutionLog], int]:
        """Get filtered and paginated execution logs.

        Uses COUNT window function for total_count alongside results
        in a single SQL query (no N+1).

        Args:
            filters: Filter criteria with pagination

        Returns:
            Tuple of (results, total_count).
        """
        query = select(
            AgentExecutionLog,
            over(func.count(AgentExecutionLog.id)),
        )

        if filters.agent_name is not None:
            query = query.where(AgentExecutionLog.agent_name == filters.agent_name)
        if filters.status is not None:
            query = query.where(AgentExecutionLog.status == filters.status)
        if filters.trigger_type is not None:
            query = query.where(AgentExecutionLog.trigger_type == filters.trigger_type)
        if filters.date_from is not None:
            query = query.where(AgentExecutionLog.started_at >= filters.date_from)
        if filters.date_to is not None:
            query = query.where(AgentExecutionLog.started_at <= filters.date_to)

        query = (
            query
            .order_by(desc(AgentExecutionLog.started_at))
            .offset(filters.offset)
            .limit(filters.limit)
        )

        result = await self._session.execute(query)
        rows = result.all()

        if not rows:
            return [], 0

        logs = [row[0] for row in rows]
        total_count = rows[0][1]
        return logs, total_count

    async def get_stats(self, hours: int = 24) -> dict:
        """Get aggregated statistics using SQL aggregate functions.

        Args:
            hours: Lookback period in hours (default 24)

        Returns:
            Dict with total, success, failed, avg_duration.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        query = select(
            func.count(AgentExecutionLog.id),
            func.count(AgentExecutionLog.id).filter(
                AgentExecutionLog.status == "success"
            ),
            func.count(AgentExecutionLog.id).filter(
                AgentExecutionLog.status.in_(["failed", "incomplete"])
            ),
            func.avg(AgentExecutionLog.duration_seconds),
        ).where(AgentExecutionLog.started_at >= cutoff)

        result = await self._session.execute(query)
        total, success, failed, avg_duration = result.one()

        return {
            "total": total or 0,
            "success": success or 0,
            "failed": failed or 0,
            "avg_duration": float(avg_duration) if avg_duration is not None else None,
        }

    async def cleanup_old(self, days: int = 90) -> int:
        """Delete execution logs older than N days.

        Args:
            days: Retention period in days (default 90)

        Returns:
            Number of deleted records.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self._session.execute(
            delete(AgentExecutionLog).where(AgentExecutionLog.created_at < cutoff)
        )
        await self._session.flush()
        deleted = result.rowcount
        if deleted > 0:
            logger.info("Cleaned up %d execution logs older than %d days", deleted, days)
        return deleted


__all__ = [
    "ExecutionLogRepository",
]
