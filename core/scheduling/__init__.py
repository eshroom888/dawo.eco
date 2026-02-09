"""Content scheduling module.

Story 4-4: Optimal time suggestions and ARQ job management
for scheduled content publishing.

Components:
    - OptimalTimeCalculator: Calculate optimal publish times
    - ConflictDetector: Detect scheduling conflicts
    - schedule_publish_job: ARQ job for publishing
    - WorkerSettings: ARQ worker configuration

Usage:
    from core.scheduling import OptimalTimeCalculator, schedule_publish_job

    calculator = OptimalTimeCalculator(timezone="Europe/Oslo")
    suggestions = await calculator.get_optimal_slots(target_date, existing_items)
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
]
