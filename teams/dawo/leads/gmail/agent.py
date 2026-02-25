"""Gmail Sender Agent.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration

Agent that executes the Gmail send pipeline on a schedule.
Uses tier="scan" — no LLM calls, pure orchestration.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, UTC

from teams.dawo.leads.gmail.pipeline import GmailSendPipeline, PipelineResult

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result of agent execution.

    Attributes:
        pipeline_result: Pipeline execution result
        executed_at: When agent ran
        skipped: True if skipped (outside business hours, etc.)
        skip_reason: Why execution was skipped
    """

    pipeline_result: PipelineResult | None = None
    executed_at: datetime | None = None
    skipped: bool = False
    skip_reason: str | None = None


class GmailSenderAgent:
    """Gmail sender agent for scheduled outreach.

    Executes the send pipeline on schedule. Uses tier="scan" —
    this agent does NO LLM work, just orchestrates API calls.

    Schedule: Every 30 minutes during business hours (8-17 Oslo time).
    """

    def __init__(self, pipeline: GmailSendPipeline) -> None:
        """Initialize agent with pipeline.

        Args:
            pipeline: Gmail send pipeline
        """
        self._pipeline = pipeline

    async def run(self, batch_size: int = 10) -> AgentResult:
        """Execute the send pipeline.

        Args:
            batch_size: Maximum leads to process

        Returns:
            AgentResult with pipeline statistics
        """
        logger.info("GmailSenderAgent starting pipeline execution")

        try:
            pipeline_result = await self._pipeline.execute(
                batch_size=batch_size
            )

            logger.info(
                f"GmailSenderAgent complete: "
                f"{pipeline_result.sent} sent, "
                f"{pipeline_result.failed} failed"
            )

            return AgentResult(
                pipeline_result=pipeline_result,
                executed_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.error(f"GmailSenderAgent execution failed: {e}")
            return AgentResult(
                executed_at=datetime.now(UTC),
                skipped=True,
                skip_reason=f"Execution error: {e}",
            )


__all__ = [
    "GmailSenderAgent",
    "AgentResult",
]
