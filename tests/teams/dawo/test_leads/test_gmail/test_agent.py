"""Tests for Gmail Sender Agent.

Epic 5: B2B Sales Pipeline
Story 5-4: Gmail API Integration
Task 10: Gmail Sender Agent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from teams.dawo.leads.gmail.agent import GmailSenderAgent, AgentResult
from teams.dawo.leads.gmail.pipeline import GmailSendPipeline, PipelineResult


@pytest.fixture
def mock_pipeline() -> AsyncMock:
    """Provide mock pipeline."""
    pipeline = AsyncMock(spec=GmailSendPipeline)
    pipeline.execute.return_value = PipelineResult(
        sent=5,
        failed=1,
        skipped_gdpr=2,
        total_processed=8,
    )
    return pipeline


@pytest.fixture
def agent(mock_pipeline: AsyncMock) -> GmailSenderAgent:
    """Provide agent with mocked pipeline."""
    return GmailSenderAgent(pipeline=mock_pipeline)


class TestGmailSenderAgent:
    """Tests for GmailSenderAgent."""

    @pytest.mark.asyncio
    async def test_run_executes_pipeline(
        self, agent: GmailSenderAgent, mock_pipeline: AsyncMock
    ) -> None:
        """Test run() executes the pipeline."""
        result = await agent.run()
        mock_pipeline.execute.assert_called_once_with(batch_size=10)
        assert result.pipeline_result is not None

    @pytest.mark.asyncio
    async def test_run_returns_pipeline_stats(
        self, agent: GmailSenderAgent
    ) -> None:
        """Test run() returns pipeline statistics."""
        result = await agent.run()
        assert result.pipeline_result.sent == 5
        assert result.pipeline_result.failed == 1
        assert result.executed_at is not None

    @pytest.mark.asyncio
    async def test_run_custom_batch_size(
        self, agent: GmailSenderAgent, mock_pipeline: AsyncMock
    ) -> None:
        """Test run() with custom batch size."""
        await agent.run(batch_size=25)
        mock_pipeline.execute.assert_called_once_with(batch_size=25)

    @pytest.mark.asyncio
    async def test_run_handles_pipeline_error(
        self, agent: GmailSenderAgent, mock_pipeline: AsyncMock
    ) -> None:
        """Test run() handles pipeline execution errors gracefully."""
        mock_pipeline.execute.side_effect = Exception("Pipeline crashed")
        result = await agent.run()
        assert result.skipped is True
        assert "Execution error" in result.skip_reason
        assert result.executed_at is not None
