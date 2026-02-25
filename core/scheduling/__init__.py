"""Content scheduling module.

Story 4-4: Optimal time suggestions and ARQ job management
for scheduled content publishing.

Story 7-6: Agent schedule configuration with cron expressions,
dependency warnings, and ARQ dispatch.

Components:
    - OptimalTimeCalculator: Calculate optimal publish times
    - ConflictDetector: Detect scheduling conflicts
    - schedule_publish_job: ARQ job for publishing
    - WorkerSettings: ARQ worker configuration
    - AgentSchedule: Database model for agent schedules
    - AgentScheduleRepository: CRUD for agent schedules
    - AgentScheduleService: Business logic for schedule management
    - cron_utils: Cron expression utilities

Usage:
    from core.scheduling import OptimalTimeCalculator, schedule_publish_job
    from core.scheduling import AgentScheduleRepository, AgentScheduleService
"""

from .optimal_time import (
    OptimalTimeCalculator,
    TimeSlotScore,
    EngagementDataProtocol,
)
from .conflict_detector import (
    ConflictDetector,
    ConflictResult,
    ConflictSeverity,
)
from .jobs import (
    schedule_publish_job,
    cancel_publish_job,
    get_scheduled_jobs_status,
    WorkerSettings,
    enqueue_publish_job,
    update_publish_job,
)
from .models import (
    AgentSchedule,
    AgentExecutionLog,
    ScheduleChangeLog,
)
from .cron_utils import (
    validate_cron_expression,
    cron_expr_to_arq_kwargs,
    calculate_next_run,
    cron_to_human_readable,
)
from .dtos import (
    AgentScheduleDTO,
    ScheduleUpdateRequest,
    DependencyWarning,
    ScheduleChangeLogDTO,
    TriggerResult,
    TeamTriggerResult,
    TriggerableAgentDTO,
    TeamDTO,
    PendingTrigger,
    ExecutionLogDTO,
    ExecutionLogDetailDTO,
    DashboardSummaryDTO,
    ExecutionLogFilterDTO,
)
from .schedule_repository import AgentScheduleRepository
from .schedule_service import AgentScheduleService
from .manual_trigger_service import (
    ManualTriggerService,
    TEAM_DEFINITIONS,
    validate_team_definitions,
    PendingTriggerStore,
    pending_trigger_store,
)
from .execution_log_repository import ExecutionLogRepository
from .execution_log_service import ExecutionLogService
from .execution_events import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionEventEmitter,
    get_execution_events,
    execution_events,
)
from .log_capture import LogCaptureHandler

__all__ = [
    # Optimal time calculation
    "OptimalTimeCalculator",
    "TimeSlotScore",
    "EngagementDataProtocol",
    # Conflict detection
    "ConflictDetector",
    "ConflictResult",
    "ConflictSeverity",
    # ARQ jobs
    "schedule_publish_job",
    "cancel_publish_job",
    "get_scheduled_jobs_status",
    "WorkerSettings",
    "enqueue_publish_job",
    "update_publish_job",
    # Agent schedule models (Story 7-6)
    "AgentSchedule",
    "ScheduleChangeLog",
    # Cron utilities (Story 7-6)
    "validate_cron_expression",
    "cron_expr_to_arq_kwargs",
    "calculate_next_run",
    "cron_to_human_readable",
    # DTOs (Story 7-6)
    "AgentScheduleDTO",
    "ScheduleUpdateRequest",
    "DependencyWarning",
    "ScheduleChangeLogDTO",
    # DTOs (Story 7-7)
    "TriggerResult",
    "TeamTriggerResult",
    "TriggerableAgentDTO",
    "TeamDTO",
    "PendingTrigger",
    # Repository (Story 7-6)
    "AgentScheduleRepository",
    # Service (Story 7-6)
    "AgentScheduleService",
    # Manual trigger service (Story 7-7)
    "ManualTriggerService",
    "TEAM_DEFINITIONS",
    "validate_team_definitions",
    "PendingTriggerStore",
    "pending_trigger_store",
    # Execution log model (Story 7-8)
    "AgentExecutionLog",
    # Execution log DTOs (Story 7-8)
    "ExecutionLogDTO",
    "ExecutionLogDetailDTO",
    "DashboardSummaryDTO",
    "ExecutionLogFilterDTO",
    # Execution log repository + service (Story 7-8)
    "ExecutionLogRepository",
    "ExecutionLogService",
    # Execution events (Story 7-8)
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionEventEmitter",
    "get_execution_events",
    "execution_events",
    # Log capture (Story 7-8)
    "LogCaptureHandler",
]
