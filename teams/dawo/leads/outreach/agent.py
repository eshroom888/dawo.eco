"""Outreach Draft Agent for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Main outreach agent that generates personalized email drafts
for qualified leads.

Uses tier="generate" (maps to Sonnet at runtime) for LLM operations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional, Protocol

from teams.dawo.leads.outreach.config import OutreachConfig
from teams.dawo.leads.outreach.pipeline import PipelineResult


logger = logging.getLogger(__name__)


# Default schedule: Run daily at 9 AM, after enrichment completes
DEFAULT_SCHEDULE = {
    "cron": "0 9 * * *",  # 9 AM daily
    "after": ["lead_enrichment"],  # Run after enrichment completes
}


@dataclass
class AgentResult:
    """Result of agent execution.

    Attributes:
        success: Whether agent completed (even partially)
        status: Execution status (complete, incomplete, failed, empty)
        leads_processed: Total leads attempted
        drafts_generated: Successfully generated drafts
        drafts_failed: Failed draft attempts
        errors: List of error messages
        started_at: Agent start time
        completed_at: Agent completion time
    """

    success: bool
    status: str
    leads_processed: int = 0
    drafts_generated: int = 0
    drafts_failed: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "success": self.success,
            "status": self.status,
            "leads_processed": self.leads_processed,
            "drafts_generated": self.drafts_generated,
            "drafts_failed": self.drafts_failed,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class OutreachPipelineProtocol(Protocol):
    """Protocol for outreach pipeline dependency."""

    async def execute(self, batch_size: Optional[int] = None) -> PipelineResult:
        """Execute the outreach pipeline."""
        ...


class OutreachDraftAgent:
    """Outreach Draft Agent.

    Generates personalized email drafts for qualified B2B leads:
    - Classifies leads by type
    - Selects appropriate templates
    - Creates personalized content
    - Validates against brand voice

    Uses tier="generate" (maps to Sonnet at runtime) for LLM operations.

    Scheduled to run:
    - Daily at 9 AM
    - After enrichment agent completes

    Attributes:
        _config: Agent configuration
        _pipeline: Outreach pipeline
    """

    def __init__(
        self,
        config: OutreachConfig,
        pipeline: OutreachPipelineProtocol,
    ) -> None:
        """Initialize the outreach agent.

        Args:
            config: Agent configuration
            pipeline: Outreach pipeline to execute
        """
        self._config = config
        self._pipeline = pipeline

    async def run(self) -> AgentResult:
        """Execute the outreach agent.

        Runs the outreach pipeline to generate drafts for qualified leads.
        Reports statistics on completion.

        Returns:
            AgentResult with execution statistics
        """
        started_at = datetime.now(UTC)

        logger.info("Outreach draft agent starting")

        try:
            # Execute pipeline with configured batch size
            pipeline_result = await self._pipeline.execute(
                batch_size=self._config.batch_size
            )

            # Map pipeline result to agent result
            agent_result = self._create_result(pipeline_result, started_at)

            logger.info(
                f"Outreach draft agent complete: "
                f"{agent_result.drafts_generated}/{agent_result.leads_processed} generated"
            )

            return agent_result

        except Exception as e:
            error_msg = f"Outreach draft agent failed: {e}"
            logger.error(error_msg)

            return AgentResult(
                success=False,
                status="failed",
                leads_processed=0,
                drafts_generated=0,
                drafts_failed=0,
                errors=[error_msg],
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )

    def get_schedule(self) -> dict[str, Any]:
        """Get the agent's schedule configuration.

        Returns:
            Dict with cron expression and dependencies
        """
        return DEFAULT_SCHEDULE.copy()

    def _create_result(
        self,
        pipeline_result: PipelineResult,
        started_at: datetime,
    ) -> AgentResult:
        """Create agent result from pipeline result.

        Args:
            pipeline_result: Result from pipeline execution
            started_at: When agent started

        Returns:
            AgentResult with mapped statistics
        """
        # Determine success and status
        if pipeline_result.status == "FAILED":
            success = False
            status = "failed"
        elif pipeline_result.total_processed == 0:
            success = True
            status = "empty"
        elif pipeline_result.status == "INCOMPLETE":
            success = True  # Partial success is still success
            status = "incomplete"
        else:
            success = True
            status = "complete"

        return AgentResult(
            success=success,
            status=status,
            leads_processed=pipeline_result.total_processed,
            drafts_generated=pipeline_result.successful,
            drafts_failed=pipeline_result.failed,
            errors=[
                e.get("error", "Unknown") if isinstance(e, dict) else str(e)
                for e in pipeline_result.errors
            ],
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
