"""Pydantic schemas for Manual Trigger API.

Story 7-7, Task 5.1: Request/response schemas for manual triggering.

Schemas:
    - TriggerAgentRequest: Trigger with optional overrides
    - TriggerAgentResponse: Single agent trigger result
    - TriggerTeamRequest: Team trigger request
    - TeamTriggerResponse: Aggregated team trigger result
    - TriggerableAgentResponse: Agent with status for listing
    - TriggerableAgentListResponse: List of triggerable agents
    - TeamResponse: Team definition
    - TeamListResponse: List of teams
    - QueueAfterRequest: Queue trigger for running agent
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TriggerAgentRequest(BaseModel):
    """Request body for triggering a single agent."""

    config_overrides: Optional[dict] = Field(
        default=None, description="Runtime config overrides for this run only"
    )
    force: bool = Field(
        default=False, description="If True, queue for after current run"
    )


class TriggerAgentResponse(BaseModel):
    """Response after triggering an agent."""

    agent_name: str = Field(..., description="Agent that was triggered")
    status: str = Field(..., description="queued / already_running / failed / not_found")
    job_id: Optional[str] = Field(default=None, description="ARQ job ID")
    triggered_at: datetime = Field(..., description="When the trigger was requested")
    message: str = Field(default="", description="Human-readable status")

    model_config = {"from_attributes": True}


class TriggerTeamRequest(BaseModel):
    """Request body for triggering a team (body is optional)."""

    pass


class TeamTriggerResponse(BaseModel):
    """Response after triggering a team."""

    team_name: str = Field(..., description="Team that was triggered")
    agent_results: list[TriggerAgentResponse] = Field(
        ..., description="Per-agent results"
    )
    total: int = Field(..., ge=0, description="Total agents in team")
    queued: int = Field(..., ge=0, description="Agents queued")
    skipped_running: int = Field(..., ge=0, description="Agents already running")
    failed: int = Field(..., ge=0, description="Agents that failed to trigger")


class TriggerableAgentResponse(BaseModel):
    """Agent available for manual triggering with status."""

    agent_name: str = Field(..., description="Unique agent identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None, description="Agent description")
    last_run_status: Optional[str] = Field(default=None, description="Last run result")
    last_run_at: Optional[datetime] = Field(default=None, description="Last execution")
    last_run_duration_seconds: Optional[float] = Field(
        default=None, description="Last run duration"
    )
    is_running: bool = Field(default=False, description="Currently executing")
    schedule_cron: Optional[str] = Field(default=None, description="Cron expression")
    next_scheduled_run: Optional[datetime] = Field(
        default=None, description="Next scheduled run"
    )

    model_config = {"from_attributes": True}


class TriggerableAgentListResponse(BaseModel):
    """List of triggerable agents."""

    agents: list[TriggerableAgentResponse] = Field(..., description="Agent entries")
    total_count: int = Field(..., ge=0, description="Total agents")


class TeamResponse(BaseModel):
    """Team definition."""

    team_name: str = Field(..., description="Unique team identifier")
    display_name: str = Field(..., description="Human-readable name")
    agents: list[str] = Field(..., description="Ordered agent names")
    description: str = Field(..., description="Team description")


class TeamListResponse(BaseModel):
    """List of team definitions."""

    teams: list[TeamResponse] = Field(..., description="Team entries")


class QueueAfterRequest(BaseModel):
    """Request body for queueing a trigger after current run."""

    pass


__all__ = [
    "QueueAfterRequest",
    "TeamListResponse",
    "TeamResponse",
    "TeamTriggerResponse",
    "TriggerAgentRequest",
    "TriggerAgentResponse",
    "TriggerTeamRequest",
    "TriggerableAgentListResponse",
    "TriggerableAgentResponse",
]
