"""Tests for LeadEnrichmentAgent.

Epic 5: B2B Sales Pipeline
Story 5-2: Lead Information Enrichment
Task 9: Create Enrichment Agent
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, UTC


class TestLeadEnrichmentAgentInit:
    """Tests for LeadEnrichmentAgent initialization."""

    def test_accepts_dependencies_via_injection(self) -> None:
        """Test agent accepts all dependencies via DI."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        pipeline = AsyncMock()

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        assert agent._config is config
        assert agent._pipeline is pipeline


class TestAgentRun:
    """Tests for agent run method."""

    @pytest.mark.asyncio
    async def test_run_executes_pipeline(self) -> None:
        """Test agent runs the enrichment pipeline."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus

        config = EnrichmentConfig()

        pipeline_result = PipelineResult(
            total_processed=5,
            successful=4,
            failed=1,
            qualified=3,
            researching=1,
            converted=0,
            status=PipelineStatus.INCOMPLETE,
        )

        pipeline = AsyncMock()
        pipeline.execute.return_value = pipeline_result

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        result = await agent.run()

        # Verify pipeline was executed
        pipeline.execute.assert_called_once()

        # Verify result contains pipeline statistics
        assert result.leads_processed == 5
        assert result.leads_enriched == 4
        assert result.leads_failed == 1

    @pytest.mark.asyncio
    async def test_run_with_custom_batch_size(self) -> None:
        """Test agent passes batch size to pipeline."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus

        config = EnrichmentConfig(batch_size=20)

        pipeline_result = PipelineResult(
            total_processed=0,
            successful=0,
            failed=0,
            qualified=0,
            researching=0,
            converted=0,
            status=PipelineStatus.EMPTY,
        )

        pipeline = AsyncMock()
        pipeline.execute.return_value = pipeline_result

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        await agent.run()

        # Verify batch size was passed
        pipeline.execute.assert_called_once_with(batch_size=20)

    @pytest.mark.asyncio
    async def test_run_returns_success_on_complete(self) -> None:
        """Test agent returns success when all leads processed."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent, AgentResult
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus

        config = EnrichmentConfig()

        pipeline_result = PipelineResult(
            total_processed=10,
            successful=10,
            failed=0,
            qualified=7,
            researching=3,
            converted=0,
            status=PipelineStatus.COMPLETE,
        )

        pipeline = AsyncMock()
        pipeline.execute.return_value = pipeline_result

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        result = await agent.run()

        assert result.success is True
        assert result.status == "complete"

    @pytest.mark.asyncio
    async def test_run_returns_partial_on_failures(self) -> None:
        """Test agent returns partial success when some leads fail."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
        from teams.dawo.leads.enrichment.config import EnrichmentConfig
        from teams.dawo.leads.enrichment.pipeline import PipelineResult, PipelineStatus

        config = EnrichmentConfig()

        pipeline_result = PipelineResult(
            total_processed=10,
            successful=7,
            failed=3,
            qualified=5,
            researching=2,
            converted=0,
            status=PipelineStatus.INCOMPLETE,
        )

        pipeline = AsyncMock()
        pipeline.execute.return_value = pipeline_result

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        result = await agent.run()

        assert result.success is True  # Still success but partial
        assert result.status == "incomplete"


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_agent_result_has_required_fields(self) -> None:
        """Test AgentResult contains all expected fields."""
        from teams.dawo.leads.enrichment.agent import AgentResult

        result = AgentResult(
            success=True,
            status="complete",
            leads_processed=10,
            leads_enriched=8,
            leads_failed=2,
            leads_qualified=6,
            leads_researching=2,
            leads_converted=0,
        )

        assert result.success is True
        assert result.status == "complete"
        assert result.leads_processed == 10
        assert result.leads_enriched == 8
        assert result.leads_failed == 2
        assert result.leads_qualified == 6
        assert result.leads_researching == 2
        assert result.leads_converted == 0

    def test_agent_result_has_timing_fields(self) -> None:
        """Test AgentResult includes timing information."""
        from teams.dawo.leads.enrichment.agent import AgentResult

        started = datetime.now(UTC)
        completed = datetime.now(UTC)

        result = AgentResult(
            success=True,
            status="complete",
            leads_processed=0,
            leads_enriched=0,
            leads_failed=0,
            leads_qualified=0,
            leads_researching=0,
            leads_converted=0,
            started_at=started,
            completed_at=completed,
        )

        assert result.started_at == started
        assert result.completed_at == completed


class TestAgentScheduling:
    """Tests for agent scheduling support."""

    def test_agent_has_schedule_config(self) -> None:
        """Test agent can be configured with schedule."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        pipeline = AsyncMock()

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        # Agent should expose its schedule info
        schedule = agent.get_schedule()
        assert schedule is not None
        assert "cron" in schedule or "after" in schedule

    def test_agent_runs_after_scanner(self) -> None:
        """Test agent is scheduled to run after scanner completes."""
        from teams.dawo.leads.enrichment.agent import LeadEnrichmentAgent
        from teams.dawo.leads.enrichment.config import EnrichmentConfig

        config = EnrichmentConfig()
        pipeline = AsyncMock()

        agent = LeadEnrichmentAgent(
            config=config,
            pipeline=pipeline,
        )

        schedule = agent.get_schedule()

        # Should run after scanner completes
        assert "after" in schedule
        assert "lead_scanner" in schedule["after"]
