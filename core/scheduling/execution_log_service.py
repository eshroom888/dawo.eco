"""Execution log service for dashboard business logic.

Story 7-8, Task 4.1: Service layer for execution log operations.

Coordinates between ExecutionLogRepository and AgentScheduleRepository
to provide enriched DTOs with display_names for the dashboard.

Usage:
    from core.scheduling.execution_log_service import ExecutionLogService

    service = ExecutionLogService(log_repo, schedule_repo)
    summary = await service.get_dashboard_summary()
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from core.scheduling.dtos import (
    DashboardSummaryDTO,
    ExecutionLogDTO,
    ExecutionLogDetailDTO,
    ExecutionLogFilterDTO,
)
from core.scheduling.execution_log_repository import ExecutionLogRepository
from core.scheduling.models import AgentExecutionLog
from core.scheduling.schedule_repository import AgentScheduleRepository

logger = logging.getLogger(__name__)

MAX_LOG_LINES = 1000


class ExecutionLogService:
    """Business logic for the execution dashboard.

    Constructor injection of both repositories.
    Batch-fetches schedules for display_name enrichment (no N+1).

    Attributes:
        _log_repo: ExecutionLogRepository for execution log persistence
        _schedule_repo: AgentScheduleRepository for display_name lookup
    """

    def __init__(
        self,
        log_repo: ExecutionLogRepository,
        schedule_repo: AgentScheduleRepository,
    ) -> None:
        """Initialize service.

        Args:
            log_repo: Repository for execution log CRUD
            schedule_repo: Repository for schedule lookups (display_name)
        """
        self._log_repo = log_repo
        self._schedule_repo = schedule_repo

    async def start_execution(
        self,
        agent_name: str,
        trigger_type: str,
        triggered_by: str,
    ) -> ExecutionLogDTO:
        """Create a new execution log entry with status='running'.

        Args:
            agent_name: Agent identifier
            trigger_type: 'scheduled' or 'manual'
            triggered_by: Who triggered the execution

        Returns:
            ExecutionLogDTO with enriched display_name.
        """
        log = AgentExecutionLog(
            agent_name=agent_name,
            started_at=datetime.now(UTC),
            status="running",
            trigger_type=trigger_type,
            triggered_by=triggered_by,
        )
        created = await self._log_repo.create(log)

        schedule = await self._schedule_repo.get_by_agent_name(agent_name)
        display_name = (
            schedule.display_name
            if schedule
            else agent_name.replace("_", " ").title()
        )

        return self._to_dto(created, display_name)

    async def complete_execution(
        self,
        log_id: str,
        status: str,
        summary: dict | None,
        error_message: str | None,
        error_traceback: str | None,
        log_output: str | None,
    ) -> ExecutionLogDTO | None:
        """Complete an execution log entry.

        Calculates duration from started_at, extracts items_processed
        from summary, and caps log_output at MAX_LOG_LINES.

        Args:
            log_id: UUID string of the execution log
            status: Final status (success, failed, incomplete)
            summary: Runner result summary dict
            error_message: Error description on failure
            error_traceback: Stack trace on failure
            log_output: Captured log lines

        Returns:
            Updated ExecutionLogDTO, or None if log not found.
        """
        uid = UUID(log_id)
        existing = await self._log_repo.get_by_id(uid)
        if existing is None:
            logger.warning("Cannot complete execution: log %s not found", log_id)
            return None

        duration = (datetime.now(UTC) - existing.started_at).total_seconds()
        items_processed = (
            summary.get("items_processed", 0) if summary else 0
        )

        # Cap log output at MAX_LOG_LINES
        capped_output = log_output
        if log_output is not None:
            lines = log_output.split("\n")
            if len(lines) > MAX_LOG_LINES:
                capped_output = "\n".join(lines[-MAX_LOG_LINES:])

        await self._log_repo.update_completion(
            log_id=uid,
            status=status,
            duration=duration,
            summary=summary,
            error_message=error_message,
            error_traceback=error_traceback,
            log_output=capped_output,
            items_processed=items_processed,
        )

        schedule = await self._schedule_repo.get_by_agent_name(existing.agent_name)
        display_name = (
            schedule.display_name
            if schedule
            else existing.agent_name.replace("_", " ").title()
        )

        # Build DTO from known values (avoids extra DB round-trip)
        return ExecutionLogDTO(
            id=str(uid),
            agent_name=existing.agent_name,
            display_name=display_name,
            started_at=existing.started_at,
            completed_at=datetime.now(UTC),
            duration_seconds=duration,
            status=status,
            trigger_type=existing.trigger_type,
            triggered_by=existing.triggered_by,
            summary=summary,
            error_message=error_message,
            error_traceback=error_traceback,
            items_processed=items_processed,
            has_log_output=capped_output is not None,
        )

    async def get_dashboard_summary(self) -> DashboardSummaryDTO:
        """Build dashboard overview with running, completions, failures.

        Batch-fetches all schedules for display_name enrichment (no N+1).

        Returns:
            DashboardSummaryDTO with aggregated data.
        """
        # Batch fetch schedules for display_name map
        all_schedules = await self._schedule_repo.get_all()
        schedule_map = {s.agent_name: s.display_name for s in all_schedules}

        # Parallel queries — all independent reads
        import asyncio

        (
            running,
            recent_success,
            recent_failures,
            recent_incomplete,
            stats,
        ) = await asyncio.gather(
            self._log_repo.get_running(),
            self._log_repo.get_recent(hours=24, status="success"),
            self._log_repo.get_recent(hours=168, status="failed"),
            self._log_repo.get_recent(hours=168, status="incomplete"),
            self._log_repo.get_stats(hours=24),
        )
        all_failures = recent_failures + recent_incomplete

        total = stats["total"]
        success_count = stats["success"]
        success_rate = (success_count / total * 100.0) if total > 0 else 0.0

        return DashboardSummaryDTO(
            running=[self._to_dto(log, self._enrich_display_name(log.agent_name, schedule_map)) for log in running],
            recent_completions=[self._to_dto(log, self._enrich_display_name(log.agent_name, schedule_map)) for log in recent_success],
            recent_failures=[self._to_dto(log, self._enrich_display_name(log.agent_name, schedule_map)) for log in all_failures],
            total_executions_24h=total,
            success_rate_24h=success_rate,
            avg_duration_24h=stats["avg_duration"],
        )

    async def get_execution_detail(self, log_id: str) -> ExecutionLogDetailDTO | None:
        """Get full execution detail including log_output.

        Args:
            log_id: UUID string of the execution log

        Returns:
            ExecutionLogDetailDTO with log_output, or None if not found.
        """
        uid = UUID(log_id)
        log = await self._log_repo.get_by_id(uid)
        if log is None:
            return None

        schedule = await self._schedule_repo.get_by_agent_name(log.agent_name)
        display_name = (
            schedule.display_name
            if schedule
            else log.agent_name.replace("_", " ").title()
        )

        return ExecutionLogDetailDTO(
            id=str(log.id),
            agent_name=log.agent_name,
            display_name=display_name,
            started_at=log.started_at,
            completed_at=log.completed_at,
            duration_seconds=log.duration_seconds,
            status=log.status,
            trigger_type=log.trigger_type,
            triggered_by=log.triggered_by,
            summary=log.summary,
            error_message=log.error_message,
            error_traceback=log.error_traceback,
            items_processed=log.items_processed,
            has_log_output=log.log_output is not None,
            log_output=log.log_output,
        )

    async def get_filtered_executions(
        self,
        filters: ExecutionLogFilterDTO,
    ) -> tuple[list[ExecutionLogDTO], int]:
        """Get filtered and paginated execution logs with display_names.

        Args:
            filters: Filter criteria with pagination

        Returns:
            Tuple of (enriched DTOs, total_count).
        """
        logs, total = await self._log_repo.get_filtered(filters)
        if not logs:
            return [], 0

        all_schedules = await self._schedule_repo.get_all()
        schedule_map = {s.agent_name: s.display_name for s in all_schedules}

        dtos = [
            self._to_dto(log, self._enrich_display_name(log.agent_name, schedule_map))
            for log in logs
        ]
        return dtos, total

    def _enrich_display_name(self, agent_name: str, schedule_map: dict) -> str:
        """Look up display_name from schedule map with fallback.

        Args:
            agent_name: Agent identifier
            schedule_map: Pre-fetched {agent_name: display_name} map

        Returns:
            Display name from schedule or title-cased fallback.
        """
        return schedule_map.get(
            agent_name,
            agent_name.replace("_", " ").title(),
        )

    @staticmethod
    def _to_dto(log: AgentExecutionLog, display_name: str) -> ExecutionLogDTO:
        """Convert model to DTO.

        Args:
            log: AgentExecutionLog model instance
            display_name: Enriched display name

        Returns:
            ExecutionLogDTO frozen dataclass.
        """
        return ExecutionLogDTO(
            id=str(log.id),
            agent_name=log.agent_name,
            display_name=display_name,
            started_at=log.started_at,
            completed_at=log.completed_at,
            duration_seconds=log.duration_seconds,
            status=log.status,
            trigger_type=log.trigger_type,
            triggered_by=log.triggered_by,
            summary=log.summary,
            error_message=log.error_message,
            error_traceback=log.error_traceback,
            items_processed=log.items_processed,
            has_log_output=log.log_output is not None,
        )


__all__ = [
    "ExecutionLogService",
]
