"""Pipeline service dataclasses.

Story 5-5, Task 3.2: Internal data structures for pipeline service.
These are NOT API schemas — those live in ui/backend/schemas/pipeline.py.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class PipelineSummary:
    """Dashboard summary data."""

    total_leads: int
    status_counts: dict[str, int]
    conversion_rate: float
    avg_days_in_pipeline: float
    followup_count: int


@dataclass(frozen=True)
class ConversionMetrics:
    """Conversion funnel metrics."""

    conversion_rate: float
    total_leads: int
    converted_count: int
    avg_time_per_stage: dict[str, float]
    weekly_trend: list[dict]


@dataclass(frozen=True)
class WeeklyTrend:
    """Weekly new vs converted counts."""

    week: str
    new_leads: int
    converted: int


@dataclass(frozen=True)
class FollowUpCandidate:
    """Lead needing follow-up."""

    lead_id: UUID
    email: str
    company: str
    days_since_contact: int
    last_contacted_at: Optional[datetime]


@dataclass(frozen=True)
class StageTimingStats:
    """Average time per pipeline stage."""

    stage: str
    avg_days: float
    lead_count: int


__all__ = [
    "PipelineSummary",
    "ConversionMetrics",
    "WeeklyTrend",
    "FollowUpCandidate",
    "StageTimingStats",
]
