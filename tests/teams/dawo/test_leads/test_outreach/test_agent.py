"""Tests for Outreach Draft Agent.

Epic 5: B2B Sales Pipeline
Story 5-3: Personalized Outreach Draft Generator

Tests for OutreachDraftAgent execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from teams.dawo.leads.outreach.config import OutreachConfig
from teams.dawo.leads.outreach.pipeline import PipelineResult


class TestOutreachDraftAgent:
    """Tests for OutreachDraftAgent class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        return OutreachConfig()

    @pytest.fixture
    def mock_pipeline(self):
        """Create a mock pipeline."""
        pipeline = AsyncMock()
        pipeline.execute.return_value = PipelineResult(
            status="COMPLETE",
            total_processed=5,
            successful=5,
            failed=0,
            errors=[],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        return pipeline

    @pytest.fixture
    def agent(self, mock_config, mock_pipeline):
        """Create OutreachDraftAgent with mocked dependencies."""
        from teams.dawo.leads.outreach.agent import OutreachDraftAgent
        return OutreachDraftAgent(
            config=mock_config,
            pipeline=mock_pipeline,
        )

    @pytest.mark.asyncio
    async def test_run_returns_agent_result(self, agent):
        """run should return AgentResult."""
        from teams.dawo.leads.outreach.agent import AgentResult
        result = await agent.run()

        assert isinstance(result, AgentResult)

    @pytest.mark.asyncio
    async def test_run_executes_pipeline(self, agent, mock_pipeline):
        """run should execute the pipeline."""
        await agent.run()

        mock_pipeline.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_passes_batch_size(self, agent, mock_pipeline, mock_config):
        """run should pass batch_size to pipeline."""
        await agent.run()

        mock_pipeline.execute.assert_called_with(batch_size=mock_config.batch_size)

    @pytest.mark.asyncio
    async def test_run_success_on_complete(self, agent):
        """run should return success=True on complete."""
        result = await agent.run()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_success_on_incomplete(self, agent, mock_pipeline):
        """run should return success=True on incomplete (partial success)."""
        mock_pipeline.execute.return_value = PipelineResult(
            status="INCOMPLETE",
            total_processed=5,
            successful=3,
            failed=2,
            errors=["Error 1", "Error 2"],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        result = await agent.run()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_failure_on_failed(self, agent, mock_pipeline):
        """run should return success=False on failed."""
        mock_pipeline.execute.return_value = PipelineResult(
            status="FAILED",
            total_processed=5,
            successful=0,
            failed=5,
            errors=["Critical error"],
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        result = await agent.run()

        assert result.success is False

    @pytest.mark.asyncio
    async def test_run_tracks_statistics(self, agent):
        """run should track processing statistics."""
        result = await agent.run()

        assert result.leads_processed == 5
        assert result.drafts_generated == 5
        assert result.drafts_failed == 0

    @pytest.mark.asyncio
    async def test_run_handles_exception(self, agent, mock_pipeline):
        """run should handle exceptions gracefully."""
        mock_pipeline.execute.side_effect = Exception("Pipeline error")

        result = await agent.run()

        assert result.success is False
        assert result.status == "failed"
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_run_logs_activity(self, agent, caplog):
        """run should log activity."""
        import logging
        with caplog.at_level(logging.INFO):
            await agent.run()

        assert any("agent" in record.message.lower() for record in caplog.records)

    def test_get_schedule_returns_dict(self, agent):
        """get_schedule should return schedule dict."""
        schedule = agent.get_schedule()

        assert isinstance(schedule, dict)

    def test_get_schedule_includes_cron(self, agent):
        """get_schedule should include cron expression."""
        schedule = agent.get_schedule()

        assert "cron" in schedule

    def test_get_schedule_after_enrichment(self, agent):
        """get_schedule should run after enrichment agent."""
        schedule = agent.get_schedule()

        assert "after" in schedule
        assert "lead_enrichment" in schedule["after"]

    def test_agent_accepts_dependencies_via_injection(self, mock_config, mock_pipeline):
        """Agent should accept dependencies via injection."""
        from teams.dawo.leads.outreach.agent import OutreachDraftAgent
        agent = OutreachDraftAgent(
            config=mock_config,
            pipeline=mock_pipeline,
        )

        assert agent._config is mock_config
        assert agent._pipeline is mock_pipeline

    @pytest.mark.asyncio
    async def test_result_has_timestamps(self, agent):
        """AgentResult should have timestamps."""
        result = await agent.run()

        assert result.started_at is not None
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_result_to_dict(self, agent):
        """AgentResult should have to_dict method."""
        result = await agent.run()

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "status" in result_dict
        assert "leads_processed" in result_dict
