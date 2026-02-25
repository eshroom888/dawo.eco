"""Lead Enrichment Agent for B2B Sales Pipeline.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 9: Create Enrichment Agent

Main enrichment agent that processes NEW leads and gathers
business information from multiple sources.

Uses tier="generate" (maps to Sonnet at runtime) for LLM analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional, Protocol

from teams.dawo.leads.enrichment.config import EnrichmentConfig
from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus


logger = logging.getLogger(__name__)


# Default schedule: Run daily at 8 AM, after scanner completes
DEFAULT_SCHEDULE = {
    "cron": "0 8 * * *",  # 8 AM daily
    "after": ["lead_scanner"],  # Run after scanner completes
}


@dataclass
class AgentResult:
    """Result of agent execution.

    Attributes:
        success: Whether agent completed (even partially)
        status: Execution status (complete, incomplete, failed, empty)
        leads_processed: Total leads attempted
        leads_enriched: Successfully enriched leads
        leads_failed: Failed enrichment attempts
        leads_qualified: Leads marked QUALIFIED
        leads_researching: Leads marked RESEARCHING
        leads_converted: Leads marked CONVERTED
        errors: List of error messages
        started_at: Agent start time
        completed_at: Agent completion time
    """

    success: bool
    status: str
    leads_processed: int = 0
    leads_enriched: int = 0
    leads_failed: int = 0
    leads_qualified: int = 0
    leads_researching: int = 0
    leads_converted: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "success": self.success,
            "status": self.status,
            "leads_processed": self.leads_processed,
            "leads_enriched": self.leads_enriched,
            "leads_failed": self.leads_failed,
            "leads_qualified": self.leads_qualified,
            "leads_researching": self.leads_researching,
            "leads_converted": self.leads_converted,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class EnrichmentPipelineProtocol(Protocol):
    """Protocol for enrichment pipeline dependency."""

    async def execute(self, batch_size: Optional[int] = None) -> PipelineResult:
        """Execute the enrichment pipeline."""
        ...


class LeadEnrichmentAgent:
    """Lead Enrichment Agent.

    Processes NEW leads and enriches them with business information
    from multiple sources:
    - Website analysis
    - Hunter.io company data
    - LLM-based business insights
    - Social media presence

    Uses tier="generate" (maps to Sonnet at runtime) for analysis.

    Scheduled to run:
    - Daily at 8 AM
    - After lead scanner completes

    Attributes:
        _config: Agent configuration
        _pipeline: Enrichment pipeline
    """

    def __init__(
        self,
        config: EnrichmentConfig,
        pipeline: EnrichmentPipelineProtocol,
    ) -> None:
        """Initialize the enrichment agent.

        Args:
            config: Agent configuration
            pipeline: Enrichment pipeline to execute
        """
        self._config = config
        self._pipeline = pipeline

    async def run(self) -> AgentResult:
        """Execute the enrichment agent.

        Runs the enrichment pipeline to process NEW leads.
        Reports statistics on completion.

        Returns:
            AgentResult with execution statistics
        """
        started_at = datetime.now(UTC)

        logger.info("Lead enrichment agent starting")

        try:
            # Execute pipeline with configured batch size
            pipeline_result = await self._pipeline.execute(
                batch_size=self._config.batch_size
            )

            # Map pipeline result to agent result
            agent_result = self._create_result(pipeline_result, started_at)

            logger.info(
                f"Lead enrichment agent complete: "
                f"{agent_result.leads_enriched}/{agent_result.leads_processed} enriched, "
                f"{agent_result.leads_qualified} qualified, "
                f"{agent_result.leads_researching} researching, "
                f"{agent_result.leads_converted} converted"
            )

            return agent_result

        except Exception as e:
            error_msg = f"Lead enrichment agent failed: {e}"
            logger.error(error_msg)

            return AgentResult(
                success=False,
                status="failed",
                leads_processed=0,
                leads_enriched=0,
                leads_failed=0,
                leads_qualified=0,
                leads_researching=0,
                leads_converted=0,
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
        if pipeline_result.status == PipelineStatus.FAILED:
            success = False
            status = "failed"
        elif pipeline_result.status == PipelineStatus.EMPTY:
            success = True
            status = "empty"
        elif pipeline_result.status == PipelineStatus.INCOMPLETE:
            success = True  # Partial success is still success
            status = "incomplete"
        else:
            success = True
            status = "complete"

        return AgentResult(
            success=success,
            status=status,
            leads_processed=pipeline_result.total_processed,
            leads_enriched=pipeline_result.successful,
            leads_failed=pipeline_result.failed,
            leads_qualified=pipeline_result.qualified,
            leads_researching=pipeline_result.researching,
            leads_converted=pipeline_result.converted,
            errors=pipeline_result.errors,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
